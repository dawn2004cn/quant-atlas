import threading
import time
import traceback

from pytdx.exhq  import TdxExHq_API
from sympy import false

from tdx_config_reader import TdxConfigReader

# 收集的高质量通达信行情服务器列表 (含电信、联通、移动多线)
TDX_SERVERS = [
    ('广东电信', '119.147.212.81', 7709),
    ('深圳电信', '119.147.164.60', 7709),
    ('北京联通', '202.108.153.230', 7709),
    ('上海联通', '210.51.158.180', 7709),
    ('武汉电信', '59.175.238.38', 7709),
    ('广州电信', '113.108.212.139', 7709),
    ('南京电信', '218.2.102.37', 7709),
    ('成都电信', '125.64.12.123', 7709),
    ('上海电信主站Z80','180.153.18.172',7709),
    ('test','101.227.73.20',7709)
]
best_server = []
TDX_ROOT_PATH = r"E:\tdx\通达信金融终端(开心果交易版)V2024.02"
class TdxBestServersConnect:

    def __init__(self, tdx_path: str):
        self.tdx_path = tdx_path
        self.tdx_cfg_reader = TdxConfigReader(TDX_ROOT_PATH)

        # strict=False 允许文件中存在重复的键名而不报错
        self.parse_hq_servers = self.tdx_cfg_reader.parse_hq_servers()
        #print(self.parse_hq_servers)
        self.api = TdxExHq_API(raise_exception=False)
        self.server_pool = [(s['name'], s['ip'], s['port']) for s in self.parse_hq_servers]
        #self.server_pool.extend(TDX_SERVERS)
        self.is_connection = false
        self.best_server = []

    def __del__(self):
        if self.is_connection:
            self.api.disconnect()


    def test_server(self,name, ip, port):
        start_time = time.time()
        try:
            print(name,ip,port)
            # 设置 1 秒超时，避免阻塞
            if self.api.connect(ip, int(port), time_out=3):
                # 模拟获取一次市场股票数量，确保业务通畅
                #count = self.api.get_markets(0)
                df = self.api.to_df(self.api.get_markets())
                end_time = time.time()
                duration = (end_time - start_time) * 1000  # 转为毫秒
                if not df.empty:
                    self.best_server.append({'name': name, 'ip': ip, 'port': int(port), 'ms': duration})
                self.api.disconnect()
        except Exception as e:
            traceback.print_exc()
            print(f"连接服务器 {name} ({ip}:{port}) 失败",e)
            pass


    def get_best_tdx_server(self):
        threads = []
        print("正在优选服务器，请稍候...")
        for name,ip,port in self.server_pool:
            self.test_server(name, ip, port)
        # 按延迟从小到大排序
        sorted_servers = sorted(self.best_server, key=lambda x: x['ms'])

        print("\n--- 优选结果 ---")
        for idx, s in enumerate(sorted_servers):
            print(f"[{idx + 1}] {s['name']}: {s['ip']}:{s['port']} | 延迟: {s['ms']:.2f}ms")

        return sorted_servers if sorted_servers else None



if __name__ == "__main__":
    cls = TdxBestServersConnect(TDX_ROOT_PATH)
    best = cls.get_best_tdx_server()
    if best:
        print(best)
        #print(f"\n推荐使用: {best['name']} ({best['ip']})")