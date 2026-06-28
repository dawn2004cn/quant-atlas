from __future__ import annotations

"""Arrow Flight Client - 零拷贝计算客户端。

基于 Apache Arrow Flight 协议与 Rust 计算引擎通信。
支持:
- 零拷贝数据传输 (PyO3 Buffer 协议)
- 批量指标计算
- 回测数据管道
"""


from dataclasses import dataclass

import numpy as np

# Arrow 相关导入 (可选)
try:
    import pyarrow as pa
    import pyarrow.flight as flight
    ARROW_AVAILABLE = True
except ImportError:
    ARROW_AVAILABLE = False

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ComputeResult:
    """计算结果"""
    data: np.ndarray
    indicator_name: str
    execution_time_ms: float
    metadata: dict


class ArrowComputeClient:
    """Arrow Flight 计算客户端

    使用两种模式:
    1. 直接调用 (Zero-Copy): 使用 PyO3 Buffer 协议
    2. Flight 模式: 通过 gRPC 调用远程服务
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8815,
        use_flight: bool = False,
    ):
        self._host = host
        self._port = port
        self._use_flight = use_flight and ARROW_AVAILABLE
        self._client = None
        self._connected = False

        if self._use_flight:
            try:
                self._client = flight.connect(f"grpc://{host}:{port}")
                self._connected = True
                logger.info(f"Connected to Arrow Flight server at {host}:{port}")
            except Exception as e:
                logger.warning(f"Flight connection failed: {e}, falling back to direct calls")

    def is_connected(self) -> bool:
        return self._connected or not self._use_flight

    # ========== 零拷贝计算 (直接调用 Rust) ==========

    def calculate_sma(self, data: np.ndarray, window: int) -> np.ndarray:
        """计算 SMA (零拷贝)"""
        if not ARROW_AVAILABLE:
            return self._calculate_sma_fallback(data, window)

        try:
            from quant_core import calculate_sma_zero_copy
            # 直接传递 numpy 数组的内存 (零拷贝)
            result = calculate_sma_zero_copy(data, window)
            return np.array(result, dtype=np.float64)
        except ImportError:
            return self._calculate_sma_fallback(data, window)

    def calculate_ema(self, data: np.ndarray, window: int) -> np.ndarray:
        """计算 EMA (零拷贝)"""
        if not ARROW_AVAILABLE:
            return self._calculate_ema_fallback(data, window)

        try:
            from quant_core import calculate_ema_zero_copy
            result = calculate_ema_zero_copy(data, window)
            return np.array(result, dtype=np.float64)
        except ImportError:
            return self._calculate_ema_fallback(data, window)

    def calculate_atr(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        window: int = 14,
    ) -> np.ndarray:
        """计算 ATR (零拷贝)"""
        if not ARROW_AVAILABLE:
            return self._calculate_atr_fallback(highs, lows, closes, window)

        try:
            from quant_core import calculate_atr_zero_copy
            result = calculate_atr_zero_copy(highs, lows, closes, window)
            return np.array(result, dtype=np.float64)
        except ImportError:
            return self._calculate_atr_fallback(highs, lows, closes, window)

    def calculate_zscore(self, data: np.ndarray, window: int = 20) -> np.ndarray:
        """计算 Z-Score (零拷贝)"""
        if not ARROW_AVAILABLE:
            return self._calculate_zscore_fallback(data, window)

        try:
            from quant_core import calculate_zscore_zero_copy
            result = calculate_zscore_zero_copy(data, window)
            return np.array(result, dtype=np.float64)
        except ImportError:
            return self._calculate_zscore_fallback(data, window)

    def batch_calculate(
        self,
        data: np.ndarray,
        indicators: list[str],
    ) -> dict[str, np.ndarray]:
        """批量计算指标 (零拷贝)"""
        if not ARROW_AVAILABLE:
            return self._batch_calculate_fallback(data, indicators)

        try:
            from quant_core import batch_calculate_zero_copy
            results = batch_calculate_zero_copy(data, indicators)
            return {
                ind: np.array(res, dtype=np.float64)
                for ind, res in zip(indicators, results)
            }
        except ImportError:
            return self._batch_calculate_fallback(data, indicators)

    # ========== Flight 模式 (远程调用) ==========

    def _flight_calculate(self, endpoint: str, data: np.ndarray) -> np.ndarray:
        """通过 Flight 调用远程计算"""
        if not self._client:
            raise RuntimeError("Flight client not connected")

        # 转换为 Arrow 格式
        arr = pa.array(data, type=pa.float64())
        table = pa.table({"data": arr})

        # 序列化
        buffer = pa.BufferOutputStream()
        with pa.ipc.new_file(buffer, table.schema) as writer:
            writer.write_table(table)
        buffer.getvalue().to_pybytes()

        # 发送请求
        ticket = flight.Ticket(endpoint.encode())
        self._client.get_ticket(ticket)
        # 注意: 实际应该使用 do_get，这里简化处理

        logger.info(f"Flight request sent to {endpoint}")
        return data  # 简化返回

    # ========== Fallback 实现 (纯 Python) ==========

    def _calculate_sma_fallback(self, data: np.ndarray, window: int) -> np.ndarray:
        """SMA 后备实现"""
        result = np.zeros_like(data)
        for i in range(len(data)):
            if i >= window - 1:
                result[i] = np.mean(data[i - window + 1:i + 1])
        return result

    def _calculate_ema_fallback(self, data: np.ndarray, window: int) -> np.ndarray:
        """EMA 后备实现"""
        alpha = 2 / (window + 1)
        result = np.zeros_like(data)
        result[0] = data[0]
        for i in range(1, len(data)):
            result[i] = data[i] * alpha + result[i - 1] * (1 - alpha)
        return result

    def _calculate_atr_fallback(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        window: int,
    ) -> np.ndarray:
        """ATR 后备实现"""
        tr = np.zeros_like(highs)
        tr[0] = highs[0] - lows[0]
        for i in range(1, len(highs)):
            hl = highs[i] - lows[i]
            hpc = abs(highs[i] - closes[i - 1])
            lpc = abs(lows[i] - closes[i - 1])
            tr[i] = max(hl, hpc, lpc)

        # 计算 SMA
        result = np.zeros_like(tr)
        for i in range(len(tr)):
            if i >= window - 1:
                result[i] = np.mean(tr[i - window + 1:i + 1])
        return result

    def _calculate_zscore_fallback(self, data: np.ndarray, window: int) -> np.ndarray:
        """Z-Score 后备实现"""
        result = np.zeros_like(data)
        for i in range(len(data)):
            if i >= window - 1:
                slice_data = data[i - window + 1:i + 1]
                mean = np.mean(slice_data)
                std = np.std(slice_data)
                if std > 0:
                    result[i] = (data[i] - mean) / std
        return result

    def _batch_calculate_fallback(
        self,
        data: np.ndarray,
        indicators: list[str],
    ) -> dict[str, np.ndarray]:
        """批量计算后备实现"""
        results = {}
        for ind in indicators:
            if "sma" in ind:
                window = int(ind.split("_")[1])
                results[ind] = self._calculate_sma_fallback(data, window)
            elif "ema" in ind:
                window = int(ind.split("_")[1])
                results[ind] = self._calculate_ema_fallback(data, window)
            elif "zscore" in ind:
                window = int(ind.split("_")[1])
                results[ind] = self._calculate_zscore_fallback(data, window)
            else:
                results[ind] = np.zeros_like(data)
        return results


class ArrowMemoryPool:
    """Arrow 内存池 - 避免频繁分配/释放

    用于高频计算场景，减少 GC 压力。
    """

    def __init__(self, max_size_mb: int = 100):
        self._max_size = max_size_mb * 1024 * 1024
        self._pools: dict[int, list[np.ndarray]] = {}  # size -> list of arrays
        self._stats = {"hits": 0, "misses": 0}

    def allocate(self, shape: tuple, dtype: np.dtype = np.float64) -> np.ndarray:
        """从池中分配数组"""
        size = np.prod(shape) * np.dtype(dtype).itemsize

        if size in self._pools and self._pools[size]:
            self._stats["hits"] += 1
            arr = self._pools[size].pop()
            arr.fill(0)  # 重置
            return arr.reshape(shape)

        self._stats["misses"] += 1
        return np.zeros(shape, dtype=dtype)

    def release(self, arr: np.ndarray) -> None:
        """回收数组到池"""
        size = arr.nbytes
        if size not in self._pools:
            self._pools[size] = []

        # 限制池大小
        total_size = sum(np.prod(a.shape) * a.itemsize for pools in self._pools.values() for a in pools)
        if total_size + size > self._max_size:
            return  # 丢弃

        self._pools[size].append(arr)

    def stats(self) -> dict:
        return {
            **self._stats,
            "hit_rate": self._stats["hits"] / max(self._stats["hits"] + self._stats["misses"], 1),
        }


# 全局客户端实例
_default_client: ArrowComputeClient | None = None


def get_arrow_client(
    host: str = "localhost",
    port: int = 8815,
    use_flight: bool = False,
) -> ArrowComputeClient:
    """获取全局 Arrow 客户端"""
    global _default_client
    if _default_client is None:
        _default_client = ArrowComputeClient(host, port, use_flight)
    return _default_client
