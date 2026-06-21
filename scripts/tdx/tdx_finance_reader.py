import pandas as pd
from pytdx.hq import TdxHq_API


class TdxFinanceReader:
    def __init__(self):
        self.api = TdxHq_API()

    def get_finance_snapshot(self, stock_code: str) -> dict:
        """
        获取通达信最新一期的财务快照数据
        :param stock_code: 例如 'sz000001'
        """
        market = 0 if stock_code.startswith('sz') else 1
        code = stock_code[2:]

        try:
            # 连接通达信行情服务器
            with self.api.connect('119.147.212.81', 7709):
                data = self.api.get_finance_info(market, code)

            if not data:
                return {}

            # 通达信返回的是一个包含众多字段的字典，我们提取最核心的指标
            # 注意：通达信返回的金额单位通常是 "万" 或者是绝对值，需要自己核对量级
            finance_dict = {
                '代码': stock_code,
                '总股本(万股)': data.get('zongguben', 0),
                '流通股本(万股)': data.get('liutongguben', 0),
                '每股收益(EPS)': data.get('meigushouyi', 0),
                '每股净资产(BPS)': data.get('meigujingzichan', 0),
                '净利润(万元)': data.get('jinglirun', 0),
                '主营营业收入(万元)': data.get('zhuyingyewushouru', 0),
                '更新日期': data.get('updatedate', '')  # 例如 20230930 代表三季报
            }
            return finance_dict

        except Exception as e:
            print(f"获取财务数据失败: {e}")
            return {}


# 运行测试
if __name__ == "__main__":
    reader = TdxFinanceReader()
    print("正在拉取 贵州茅台 (sh600519) 的最新财务快照...")
    fin_data = reader.get_finance_snapshot("sh600519")
    for k, v in fin_data.items():
        print(f"{k}: {v}")