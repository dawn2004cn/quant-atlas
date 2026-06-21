
from abc import ABC, abstractmethod
# ==========================================
# 2. 选股模型基类 (抽象层 - 依赖倒置 & 开闭原则)
# ==========================================
class BaseSelectionModel(ABC):
    """选股模型抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """模型名称"""
        pass

    @abstractmethod
    def evaluate(self, df: pd.DataFrame, indicators: AdvancedIndicators) -> Optional[Dict]:
        """
        评估函数：对传入的数据进行评估
        :param df: 标准化的历史K线数据 (列名为小写 open, high, low, close, volume)
        :param indicators: 指标计算工具类
        :return: 若未选中返回 None；若选中返回 Dict 包含得分和理由
        """
        pass