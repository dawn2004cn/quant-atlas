"""Strategy Pool Tests."""

import pytest

from app.domain.strategies.pool import StrategyPool, PoolConfig, TenantContext
from app.domain.strategies.pool import ResourceManager, ResourceLimit
from app.domain.strategies.plugin import StrategyPlugin, PluginMetadata, PluginConfig, PluginState


class TestStrategyPool:
    """策略池测试"""

    def test_register_tenant(self):
        pool = StrategyPool()
        tenant = TenantContext(tenant_id="tenant1", name="Test Tenant")
        result = pool.register_tenant(tenant)
        assert result is True

    def test_create_instance(self):
        pool = StrategyPool()
        pool.register_tenant(TenantContext(tenant_id="t1", name="T1"))

        class TestPlugin(StrategyPlugin):
            @property
            def metadata(self):
                return PluginMetadata(id="test", name="Test", version="1.0")
            def on_load(self): return True
            def on_unload(self): return True
            def on_init(self, c): return True
            def on_start(self): return True
            def on_stop(self): return True
            def on_update(self, p): return True
            def analyze(self, d): return type('R', (), {'signals': []})()

        plugin = TestPlugin()
        instance = pool.create_instance("t1", plugin)

        assert instance is not None
        assert instance.tenant_id == "t1"

    def test_destroy_instance(self):
        pool = StrategyPool()
        pool.register_tenant(TenantContext(tenant_id="t1", name="T1"))

        class TestPlugin(StrategyPlugin):
            @property
            def metadata(self):
                return PluginMetadata(id="test", name="Test", version="1.0")
            def on_load(self): return True
            def on_unload(self): return True
            def on_init(self, c): return True
            def on_start(self): return True
            def on_stop(self): return True
            def on_update(self, p): return True
            def analyze(self, d): return type('R', (), {'signals': []})()

        plugin = TestPlugin()
        instance = pool.create_instance("t1", plugin)
        assert instance is not None

        result = pool.destroy_instance(instance.instance_id)
        assert result is True

    def test_tenant_limits(self):
        pool = StrategyPool()
        pool.register_tenant(TenantContext(tenant_id="t1", name="T1", max_strategies=1))

        class TestPlugin(StrategyPlugin):
            @property
            def metadata(self):
                return PluginMetadata(id="test", name="Test", version="1.0")
            def on_load(self): return True
            def on_unload(self): return True
            def on_init(self, c): return True
            def on_start(self): return True
            def on_stop(self): return True
            def on_update(self, p): return True
            def analyze(self, d): return type('R', (), {'signals': []})()

        plugin1 = TestPlugin()
        plugin2 = TestPlugin()

        instance1 = pool.create_instance("t1", plugin1)
        assert instance1 is not None

        # 超出限制
        instance2 = pool.create_instance("t1", plugin2)
        assert instance2 is None

    def test_stats(self):
        pool = StrategyPool()
        pool.register_tenant(TenantContext(tenant_id="t1", name="T1"))

        class TestPlugin(StrategyPlugin):
            @property
            def metadata(self):
                return PluginMetadata(id="test", name="Test", version="1.0")
            def on_load(self): return True
            def on_unload(self): return True
            def on_init(self, c): return True
            def on_start(self): return True
            def on_stop(self): return True
            def on_update(self, p): return True
            def analyze(self, d): return type('R', (), {'signals': []})()

        plugin = TestPlugin()
        pool.create_instance("t1", plugin)

        stats = pool.get_stats()
        assert stats["total_instances"] == 1
        assert stats["total_tenants"] == 1


class TestResourceManager:
    """资源管理器测试"""

    def test_set_and_get_limit(self):
        rm = ResourceManager()
        limit = ResourceLimit(max_memory_mb=128.0)
        rm.set_limit("instance1", limit)

        retrieved = rm.get_limit("instance1")
        assert retrieved.max_memory_mb == 128.0

    def test_check_limits(self):
        rm = ResourceManager()
        from app.domain.strategies.pool.resource_manager import ResourceUsage

        limit = ResourceLimit(max_memory_mb=100.0)
        rm.set_limit("instance1", limit)

        # 正常情况
        usage = ResourceUsage(memory_mb=50.0)
        rm.record_usage("instance1", usage)
        valid, msg = rm.check_limits("instance1")
        assert valid is True

        # 超出限制
        usage = ResourceUsage(memory_mb=150.0)
        rm.record_usage("instance1", usage)
        valid, msg = rm.check_limits("instance1")
        assert valid is False
        assert "Memory limit exceeded" in msg

    def test_total_usage(self):
        rm = ResourceManager()
        from app.domain.strategies.pool.resource_manager import ResourceUsage

        rm.record_usage("i1", ResourceUsage(memory_mb=50.0, execution_count=10))
        rm.record_usage("i2", ResourceUsage(memory_mb=30.0, execution_count=5))

        total = rm.get_total_usage()
        assert total.memory_mb == 80.0
        assert total.execution_count == 15


if __name__ == "__main__":
    pytest.main([__file__, "-v"])