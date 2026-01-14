"""
Button handler for NanoHat OLED 3-button interface.

K1 = Left, K2 = Middle/Select, K3 = Right
"""

from __future__ import annotations

import platform
import time
from enum import Enum
from typing import Callable, Optional


class Button(Enum):
    K1 = 0  # Left
    K2 = 1  # Middle
    K3 = 2  # Right


# GPIO pins for NanoHat OLED buttons
GPIO_PINS = {
    Button.K1: 0,   # PA0
    Button.K2: 2,   # PA2
    Button.K3: 3,   # PA3
}


class Buttons:
    """Button input handler - simple press detection only."""

    DEBOUNCE_MS = 30  # Debounce time in milliseconds
    STARTUP_IGNORE_MS = 1000  # Ignore button presses for this long after init

    def __init__(self) -> None:
        self._callbacks: dict[Button, list[Callable]] = {b: [] for b in Button}
        self._states: dict[Button, bool] = {b: False for b in Button}
        self._last_change: dict[Button, float] = {b: 0.0 for b in Button}
        self._simulated = not self._is_nanopi()
        self._gpio = None
        self._init_time = time.time()

        if not self._simulated:
            self._init_gpio()

    def _is_nanopi(self) -> bool:
        return platform.system() == "Linux" and platform.machine() == "aarch64"

    def _init_gpio(self) -> None:
        try:
            import OPi.GPIO as GPIO
            GPIO.setmode(GPIO.SUNXI)
            for pin in GPIO_PINS.values():
                GPIO.setup(f"PA{pin}", GPIO.IN, pull_up_down=GPIO.PUD_UP)
            self._gpio = GPIO

            # Read initial button states so we don't trigger on startup
            for button, pin in GPIO_PINS.items():
                self._states[button] = GPIO.input(f"PA{pin}") == 0

            print("Buttons initialized on GPIO")
        except Exception as e:
            print(f"GPIO init failed: {e}")
            self._simulated = True

    def on_press(self, button: Button, callback: Callable) -> None:
        self._callbacks[button].append(callback)

    def poll(self) -> None:
        """Poll buttons. Call in main loop."""
        if self._simulated:
            self._poll_keyboard()
        else:
            self._poll_gpio()

    def _poll_gpio(self) -> None:
        if not self._gpio:
            return

        now = time.time()

        # Ignore all input during startup to avoid false triggers
        if now - self._init_time < self.STARTUP_IGNORE_MS / 1000.0:
            return

        debounce_sec = self.DEBOUNCE_MS / 1000.0

        for button, pin in GPIO_PINS.items():
            pressed = self._gpio.input(f"PA{pin}") == 0  # Active low

            # Debounce: ignore changes within debounce window
            if now - self._last_change[button] < debounce_sec:
                continue

            if pressed and not self._states[button]:
                # Just pressed - fire callback
                self._states[button] = True
                self._last_change[button] = now
                for callback in self._callbacks[button]:
                    callback()

            elif not pressed and self._states[button]:
                # Just released
                self._states[button] = False
                self._last_change[button] = now

    def _poll_keyboard(self) -> None:
        """Simulated keyboard input for development."""
        import sys
        import select

        if select.select([sys.stdin], [], [], 0)[0]:
            key = sys.stdin.read(1)
            if key == "1":
                for cb in self._callbacks[Button.K1]:
                    cb()
            elif key == "2":
                for cb in self._callbacks[Button.K2]:
                    cb()
            elif key == "3":
                for cb in self._callbacks[Button.K3]:
                    cb()
            elif key == "q":
                raise KeyboardInterrupt

    def cleanup(self) -> None:
        if self._gpio:
            self._gpio.cleanup()
