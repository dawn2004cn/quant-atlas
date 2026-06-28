import logging
import time

from pytdx.exhq import TdxExHq_API
from pytdx.hq import TdxHq_API

logger = logging.getLogger(__name__)

from app.config.tdx_servers import get_tdx_ex_servers, get_tdx_servers

TDX_SERVERS = get_tdx_servers()
TDX_EX_SERVERS = get_tdx_ex_servers()

class TdxBestServersConnect:
    """通达信行情服务器优选工具"""

    def __init__(self):
        self.api = TdxHq_API(raise_exception=False)
        self.api_ex = TdxExHq_API(raise_exception=False)
        self.server_pool = TDX_SERVERS
        self.server_ex_pool = TDX_EX_SERVERS
        self.best_servers = []
        self.best_servers_ex = []

    def test_server(self, name, ip, port):
        start_time = time.time()
        try:
            # 设置 3 秒超时，避免阻塞
            if self.api.connect(ip, int(port), time_out=3):
                # 模拟获取一次市场股票数量
                count = self.api.get_security_count(0)
                end_time = time.time()
                duration = (end_time - start_time) * 1000
                if count > 0:
                    self.best_servers.append({'name': name, 'ip': ip, 'port': int(port), 'ms': duration})
                self.api.disconnect()
        except Exception as e:
            logger.warning("tdx_selector.py.test_server: %s", e)
    def test_server_ex(self, name, ip, port):
        start_time = time.time()
        try:
            # 设置 3 秒超时，避免阻塞
            if self.api_ex.connect(ip, int(port), time_out=3):
                # 模拟获取一次市场股票数量
                df = self.api_ex.to_df(self.api_ex.get_markets())
                end_time = time.time()
                duration = (end_time - start_time) * 1000
                if not df.empty:
                    self.best_servers_ex.append({'name': name, 'ip': ip, 'port': int(port), 'ms': duration})
                self.api_ex.disconnect()
        except Exception as e:
            logger.warning("tdx_selector.py.test_server_ex: %s", e)

    def get_best_tdx_servers(self):
        """返回按延迟排序的服务器列表"""
        self.best_servers = []
        #for name, ip, port in self.server_pool:
        for _idx, s in enumerate(self.server_pool):
            self.test_server(s['name'], s['ip'], s['port'])

        return sorted(self.best_servers, key=lambda x: x['ms'])
# ==========================================
# 🚀 运行验证：不复权 vs 前复权
# ==========================================
if __name__ == "__main__":
    tdxServer = TdxBestServersConnect()
    tdxServer.get_best_tdx_servers()
    print(tdxServer.best_servers)
