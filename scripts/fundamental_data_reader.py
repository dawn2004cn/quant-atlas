import akshare as ak
import pandas as pd


class FundamentalDataReader:
    """深度基本面与股东数据读取器 (基于 AKShare)"""

    @staticmethod
    def get_top10_shareholders(stock_code: str, date: str = None) -> pd.DataFrame:
        """
        获取十大流通股东明细
        :param stock_code: 纯代码，如 '600519'
        :param date: 财报日期，如 '20230930'。如果不传，返回最新。
        """
        try:
            # 东方财富接口：获取十大流通股东
            df = ak.stock_gdfx_top_10_em(symbol=stock_code, date=date)
            if df.empty:
                return df

            # 清洗并返回核心列
            columns_needed = ['报告期', '股东名称', '持股数', '持股比例', '增减', '股份类型']
            df = df[columns_needed].copy()
            return df
        except Exception as e:
            print(f"获取股东数据失败: {e}")
            return pd.DataFrame()

    @staticmethod
    def get_financial_report(stock_code: str) -> pd.DataFrame:
        """
        获取历史核心财务指标 (用于计算利润增长率等)
        包含：每股收益、营业收入、净利润、净资产收益率(ROE)等
        """
        try:
            # 新浪接口：获取财务主要指标
            df = ak.stock_financial_abstract(symbol=stock_code)
            return df
        except Exception as e:
            print(f"获取财报数据失败: {e}")
            return pd.DataFrame()


# 运行测试
if __name__ == "__main__":
    ticker = "600519"  # 贵州茅台

    print(f"=== 1. 获取 {ticker} 最新十大流通股东 ===")
    df_shareholders = FundamentalDataReader.get_top10_shareholders(ticker)
    if not df_shareholders.empty:
        print(df_shareholders.head(5).to_string())

    print(f"\n=== 2. 获取 {ticker} 历史财务核心指标 ===")
    df_finance = FundamentalDataReader.get_financial_report(ticker)
    if not df_finance.empty:
        print(df_finance[['截止日期', '每股收益', '净利润', '净利润同比增长率']].head(4).to_string())