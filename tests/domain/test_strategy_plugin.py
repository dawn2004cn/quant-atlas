"""Strategy Plugin System Tests."""

import pytest

from app.domain.strategies.plugin import (
    StrategyPlugin,
    PluginMetadata,
    PluginState,
    PluginConfig,
    StrategyRegistry,
    StrategyEngine,
    StrategyLoader,
)
from app.domain.strategies.plugin.adapters import (
    MacdPlugin,
    RsiPlugin,
    StrategyAdapter,
)


class TestPluginMetadata:
    """插件元数据测试"""

    def test_create_metadata(self):
        meta = PluginMetadata(
            id="test_plugin",
            name="Test Plugin",
            version="1.0.0",
        )
        assert meta.id == "test_plugin"
        assert meta.name == "Test Plugin"
        assert meta.version == "1.0.0"


class TestPluginState:
    """插件状态测试"""

    def test_state_values(self):
        assert PluginState.DISCOVERED.value == "discovered"
        assert PluginState.LOADED.value == "loaded"
        assert PluginState.RUNNING.value == "running"


class TestStrategyRegistry:
    """策略注册中心测试"""

    def test_register_plugin(self):
        registry = StrategyRegistry()

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
        result = registry.register(plugin)

        assert result is True
        assert "test" in [e.id for e in registry.list_all()]

    def test_unregister_plugin(self):
        registry = StrategyRegistry()

        class TestPlugin(StrategyPlugin):
            @property
            def metadata(self):
                return PluginMetadata(id="test2", name="Test2", version="1.0")

            def on_load(self): return True
            def on_unload(self): return True
            def on_init(self, c): return True
            def on_start(self): return True
            def on_stop(self): return True
            def on_update(self, p): return True
            def analyze(self, d): return type('R', (), {'signals': []})()

        plugin = TestPlugin()
        registry.register(plugin)
        result = registry.unregister("test2")

        assert result is True

    def test_get_by_name(self):
        registry = StrategyRegistry()

        plugin = MacdPlugin({"fast_period": 12})
        registry.register(plugin)

        found = registry.get_by_name("MACD Crossover")
        assert found is not None


class TestStrategyEngine:
    """策略引擎测试"""

    def test_initialize_plugin(self):
        registry = StrategyRegistry()
        engine = StrategyEngine(registry)

        plugin = MacdPlugin()
        registry.register(plugin)

        config = PluginConfig(enabled=True, params={})
        result = engine.initialize_plugin("macd_crossover", config)

        assert result is True

    def test_start_stop_plugin(self):
        registry = StrategyRegistry()
        engine = StrategyEngine(registry)

        plugin = RsiPlugin()
        registry.register(plugin)

        # 启动
        result = engine.start_plugin("rsi_reversal")
        assert result is True
        assert "rsi_reversal" in engine.get_running_plugins()

        # 停止
        result = engine.stop_plugin("rsi_reversal")
        assert result is True

    def test_execute(self):
        registry = StrategyRegistry()
        engine = StrategyEngine(registry)

        plugin = MacdPlugin()
        registry.register(plugin)
        engine.start_plugin("macd_crossover")

        # 执行分析
        data = {
            "close": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111,
                      112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125],
            "high": [105] * 26,
            "low": [95] * 26,
            "volume": [1000] * 26,
        }

        signals = engine.execute(data)
        assert isinstance(signals, list)

        engine.stop_all()


class TestPluginAdapter:
    """插件适配器测试"""

    def test_macd_plugin(self):
        plugin = MacdPlugin({"fast_period": 12, "slow_period": 26})

        assert plugin.metadata.id == "macd_crossover"
        assert plugin.metadata.name == "MACD Crossover"
        assert "trend" in plugin.metadata.tags

    def test_rsi_plugin(self):
        plugin = RsiPlugin({"rsi_period": 14, "oversold": 30, "overbought": 70})

        assert plugin.metadata.id == "rsi_reversal"
        assert "oscillator" in plugin.metadata.tags

    def test_plugin_lifecycle(self):
        plugin = MacdPlugin()

        # 加载
        assert plugin.on_load() is True
        assert plugin.get_state() == PluginState.LOADED

        # 初始化
        config = PluginConfig(enabled=True, params={})
        assert plugin.on_init(config) is True
        assert plugin.get_state() == PluginState.INITIALIZED

        # 启动
        assert plugin.on_start() is True
        assert plugin.get_state() == PluginState.RUNNING

        # 分析
        result = plugin.analyze({"close": [100, 101, 102]})
        assert result is not None

        # 停止
        assert plugin.on_stop() is True
        assert plugin.get_state() == PluginState.STOPPED


class TestStrategyLoader:
    """策略加载器测试"""

    def test_create_loader(self):
        loader = StrategyLoader()
        assert loader is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])