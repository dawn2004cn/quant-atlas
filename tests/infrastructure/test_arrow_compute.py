"""Arrow Compute 集成测试."""

import numpy as np
import pytest


class TestArrowClient:
    """Arrow 计算客户端测试"""

    def test_import_client(self):
        """测试导入客户端"""
        try:
            from app.infrastructure.compute.arrow_client import ArrowComputeClient, get_arrow_client
            assert ArrowComputeClient is not None
        except ImportError as e:
            pytest.skip(f"Import error: {e}")

    def test_create_client(self):
        """测试创建客户端"""
        try:
            from app.infrastructure.compute.arrow_client import ArrowComputeClient
            client = ArrowComputeClient(use_flight=False)
            assert client is not None
        except ImportError:
            pytest.skip("Module not available")

    def test_sma_fallback(self):
        """测试 SMA 后备实现"""
        try:
            from app.infrastructure.compute.arrow_client import ArrowComputeClient

            client = ArrowComputeClient(use_flight=False)

            # 创建测试数据
            data = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])

            # 计算 SMA
            result = client.calculate_sma(data, window=3)

            # 验证结果
            assert len(result) == len(data)
            assert result[2] == 2.0  # (1+2+3)/3
            assert result[3] == 3.0  # (2+3+4)/3

        except ImportError:
            pytest.skip("Module not available")

    def test_ema_fallback(self):
        """测试 EMA 后备实现"""
        try:
            from app.infrastructure.compute.arrow_client import ArrowComputeClient

            client = ArrowComputeClient(use_flight=False)

            data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])

            result = client.calculate_ema(data, window=3)

            assert len(result) == len(data)
            assert result[0] == 1.0  # 第一个值保持

        except ImportError:
            pytest.skip("Module not available")

    def test_zscore_fallback(self):
        """测试 Z-Score 后备实现"""
        try:
            from app.infrastructure.compute.arrow_client import ArrowComputeClient

            client = ArrowComputeClient(use_flight=False)

            # 固定数据便于验证
            data = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])

            result = client.calculate_zscore(data, window=5)

            assert len(result) == len(data)

        except ImportError:
            pytest.skip("Module not available")

    def test_batch_calculate(self):
        """测试批量计算"""
        try:
            from app.infrastructure.compute.arrow_client import ArrowComputeClient

            client = ArrowComputeClient(use_flight=False)

            data = np.arange(100.0)

            indicators = ["sma_5", "sma_10", "ema_5", "zscore_10"]

            results = client.batch_calculate(data, indicators)

            assert "sma_5" in results
            assert "sma_10" in results
            assert "ema_5" in results
            assert "zscore_10" in results

            # 验证形状一致
            for ind, arr in results.items():
                assert arr.shape == data.shape

        except ImportError:
            pytest.skip("Module not available")


class TestArrowMemoryPool:
    """Arrow 内存池测试"""

    def test_allocate(self):
        """测试内存分配"""
        try:
            from app.infrastructure.compute.arrow_client import ArrowMemoryPool

            pool = ArrowMemoryPool(max_size_mb=10)

            arr = pool.allocate((100, 100))

            assert arr.shape == (100, 100)
            assert arr.dtype == np.float64

        except ImportError:
            pytest.skip("Module not available")

    def test_release(self):
        """测试内存回收"""
        try:
            from app.infrastructure.compute.arrow_client import ArrowMemoryPool

            pool = ArrowMemoryPool(max_size_mb=10)

            arr = pool.allocate((50, 50))
            pool.release(arr)

            stats = pool.stats()

            assert "hits" in stats
            assert "misses" in stats

        except ImportError:
            pytest.skip("Module not available")


class TestZeroCopyFunctions:
    """零拷贝函数测试 (如果可用)"""

    def test_sma_zero_copy_import(self):
        """测试零拷贝函数导入"""
        try:
            from quant_core import calculate_sma_zero_copy
            assert calculate_sma_zero_copy is not None
        except ImportError:
            pytest.skip("Rust core not built")

    def test_sma_zero_copy_call(self):
        """测试零拷贝函数调用"""
        try:
            from quant_core import calculate_sma_zero_copy
            import numpy as np

            data = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)

            result = calculate_sma_zero_copy(data, 3)

            assert len(result) == 5

        except ImportError:
            pytest.skip("Rust core not built")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])