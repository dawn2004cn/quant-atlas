import pandas as pd



from app.core.logger import get_logger

logger = get_logger(__name__)


class HolyGrailEnsembleEngine:
    """
    量化核心：多策略共振投票引擎 (Ensemble Voting Engine)
    """

    def __init__(self):
        # 挂载的策略武器库
        self.active_strategies = []

    def load_models(self, strategy_list: list):
        """
        动态挂载策略组合
        :param strategy_list: 策略实例的列表
        """
        self.active_strategies = strategy_list
        logger.info("引擎已成功挂载 %s 个量化模型", len(self.active_strategies))

    def evaluate_single_stock(self, df: pd.DataFrame) -> dict | None:
        """
        让所有激活的策略对单只股票进行体检打分
        """
        if df is None or df.empty:
            return None

        buy_votes = 0
        triggered_details = []
        valid_strategies_count = 0

        for strategy in self.active_strategies:
            # 1. 检查数据长度是否满足该策略的最少预热要求
            if len(df) < strategy.get_start_idx():
                continue

            valid_strategies_count += 1

            try:
                # 2. 调用策略生成信号 (传入 df 的副本防止数据污染)
                sig_df = strategy.generate_signals(df.copy())

                # 3. 检查最后一天是否触发了买入信号 (Signal == 1)
                if sig_df['Signal'].iloc[-1] == 1:
                    buy_votes += 1
                    triggered_details.append(f"[{strategy.category}] {strategy.name}")
            except Exception:
                # 容错机制：某个策略即便写错了或缺少字段，不能让整个引擎崩溃
                # print(f"⚠️ 策略 {strategy.name} 执行异常: {e}")
                continue

        # 如果没有策略适用，或没有触发任何买点，返回 None
        if valid_strategies_count == 0 or buy_votes == 0:
            return None

        # 4. 计算综合共振置信度得分 (满分 100)
        # 公式：触发买入的策略数 / 参与体检的策略总数
        confidence_score = round((buy_votes / valid_strategies_count) * 100, 1)

        return {
            "score": confidence_score,
            "vote_count": f"{buy_votes}/{valid_strategies_count}",
            "triggered_models": " | ".join(triggered_details)
        }

    def run_market_scan(self, stock_data_dict: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        执行全市场极速扫描
        :param stock_data_dict: 字典格式 {'sh600519': df_maotai, 'sz000001': df_pingan, ...}
        :return: 包含选股结果的报表 DataFrame
        """
        logger.info("开始全市场扫描，共计 %s 只标的", len(stock_data_dict))
        results = []

        for ticker, df in stock_data_dict.items():
            res = self.evaluate_single_stock(df)

            if res is not None:
                results.append({
                    "代码": ticker,
                    "最新收盘价": round(df['Close'].iloc[-1], 2),
                    "共振得分": res['score'],
                    "触发策略数": res['vote_count'],
                    "主力买入逻辑": res['triggered_models']
                })

        # 将结果汇总为 Pandas DataFrame 并按得分降序排列
        report_df = pd.DataFrame(results)
        if not report_df.empty:
            report_df = report_df.sort_values(by="共振得分", ascending=False).reset_index(drop=True)

        return report_df
