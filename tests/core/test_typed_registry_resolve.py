"""Registry must instantiate @register_service classes, not return bare types."""

from __future__ import annotations

from app.core.typed_registry import TypedServiceRegistry


def test_resolve_instantiates_registered_class() -> None:
    reg = TypedServiceRegistry()

    class _DemoService:
        def __init__(self) -> None:
            self.ready = True

        def ping(self) -> str:
            return "pong"

    reg.register("demo_service", _DemoService)
    svc = reg.resolve("demo_service")
    assert isinstance(svc, _DemoService)
    assert svc.ping() == "pong"
    assert reg.resolve("demo_service") is svc


def test_register_skips_class_when_factory_exists() -> None:
    reg = TypedServiceRegistry()

    class _FromFactory:
        def __init__(self) -> None:
            self.source = "factory"

    class _FromDecorator:
        def __init__(self) -> None:
            self.source = "class"

    reg.register_factory("demo_service", lambda _reg: _FromFactory())
    reg.register("demo_service", _FromDecorator)

    svc = reg.resolve("demo_service")
    assert isinstance(svc, _FromFactory)
    assert svc.source == "factory"
