"""
OLED Display - SSD1306 128x64.

Simple display wrapper. Full 128x64 is yours - no forced layout.
"""

from __future__ import annotations

import platform
from pathlib import Path
from typing import Callable, Optional

from PIL import Image, ImageDraw, ImageFont

# Display size
WIDTH = 128
HEIGHT = 64

# Fonts
FONTS_DIR = Path(__file__).parent.parent.parent.parent / "assets" / "fonts"


class Display:
    """SSD1306 128x64 OLED display."""

    def __init__(self) -> None:
        self.width = WIDTH
        self.height = HEIGHT
        self._device = None
        self._simulated = not self._is_nanopi()
        self._last_image: Optional[Image.Image] = None

        if not self._simulated:
            self._init_hardware()

        self._load_fonts()

    def _is_nanopi(self) -> bool:
        return platform.system() == "Linux" and platform.machine() == "aarch64"

    def _init_hardware(self) -> None:
        try:
            from luma.core.interface.serial import i2c
            from luma.oled.device import ssd1306

            serial = i2c(port=0, address=0x3C)
            self._device = ssd1306(serial, width=self.width, height=self.height)
        except Exception as e:
            print(f"Hardware init failed: {e}")
            self._simulated = True

    def _load_fonts(self) -> None:
        try:
            # Terminus - classic terminal bitmap font
            self.font = ImageFont.truetype(str(FONTS_DIR / "TerminusTTF-4.49.3.ttf"), 12)
            self.font_bold = ImageFont.truetype(str(FONTS_DIR / "TerminusTTF-Bold-4.49.3.ttf"), 12)
            self.icons = ImageFont.truetype(str(FONTS_DIR / "materialdesignicons.ttf"), 12)
            self.icons_lg = ImageFont.truetype(str(FONTS_DIR / "materialdesignicons.ttf"), 20)
        except Exception as e:
            print(f"Font load error: {e}")
            self.font = ImageFont.load_default()
            self.font_bold = self.font
            self.icons = self.font
            self.icons_lg = self.font

    def render(self, draw_func: Callable[[ImageDraw.ImageDraw], None]) -> None:
        """Render frame. draw_func receives ImageDraw, draws to 128x64."""
        if self._device and not self._simulated:
            from luma.core.render import canvas
            with canvas(self._device) as draw:
                draw_func(draw)
        else:
            img = Image.new("1", (self.width, self.height), "black")
            draw = ImageDraw.Draw(img)
            draw_func(draw)
            self._last_image = img
            self._print_ascii(img)

    def _print_ascii(self, img: Image.Image) -> None:
        print("\033[2J\033[H", end="")
        for y in range(self.height):
            line = ""
            for x in range(self.width):
                line += "█" if img.getpixel((x, y)) else " "
            print(line)

    def screenshot(self, path: str = "screenshot.png") -> None:
        if self._last_image:
            scaled = self._last_image.resize((self.width * 4, self.height * 4), Image.Resampling.NEAREST)
            scaled.save(path)

    def clear(self) -> None:
        if self._device:
            self._device.clear()

    def set_brightness(self, level: int) -> None:
        """Set display brightness (0-255). Maps to contrast control."""
        if self._device:
            self._device.contrast(max(0, min(255, level)))


# Material Design Icons
ICON = {
    "shield": "\U000F0498",
    "shield_check": "\U000F0565",
    "shield_off": "\U000F099E",
    "chevron_left": "\U000F0141",
    "chevron_right": "\U000F0142",
    "sync": "\U000F04E6",
    "loading": "\U000F0772",
    "dots": "\U000F01D8",
}
