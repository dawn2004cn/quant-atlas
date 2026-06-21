import time
import threading
import logging

from typing import Any
from pytdx.hq import TdxHq_API

logger = logging.getLogger(__name__)

# TDX server pool — fallback IPs used when app.config is not importable
# (e.g. standalone script usage outside the app package).
# When running within the app, these are overridden by app.config.tdx_servers.
_TDX_FALLBACK_SERVERS: list[tuple[str, int]] = [
    ("119.147.212.81", 7709),  # 广东电信
    ("119.147.164.60", 7709),  # 深圳电信备用
    ("202.108.153.230", 7709), # 北京联通
    ("210.51.158.180", 7709),  # 上海联通
    ("59.175.238.38", 7709),   # 武汉电信
    ("113.108.212.139", 7709), # 广州电信
]


def _load_server_pool() -> list[tuple[str, int]]:
    """Load TDX server pool, preferring app.config if available."""
    try:
        from app.config.tdx_servers import get_tdx_servers
        servers = get_tdx_servers()
        return [(s["ip"], int(s["port"])) for s in servers]
    except Exception:
        return _TDX_FALLBACK_SERVERS


class TdxConnectionManager:
    """通达信长连接守护者 (单例模式 + 自动心跳重连 + IP故障转移)"""
    _instance = None
    _init_lock = threading.Lock()
    _last_reconnect_attempt = 0
    _reconnect_cooldown = 10 # 10秒内不重复尝试重连

    def __new__(cls):
        with cls._init_lock:
            if cls._instance is None:
                cls._instance = super(TdxConnectionManager, cls).__new__(cls)
                cls._instance._init()
            return cls._instance

    def _init(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.api = TdxHq_API()
            self.is_connected = False
            
            # 使用服务器列表（优先从 app.config 加载，失败则用内置备用列表）
            self.server_pool = _load_server_pool()
            self.current_server_idx = 0

            self.data_lock = threading.RLock()
            self._start_heartbeat()
            self._reconnect() # 初始化时尝试连接一次

    def _start_heartbeat(self):
        """启动后台心跳线程，保持连接活跃并检测断开"""
        def heartbeat_loop():
            while True:
                time.sleep(60)  # 每分钟发送一次心跳
                with self.data_lock:
                    if self.is_connected:
                        try:
                            # 发送一个轻量级请求作为心跳
                            self.api.get_market_gn_list()
                        except Exception:
                            # print("💔 TDX 心跳失败，连接已断开，尝试重连...")
                            self.is_connected = False
                            self._reconnect()
                    else:
                        self._reconnect()
        threading.Thread(target=heartbeat_loop, daemon=True).start()

    def _reconnect(self) -> bool:
        """核心重连机制：遍历 IP 池，直到连接成功"""
        with self.data_lock:
            now = time.time()
            if now - self._last_reconnect_attempt < self._reconnect_cooldown:
                # print(f"🚦 TDX 重连冷却中 ({int(self._reconnect_cooldown - (now - self._last_reconnect_attempt))}s)")
                return self.is_connected

            self._last_reconnect_attempt = now
            # 断开可能残留的僵尸连接
            try: self.api.disconnect()
            except Exception as e: logger.debug("tdx_connect_manager.connect: %s", e)

            for i in range(len(self.server_pool)):
                server = self.server_pool[self.current_server_idx]
                try:
                    self.api.connect(server[0], server[1])
                    self.is_connected = True
                    # print(f"✅ TDX 连接成功: {server[0]}:{server[1]}")
                    return True
                except Exception:
                    # print(f"❌ TDX 连接失败: {server[0]}:{server[1]}")
                    self.is_connected = False
                    self.current_server_idx = (self.current_server_idx + 1) % len(self.server_pool) # 切换服务器
            
            # print("💔 TDX 所有服务器连接均失败。")
            self.is_connected = False
            return False

    def execute(self, func_name: str, *args, **kwargs) -> Any:
        """安全执行 TDX API 调用"""
        with self.data_lock:
            if not self.is_connected:
                self._reconnect()
                if not self.is_connected:
                    raise ConnectionError("TDX 连接失败，无法执行 API 调用。")
            
            # 自动处理接口调用失败或返回空数据的情况
            try:
                func = getattr(self.api, func_name)
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                # print(f"⚠️ TDX API 调用失败 ({func_name}): {e}，尝试重连...")
                self.is_connected = False
                self._reconnect() # 失败后立刻尝试重连
                if self.is_connected: # 重连成功后再次尝试
                    func = getattr(self.api, func_name)
                    return func(*args, **kwargs)
                raise ConnectionError(f"TDX API 调用失败，重连后仍无法恢复: {e}")

    def __del__(self):
        """析构函数中确保连接断开"""
        try: self.api.disconnect()
        except Exception as e: logger.debug("tdx_connect_manager.__del__: %s", e)

# 模块级别的单例访问点 (防止在 MultiSourceMarketProvider 中重复初始化)
tdx_manager_instance = TdxConnectionManager()


if __name__ == '__main__':
    # 测试 TdxConnectionManager
    manager = TdxConnectionManager()
    print("等待 TDX 连接建立...")
    time.sleep(5) # 等待心跳连接

    if manager.is_connected:
        print("TDX 已连接，尝试获取股票列表...")
        try:
            stocks = manager.execute('get_security_list', 1, 0) # 获取上海市场股票列表
            if stocks:
                print(f"成功获取 {len(stocks)} 只股票")
                print(stocks[:5])
            else:
                print("获取股票列表失败或为空。")
        except ConnectionError as e:
            print(f"执行失败: {e}")
    else:
        print("TDX 未连接，请检查网络或服务器状态。")

    print("再次尝试获取 (应复用现有连接)...")
    try:
        stocks = manager.execute('get_security_list', 0, 0) # 获取深圳市场股票列表
        if stocks:
            print(f"成功获取 {len(stocks)} 只股票")
        else:
            print("获取股票列表失败或为空。")
    except ConnectionError as e:
        print(f"执行失败: {e}")
    
    time.sleep(120) # 保持运行，观察心跳
