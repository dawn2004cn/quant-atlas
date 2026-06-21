import os
import sys
import configparser

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

try:
    from app.config import TDX_ROOT_PATH
except ImportError:
    TDX_ROOT_PATH = r"E:\tdx\通达信金融终端(开心果交易版)V2024.02"

class TdxConfigReader:
    def __init__(self, tdx_path: str):
        self.tdx_path = tdx_path
        self.cfg_path = os.path.join(tdx_path, "connect.cfg")

        # strict=False 允许文件中存在重复的键名而不报错
        self.config = configparser.ConfigParser(strict=False)
        self.server_pool = []

        self.ex_server_pool = []

    def parse_hq_servers(self) -> list:
        """
        解析 connect.cfg，提取所有的行情服务器 (HQNode)
        :return: 返回格式为 [(ip, port), (ip, port), ...] 的列表
        """
        if not os.path.exists(self.cfg_path):
            print(f"[ERROR] Config file not found: {self.cfg_path}")
            return []

        # 通达信文件必须使用 gbk 编码读取
        try:
            self.config.read(self.cfg_path, encoding='gbk')
        except UnicodeDecodeError:
            # 兼容极少数被修改过编码的版本
            self.config.read(self.cfg_path, encoding='utf-8')

        #server_pool = []

        #ex_server_pool = []

        # 检查是否存在行情节点
        if 'HQHOST' in self.config:
            hq_nodes = self.config['HQHOST']

            name = ''
            ip = ''
            port = 7709
            # 遍历所有的 Host_XX
            for key, value in hq_nodes.items():
                if key.lower().startswith('hostname'):
                    if name != '':
                        self.server_pool.append({
                            'name': name,
                            'ip': ip,
                            'port': port
                        })
                    name = value
                if key.lower().startswith('ipaddress'):
                    # value 格式通常为: "名称,IP,端口" 或者 "名称,IP,端口,其他参数"
                    ip = value;
                if key.lower().startswith('port'):
                    port = value

        # 检查是否存在行情节点
        if 'DSHOST' in self.config:
            hq_nodes = self.config['DSHOST']

            name = ''
            ip = ''
            port = 7727
            # 遍历所有的 Host_XX
            for key, value in hq_nodes.items():
                if key.lower().startswith('hostname'):
                    if name != '':
                        self.ex_server_pool.append({
                                        'name': name,
                                        'ip': ip,
                                        'port': port
                                    })
                    name = value
                if key.lower().startswith('ipaddress'):
                    # value 格式通常为: "名称,IP,端口" 或者 "名称,IP,端口,其他参数"
                    ip = value;
                if key.lower().startswith('port'):
                    port = value
        return self.ex_server_pool


# ==========================================
# Main entry point
# ==========================================
if __name__ == "__main__":
    print("=" * 60)
    print("TdxConfigReader - Parse connect.cfg")
    print("=" * 60)

    cfg_reader = TdxConfigReader(TDX_ROOT_PATH)
    servers = cfg_reader.parse_hq_servers()

    print(f"\n[OK] Found {len(servers)} HQ server nodes:\n")

    for i, srv in enumerate(servers[:100]):  # 只打印前10个
        print(f"  [{i+1}] Name: {srv['name']:<15} | IP: {srv['ip']:<15} | Port: {srv['port']}")

    # 将其转换为 pytdx 引擎直接可用的 server_pool 格式
    pytdx_pool = [(s['name'],s['ip'], s['port']) for s in servers]
    print(f"\n[INFO] Pytdx connection pool format (first 5):\n  {pytdx_pool[:100]}")
    print("=" * 60)
