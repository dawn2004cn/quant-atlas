"""Venue Registry — manages available execution venues with health monitoring."""

from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime
from typing import Any

from .execution_venue import ExecutionVenue, VenueStatus

logger = logging.getLogger(__name__)


class VenueRegistry:
    """Registry for execution venues with automatic health monitoring.

    Features:
    - Dynamic venue registration/deregistration
    - Periodic health checks
    - Automatic failover ordering by priority and health
    - Circuit breaker pattern for unhealthy venues
    """

    def __init__(
        self,
        *,
        health_check_interval: int = 30,
        recovery_check_interval: int = 60,
    ):
        self._venues: dict[str, ExecutionVenue] = {}
        self._lock = threading.Lock()
        self._health_check_interval = health_check_interval
        self._recovery_check_interval = recovery_check_interval
        self._monitor_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._health_history: dict[str, list[dict[str, Any]]] = {}

    def register(self, venue: ExecutionVenue) -> None:
        """Register an execution venue.

        Args:
            venue: The venue to register
        """
        with self._lock:
            self._venues[venue.venue_id] = venue
            self._health_history.setdefault(venue.venue_id, [])
        logger.info("registered execution venue: %s (priority=%d)",
                   venue.venue_id, venue.priority)

    def unregister(self, venue_id: str) -> None:
        """Unregister an execution venue.

        Args:
            venue_id: The venue to remove
        """
        with self._lock:
            removed = self._venues.pop(venue_id, None)
            if removed:
                logger.info("unregistered execution venue: %s", venue_id)

    def get_venue(self, venue_id: str) -> ExecutionVenue | None:
        """Get a specific venue by ID.

        Args:
            venue_id: The venue to retrieve

        Returns:
            The venue or None if not found
        """
        with self._lock:
            return self._venues.get(venue_id)

    def get_healthy_venues(
        self,
        *,
        preferred: list[str] | None = None,
    ) -> list[ExecutionVenue]:
        """Get venues sorted by priority, filtering unhealthy ones.

        Args:
            preferred: Optional list of preferred venue IDs to try first

        Returns:
            List of venues sorted by priority (healthy first)
        """
        with self._lock:
            all_venues = list(self._venues.values())

        # Separate by health status
        healthy = [v for v in all_venues if v.status == VenueStatus.HEALTHY]
        degraded = [v for v in all_venues if v.status == VenueStatus.DEGRADED]

        # Sort each group by priority (lower = higher priority)
        healthy.sort(key=lambda v: v.priority)
        degraded.sort(key=lambda v: v.priority)

        # If preferred venues specified, move them to front
        if preferred:
            preferred_set = set(preferred)
            preferred_healthy = [v for v in healthy if v.venue_id in preferred_set]
            other_healthy = [v for v in healthy if v.venue_id not in preferred_set]
            healthy = preferred_healthy + other_healthy

        # Return healthy first, then degraded as fallback
        return healthy + degraded

    def get_all_venues(self) -> list[ExecutionVenue]:
        """Get all registered venues regardless of health."""
        with self._lock:
            return list(self._venues.values())

    async def check_all_health(self) -> dict[str, VenueStatus]:
        """Run health checks on all venues.

        Returns:
            Dict mapping venue_id to current status
        """
        results = {}
        with self._lock:
            venues = list(self._venues.values())

        for venue in venues:
            try:
                status = await asyncio.wait_for(
                    venue.health_check(),
                    timeout=10.0,
                )
                results[venue.venue_id] = status

                # Record health check in history
                with self._lock:
                    history = self._health_history.setdefault(venue.venue_id, [])
                    history.append({
                        "timestamp": datetime.now().isoformat(),
                        "status": status.value,
                    })
                    # Keep only last 100 checks
                    if len(history) > 100:
                        self._health_history[venue.venue_id] = history[-100:]

            except asyncio.TimeoutError:
                results[venue.venue_id] = VenueStatus.UNHEALTHY
                logger.warning("health check timeout for venue %s", venue.venue_id)
            except Exception as exc:
                results[venue.venue_id] = VenueStatus.UNHEALTHY
                logger.warning("health check failed for venue %s: %s",
                             venue.venue_id, exc)

        return results

    def start_monitoring(self) -> None:
        """Start background health monitoring thread."""
        if self._monitor_thread is not None and self._monitor_thread.is_alive():
            return

        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="venue-health-monitor",
            daemon=True,
        )
        self._monitor_thread.start()
        logger.info("venue health monitoring started (interval=%ds)",
                   self._health_check_interval)

    def stop_monitoring(self) -> None:
        """Stop background health monitoring."""
        self._stop_event.set()
        if self._monitor_thread is not None:
            self._monitor_thread.join(timeout=5.0)
            self._monitor_thread = None
        logger.info("venue health monitoring stopped")

    def _monitor_loop(self) -> None:
        """Background health check loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while not self._stop_event.is_set():
            try:
                results = loop.run_until_complete(self.check_all_health())

                # Log summary
                healthy_count = sum(1 for s in results.values()
                                   if s == VenueStatus.HEALTHY)
                total_count = len(results)
                logger.debug("venue health: %d/%d healthy",
                           healthy_count, total_count)

            except Exception as exc:
                logger.warning("venue health monitor error: %s", exc)

            # Wait for next check
            self._stop_event.wait(self._health_check_interval)

        loop.close()

    def get_manifest(self) -> dict[str, Any]:
        """Get registry status manifest.

        Returns:
            Dict with venue status and statistics
        """
        with self._lock:
            venues = list(self._venues.values())

        venue_stats = [v.stats for v in venues]
        healthy_count = sum(1 for v in venues if v.status == VenueStatus.HEALTHY)

        return {
            "total_venues": len(venues),
            "healthy_venues": healthy_count,
            "degraded_venues": sum(1 for v in venues if v.status == VenueStatus.DEGRADED),
            "unhealthy_venues": sum(1 for v in venues if v.status == VenueStatus.UNHEALTHY),
            "monitoring_active": (self._monitor_thread is not None and
                                 self._monitor_thread.is_alive()),
            "venues": venue_stats,
        }

    def reset_all_venues(self) -> None:
        """Manually reset all venues to HEALTHY status."""
        with self._lock:
            venues = list(self._venues.values())
        for venue in venues:
            venue.reset_status()
        logger.info("all venues manually reset to HEALTHY")


__all__ = ["VenueRegistry"]
