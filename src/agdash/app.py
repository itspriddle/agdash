"""Main application."""

from __future__ import annotations

import signal
import time

from agdash.hardware.buttons import Button, Buttons
from agdash.hardware.display import Display, WIDTH, HEIGHT, ICON
from agdash.services.adguard import AdGuardManager
from agdash.services.config import Config
from agdash.ui.screens import AdGuardScreen


class App:
    """AGDash application."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.running = False

        # Hardware
        self.display = Display()
        self.buttons = Buttons()

        # Services
        self.adguard = AdGuardManager(config.adguard) if config.adguard else None

        # Screen
        self.screen = AdGuardScreen(
            on_disable=self._disable_instance,
            on_disable_all=self._disable_all,
            on_enable=self._enable_instance,
            on_enable_all=self._enable_all,
            on_flush=self._flush_instance,
            on_flush_all=self._flush_all,
        )

        # Timing
        self._last_refresh = 0.0

    def run(self) -> None:
        """Main loop."""
        self.running = True
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

        # Setup buttons: K1=up, K2=select, K3=down
        self.buttons.on_press(Button.K1, self.screen.on_k1)
        self.buttons.on_press(Button.K2, self.screen.on_k2)
        self.buttons.on_press(Button.K3, self.screen.on_k3)

        # Splash screen
        self._show_splash()

        # Initial data
        self._refresh_data()

        print("AGDash started. K1/K3=nav, K2=select")

        try:
            while self.running:
                self.buttons.poll()

                # Refresh data every 30s
                now = time.time()
                if now - self._last_refresh > 30:
                    self._refresh_data()

                # Render
                self.screen.render(self.display)

                time.sleep(0.02)  # 20ms for responsive buttons
        except KeyboardInterrupt:
            pass
        finally:
            self._cleanup()

    def _show_splash(self, duration: float = 2.0) -> None:
        """Show splash screen for a few seconds."""
        def draw(d):
            # Row 1: Shield icon (centered)
            icon = ICON["shield_check"]
            icon_bbox = d.textbbox((0, 0), icon, font=self.display.icons_lg)
            icon_w = icon_bbox[2] - icon_bbox[0]
            d.text(((WIDTH - icon_w) // 2, 12), icon, font=self.display.icons_lg, fill="white")

            # Row 2-3: "AdGuard" text (centered)
            text = "AdGuard"
            text_bbox = d.textbbox((0, 0), text, font=self.display.font_bold)
            text_w = text_bbox[2] - text_bbox[0]
            d.text(((WIDTH - text_w) // 2, 40), text, font=self.display.font_bold, fill="white")

        self.display.render(draw)
        time.sleep(duration)

    def _refresh_data(self) -> None:
        if self.adguard:
            data = self.adguard.get_all_status()
            self.screen.update(data)
        self._last_refresh = time.time()

    def _disable_instance(self, name: str, duration_ms: int | None) -> None:
        if self.adguard:
            self.adguard.disable(name, duration_ms)
            self._refresh_data()

    def _disable_all(self, duration_ms: int | None) -> None:
        if self.adguard:
            self.adguard.disable_all(duration_ms)
            self._refresh_data()

    def _enable_instance(self, name: str) -> None:
        if self.adguard:
            self.adguard.enable(name)
            self._refresh_data()

    def _enable_all(self) -> None:
        if self.adguard:
            self.adguard.enable_all()
            self._refresh_data()

    def _flush_instance(self, name: str) -> None:
        if self.adguard:
            self.adguard.clear_cache(name)

    def _flush_all(self) -> None:
        if self.adguard:
            self.adguard.clear_cache_all()

    def _shutdown(self, *args) -> None:
        print("\nShutting down...")
        self.running = False

    def _cleanup(self) -> None:
        self.buttons.cleanup()
        self.display.clear()
        print("AGDash stopped.")
