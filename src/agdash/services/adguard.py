"""AdGuard Home API client."""

from __future__ import annotations

from typing import Optional

import requests

from agdash.services.config import AdGuardInstance


class AdGuard:
    """Single AdGuard Home instance."""

    def __init__(self, instance: AdGuardInstance) -> None:
        self.name = instance.name
        self.url = instance.url.rstrip("/")
        self.auth = (instance.username, instance.password)
        self._session = requests.Session()
        self._session.auth = self.auth

    def get_status(self) -> dict:
        """Get filtering status and stats."""
        try:
            # Get protection status
            status_resp = self._session.get(f"{self.url}/control/status", timeout=5)
            status = status_resp.json() if status_resp.ok else {}

            # Get stats
            stats_resp = self._session.get(f"{self.url}/control/stats", timeout=5)
            stats = stats_resp.json() if stats_resp.ok else {}

            enabled = status.get("protection_enabled", False)
            queries = stats.get("num_dns_queries", 0)
            blocked = stats.get("num_blocked_filtering", 0)
            blocked_pct = (blocked / queries * 100) if queries > 0 else 0

            return {
                "name": self.name,
                "enabled": enabled,
                "queries": queries,
                "blocked": blocked,
                "blocked_pct": blocked_pct,
            }
        except Exception as e:
            print(f"AdGuard {self.name} error: {e}")
            return {
                "name": self.name,
                "enabled": False,
                "queries": 0,
                "blocked": 0,
                "blocked_pct": 0,
                "error": str(e),
            }

    def toggle(self) -> bool:
        """Toggle protection on/off. Returns new state."""
        status = self.get_status()
        new_state = not status.get("enabled", False)
        return self.set_protection(new_state)

    def clear_cache(self) -> bool:
        """Clear DNS cache. Returns True on success."""
        try:
            resp = self._session.post(f"{self.url}/control/cache_clear", timeout=5)
            return resp.ok
        except Exception as e:
            print(f"Clear cache {self.name} failed: {e}")
            return False

    def set_protection(self, enabled: bool, duration_ms: int | None = None) -> bool:
        """Set protection state. Duration in ms for timed disable. Returns actual state."""
        try:
            payload: dict = {"enabled": enabled}
            if not enabled and duration_ms is not None:
                payload["duration"] = duration_ms
            resp = self._session.post(
                f"{self.url}/control/protection",
                json=payload,
                timeout=5,
            )
            return enabled if resp.ok else not enabled
        except Exception as e:
            print(f"Set protection {self.name} failed: {e}")
            return not enabled


class AdGuardManager:
    """Manages multiple AdGuard instances."""

    def __init__(self, instances: list[AdGuardInstance]) -> None:
        self.clients = [AdGuard(inst) for inst in instances]

    def get_all_status(self) -> list[dict]:
        return [c.get_status() for c in self.clients]

    def toggle(self, name: str, duration_ms: int | None = None) -> None:
        """Toggle protection for a specific instance. Duration for timed disable."""
        for c in self.clients:
            if c.name == name:
                status = c.get_status()
                new_state = not status.get("enabled", False)
                c.set_protection(new_state, duration_ms if not new_state else None)
                return

    def disable(self, name: str, duration_ms: int | None = None) -> None:
        """Disable protection for a specific instance with optional duration."""
        for c in self.clients:
            if c.name == name:
                c.set_protection(False, duration_ms)
                return

    def enable(self, name: str) -> None:
        """Enable protection for a specific instance."""
        for c in self.clients:
            if c.name == name:
                c.set_protection(True)
                return

    def toggle_all(self, duration_ms: int | None = None) -> None:
        """Toggle all instances. If any are off, turn all on. If all on, turn all off."""
        statuses = self.get_all_status()
        all_on = all(s.get("enabled", False) for s in statuses)

        # If all on, turn all off. Otherwise turn all on.
        new_state = not all_on

        for c in self.clients:
            c.set_protection(new_state, duration_ms if not new_state else None)

    def disable_all(self, duration_ms: int | None = None) -> None:
        """Disable protection for all instances with optional duration."""
        for c in self.clients:
            c.set_protection(False, duration_ms)

    def enable_all(self) -> None:
        """Enable protection for all instances."""
        for c in self.clients:
            c.set_protection(True)

    def clear_cache(self, name: str) -> None:
        """Clear DNS cache for a specific instance."""
        for c in self.clients:
            if c.name == name:
                c.clear_cache()
                return

    def clear_cache_all(self) -> None:
        """Clear DNS cache for all instances."""
        for c in self.clients:
            c.clear_cache()
