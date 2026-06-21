import yfinance as yf
import pandas as pd
import numpy as np
import ta
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import warnings

warnings.filterwarnings('ignore')

class MLTradingProject:
    def __init__(self, ticker="SPY", start_date="2015-01-01", end_date="2024-01-01"):
        self.ticker = ticker
        self.start_date = start_date
        self.end_date = end_date
        self.df = None
        self.model = None
        self.features = None

    def fetch_data(self):
        """1. 获取数据"""
        print(f"📥 正在下载 {self.ticker} 数据...")
        df = yf.download(self.ticker, start=self.start_date, end=self.end_date, progress=False)

        # 处理 yfinance 多重索引列的问题
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel('Ticker')

        # 确保列名是标准格式
        self.df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        print(f"✅ 数据下载完成，共 {len(self.df)} 条记录。")

    def feature_engineering(self):
        """2. 特征工程：生成 ta 库的所有 100+ 个指标"""
        print("⚙️ 正在生成 100+ 个 TA 特征...")

        # 使用 ta 库一键添加所有特征
        self.df = ta.add_all_ta_features(
            self.df, open="Open", high="High", low="Low", close="Close", volume="Volume", fillna=False
        )

        # 3. 定义目标标签 (Target Label)
        # 预测下一天的收益率，如果 > 0 则为 1 (做多)，否则为 0 (空仓/做空)
        self.df['Next_Day_Return'] = self.df['Close'].shift(-1) / self.df['Close'] - 1
        self.df['Target'] = (self.df['Next_Day_Return'] > 0).astype(int)

        # 保存基准每日收益率用于后续回测
        self.df['Daily_Return'] = self.df['Close'].pct_change()

        # 清洗数据：删除因为计算指标产生的 NaN 和缺失的目标值（最后一天）
        self.df.replace([np.inf, -np.inf], np.nan, inplace=True)
        self.df.dropna(inplace=True)

        # 获取所有的特征列名 (排除原始行情列和目标列)
        exclude_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'Next_Day_Return', 'Target', 'Daily_Return']
        self.features = [col for col in self.df.columns if col not in exclude_cols]
        print(f"✅ 特征工程完成，最终用于训练的特征数量: {len(self.features)}个。")

    def train_model(self):
        """4. 划分训练/测试集并训练模型"""
        print("🧠 正在训练随机森林模型...")

        # 必须按时间顺序划分，绝不能随机打乱 (防止未来函数)
        split_idx = int(len(self.df) * 0.8)  # 80% 训练，20% 测试

        train_data = self.df.iloc[:split_idx]
        test_data = self.df.iloc[split_idx:]

        X_train = train_data[self.features]
        y_train = train_data['Target']

        X_test = test_data[self.features]
        y_test = test_data['Target']

        # 初始化随机森林分类器
        # class_weight='balanced' 解决牛市中“涨”多于“跌”的样本不平衡问题
        # min_samples_leaf=50 防止叶子节点过少导致的严重过拟合
        self.model = RandomForestClassifier(
            n_estimators=200,
            max_depth=7,
            min_samples_leaf=50,
            class_weight='balanced',
            random_state=42,
            n_jobs=-1
        )

        self.model.fit(X_train, y_train)

        # 预测与评估
        y_pred = self.model.predict(X_test)
        print("✅ 模型训练完成！测试集评估报告:")
        print(classification_report(y_test, y_pred))

        # 保存预测结果到 DataFrame
        self.df.loc[test_data.index, 'Prediction'] = y_pred
        # 获取预测上涨的概率
        self.df.loc[test_data.index, 'Prob_Up'] = self.model.predict_proba(X_test)[:, 1]

        # 输出最重要的10个特征
        importances = pd.Series(self.model.feature_importances_, index=self.features)
        print("\n🏆 Top 10 最重要的指标特征:")
        print(importances.nlargest(10))

    def run_strategy_backtest(self):
        """5. 策略回测: 根据模型特征做出交易决策"""
        print("\n📈 正在执行策略回测...")

        # 仅截取测试集部分进行回测
        backtest_df = self.df.dropna(subset=['Prediction']).copy()

        # ----------------------------------------------------
        # 💡 核心买卖决策规则：
        # 1. 传统做法：如果 Prediction == 1 就买入。
        # 2. 高收益改进做法：模型不仅输出 0/1，还输出上涨的概率 (Prob_Up)。
        # ----------------------------------------------------
        # 💡 核心买卖决策规则：
        # 1. 传统做法：如果 Prediction == 1 就买入。
        # 2. 高收益改进做法：模型不仅输出 0/1，还输出上涨的概率 (Prob_Up)。
        #
        # 为了达到【回测收益率最高】且控制风险，我们设定一个概率阈值（例如 > 0.55 才买入）。
        # 这能大幅过滤掉模型“勉强预测会上涨”的弱信号，减少频繁交易带来的磨损，提高胜率。
        #
        # 交易动作：
        # - 当模型预测明天上涨概率 > 0.55 时，全仓做多 (Position = 1)
        # - 否则，空仓观望避险 (Position = 0)
        # ----------------------------------------------------

        entry_threshold = 0.55

        # 设定每天的仓位 (0代表空仓，1代表满仓)
        backtest_df['Position'] = np.where(backtest_df['Prob_Up'] > entry_threshold, 1, 0)

        # 计算策略的每日收益
        # 逻辑：今天的仓位 (Position) 乘上 今天的 Next_Day_Return（也就是明天的实际涨跌幅）
        backtest_df['Strategy_Return'] = backtest_df['Position'] * backtest_df['Next_Day_Return']

        # 计算基准的每日收益 (一直满仓持有)
        backtest_df['Benchmark_Return'] = backtest_df['Next_Day_Return']

        # 计算累计收益 (Cumulative Returns)
        backtest_df['Cum_Strategy'] = (1 + backtest_df['Strategy_Return']).cumprod()
        backtest_df['Cum_Benchmark'] = (1 + backtest_df['Benchmark_Return']).cumprod()

        # 提取最终评估指标
        total_strategy_return = backtest_df['Cum_Strategy'].iloc[-1] - 1
        total_benchmark_return = backtest_df['Cum_Benchmark'].iloc[-1] - 1

        # 计算策略胜率
        winning_trades = backtest_df[(backtest_df['Position'] == 1) & (backtest_df['Next_Day_Return'] > 0)]
        total_trades = backtest_df[backtest_df['Position'] == 1]
        win_rate = len(winning_trades) / len(total_trades) if len(total_trades) > 0 else 0

        print("-" * 40)
        print(f"💰 基准累计收益 (Buy & Hold): {total_benchmark_return * 100:.2f}%")
        print(f"🚀 机器学习策略累计收益:   {total_strategy_return * 100:.2f}%")
        print(f"🎯 策略胜率 (胜次/总出手):   {win_rate * 100:.2f}% | 交易天数: {len(total_trades)} / {len(backtest_df)}")
        print("-" * 40)

        # 绘制收益曲线对比图
        try:
            plt.figure(figsize=(12, 6))
            plt.plot(backtest_df.index, backtest_df['Cum_Strategy'], label='ML Strategy (Prob > 0.55)', color='red',
                     linewidth=2)
            plt.plot(backtest_df.index, backtest_df['Cum_Benchmark'], label='Benchmark (Buy & Hold)', color='gray',
                     alpha=0.7)
            plt.title(f"[{self.ticker}] ML Trading Strategy vs Benchmark Returns")
            plt.xlabel("Date")
            plt.ylabel("Cumulative Return (1.0 = 100%)")
            plt.legend()
            plt.grid(True)
            plt.show()
        except Exception as e:
            print("绘图失败 (如果不在 Jupyter/GUI 环境中可忽略):", e)

        return backtest_df

# ==========================================
# 主执行入口
# ==========================================
if __name__ == "__main__":
    # 我们以苹果公司(AAPL) 过去几年的数据为例
    # 你可以修改为 TSLA, SPY (标普500), 或 000300.SS (沪深300)
    project = MLTradingProject(ticker="AAPL", start_date="2018-01-01", end_date="2024-01-01")

    # 依次执行流程
    project.fetch_data()  # 1. 获取数据
    project.feature_engineering()  # 2. 灌入 100+ ta 特征
    project.train_model()  # 3. 训练随机森林并查看特征重要性
    result_df = project.run_strategy_backtest()  # 4. 回测并出图