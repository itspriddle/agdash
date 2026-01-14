#!/usr/bin/env python3
"""Generate screenshots with mock data."""

from agdash.hardware.display import Display
from agdash.ui.screens import AdGuardScreen

# Mock data: 67k + 9k = 76k
MOCK_DATA = [
    {"name": "DNS1", "enabled": True, "queries": 67000, "blocked": 8040, "blocked_pct": 12},
    {"name": "DNS2", "enabled": True, "queries": 9000, "blocked": 990, "blocked_pct": 11},
]


def main():
    display = Display()
    screen = AdGuardScreen()
    screen.update(MOCK_DATA)

    # Home screen
    screen.render(display)
    display.screenshot("docs/screenshot-home.png")
    print("Saved docs/screenshot-home.png")

    # Detail screen (DNS1 selected, FLUSH highlighted)
    screen.selected = 0
    screen.in_detail = True
    screen.detail_selected = 1  # FLUSH selected
    screen.render(display)
    display.screenshot("docs/screenshot-detail.png")
    print("Saved docs/screenshot-detail.png")

    # Confirm screen
    screen.in_detail = False
    screen.in_confirm = True
    screen.confirm_target = "DNS1"
    screen.confirm_selected = 0
    screen.render(display)
    display.screenshot("docs/screenshot-confirm.png")
    print("Saved docs/screenshot-confirm.png")


if __name__ == "__main__":
    main()
