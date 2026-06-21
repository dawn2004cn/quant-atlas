import akshare as ak


class EastMoneyRealTimeReader:
    """东方财富全市场实时快照 (AKShare)"""

    def get_all_market_realtime(self):
        try:
            print("正在从东方财富拉取全市场实时快照...")
            # 接口: stock_zh_a_spot_em 返回东方财富网站上的最新A股实时行情
            df = ak.stock_zh_a_spot_em()

            # 返回包含了: 代码, 名称, 最新价, 涨跌幅, 成交量, 成交额, 换手率 等等
            return df
        except Exception as e:
            print(f"AKShare 获取失败: {e}")
            return pd.DataFrame()


if __name__ == "__main__":
    reader = EastMoneyRealTimeReader()
    df_all = reader.get_all_market_realtime()
    print(f"\n=== 东方财富全市场实时快照 (共 {len(df_all)} 只股票) ===")
    # 打印涨幅榜前 5 名
    top_5 = df_all.sort_values(by='涨跌幅', ascending=False).head(5)
    print(top_5[['代码', '名称', '最新价', '涨跌幅', '成交额']].to_string())