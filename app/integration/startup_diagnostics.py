from __future__ import annotations
"""Startup Diagnostics Service.

Logs and tracks application startup sequence.
"""


import time
from dataclasses import dataclass


from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StartupStep:
    """A single startup step."""
    name: str
    status: str  # "started", "completed", "failed"
    start_time: float
    end_time: float | None = None
    duration_ms: float | None = None
    error: str | None = None

    def complete(self, error: str = None) -> None:
        self.status = "completed" if not error else "failed"
        self.end_time = time.perf_counter()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        if error:
            self.error = error


class StartupDiagnostics:
    """Tracks application startup sequence."""

    def __init__(self):
        self._steps: list[StartupStep] = []
        self._current_step: str | None = None
        self._start_time = time.perf_counter()
        logger.info("StartupDiagnostics initialized")

    def start_step(self, name: str) -> None:
        """Start a startup step."""
        step = StartupStep(
            name=name,
            status="started",
            start_time=time.perf_counter()
        )
        self._steps.append(step)
        self._current_step = name
        logger.info(f"Startup step started: {name}")

    def complete_step(self, name: str, error: str = None) -> None:
        """Complete a startup step."""
        for step in reversed(self._steps):
            if step.name == name and step.status == "started":
                step.complete(error)
                self._current_step = None
                if error:
                    logger.error(f"Startup step failed: {name} - {error}")
                else:
                    logger.info(f"Startup step completed: {name} ({step.duration_ms:.1f}ms)")
                break

    def get_summary(self) -> dict:
        """Get startup summary."""
        total_duration = (time.perf_counter() - self._start_time) * 1000

        completed = sum(1 for s in self._steps if s.status == "completed")
        failed = sum(1 for s in self._steps if s.status == "failed")

        return {
            "total_duration_ms": total_duration,
            "total_steps": len(self._steps),
            "completed": completed,
            "failed": failed,
            "steps": [
                {
                    "name": s.name,
                    "status": s.status,
                    "duration_ms": s.duration_ms,
                    "error": s.error
                }
                for s in self._steps
            ]
        }

    def log_summary(self) -> None:
        """Log startup summary."""
        summary = self.get_summary()
        logger.info("="*50)
        logger.info("STARTUP DIAGNOSTICS SUMMARY")
        logger.info("="*50)
        logger.info(f"Total duration: {summary['total_duration_ms']:.1f}ms")
        logger.info(f"Steps: {summary['completed']}/{summary['total_steps']} completed")
        if summary['failed'] > 0:
            logger.warning(f"Failed steps: {summary['failed']}")
        for step in summary['steps']:
            status_icon = "✓" if step['status'] == "completed" else "✗"
            duration = f"{step['duration_ms']:.1f}ms" if step['duration_ms'] else "N/A"
            logger.info(f"  {status_icon} {step['name']}: {step['status']} ({duration})")
        logger.info("="*50)

    @property
    def is_complete(self) -> bool:
        """Check if all steps are complete."""
        return all(s.status != "started" for s in self._steps)

    @property
    def has_failures(self) -> bool:
        """Check if any step failed."""
        return any(s.status == "failed" for s in self._steps)


# Global instance
_startup_diagnostics: StartupDiagnostics | None = None


def get_startup_diagnostics() -> StartupDiagnostics:
    """Get global startup diagnostics."""
    global _startup_diagnostics
    if _startup_diagnostics is None:
        _startup_diagnostics = StartupDiagnostics()
    return _startup_diagnostics


def log_startup(component: str) -> None:
    """Log a startup component."""
    diagnostics = get_startup_diagnostics()
    diagnostics.start_step(component)


def log_startup_complete(component: str, error: str = None) -> None:
    """Log startup component completion."""
    diagnostics = get_startup_diagnostics()
    diagnostics.complete_step(component, error)


__all__ = [
    "StartupStep",
    "StartupDiagnostics",
    "get_startup_diagnostics",
    "log_startup",
    "log_startup_complete",
]
