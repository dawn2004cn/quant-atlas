"""Tests for app.application.request_executor."""

from __future__ import annotations

import asyncio

import pytest

from app.application.request_executor import run_async


async def _answer() -> str:
    return "ok"


def test_run_async_executes_coroutine():
    assert run_async(_answer()) == "ok"


def test_run_async_accepts_factory():
    assert run_async(_answer) == "ok"


def test_async_task_decorator_delegates_to_run_async():
    from app.modules.system.services.base import async_task

    @async_task
    async def add(a: int, b: int) -> int:
        return a + b

    assert add(2, 3) == 5


@pytest.mark.asyncio
async def test_run_async_from_running_loop_uses_thread_pool():
    """When a loop is already running, run_async must still return."""

    def _call():
        return run_async(_answer())

    result = await asyncio.to_thread(_call)
    assert result == "ok"
