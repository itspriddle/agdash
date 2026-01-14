"""AdGuard screen - scrollable home with detail drill-down."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Callable, Optional

from agdash.hardware.display import WIDTH, HEIGHT, ICON

if TYPE_CHECKING:
    from agdash.hardware.display import Display


def fmt_num(n: int) -> str:
    """Format number with k/M suffix (truncated/floor for intuitive display)."""
    if n >= 1_000_000:
        return f"{n // 100_000 / 10:.1f}M"
    elif n >= 1_000:
        return f"{n // 1_000}k"
    return str(n)


class AdGuardScreen:
    """AdGuard screen - 4 row grid layout (16px each, 64px total)."""

    ROW_H = 16  # 4 rows × 16px = 64px
    ROWS = 4

    # Detail menu items
    DETAIL_MENU = ["TOGGLE", "FLUSH", "< BACK"]

    # ALL menu items (no stats, just actions)
    ALL_MENU = ["TOGGLE", "FLUSH", "< BACK"]

    # Duration options for disable (label, milliseconds or None for cancel)
    DURATION_OPTIONS = [
        ("FOREVER", None),  # None = indefinite
        ("5 MINS", 5 * 60 * 1000),
        ("1 HOUR", 60 * 60 * 1000),
        ("CANCEL", -1),  # -1 = cancel
    ]

    def __init__(
        self,
        on_disable: Optional[Callable[[str, Optional[int]], None]] = None,
        on_disable_all: Optional[Callable[[Optional[int]], None]] = None,
        on_enable: Optional[Callable[[str], None]] = None,
        on_enable_all: Optional[Callable[[], None]] = None,
        on_flush: Optional[Callable[[str], None]] = None,
        on_flush_all: Optional[Callable[[], None]] = None,
    ) -> None:
        self.on_disable = on_disable
        self.on_disable_all = on_disable_all
        self.on_enable = on_enable
        self.on_enable_all = on_enable_all
        self.on_flush = on_flush
        self.on_flush_all = on_flush_all
        self.instances: list[dict] = []
        self.selected = 0  # 0=DNS1, 1=DNS2, 2=ALL
        self.in_detail = False
        self.detail_selected = 0  # 0=TOGGLE, 1=FLUSH, 2=BACK
        self.in_all_menu = False  # ALL menu view
        self.all_menu_selected = 0  # 0=TOGGLE, 1=FLUSH, 2=BACK
        self.in_confirm = False
        self.confirm_selected = 0  # 0=YES, 1=NO
        self.confirm_target: Optional[str] = None  # Name to act on, or None for ALL
        self.confirm_action: str = "enable"  # "enable" or "flush"
        self.in_duration = False  # Duration selection for disable
        self.duration_selected = 0
        self.loading = False
        self._display: Optional[Display] = None

    def update(self, instances: list[dict]) -> None:
        self.instances = instances

    def render(self, display: Display) -> None:
        self._display = display
        if self.loading:
            self._render_loading(display)
        elif self.in_duration:
            self._render_duration(display)
        elif self.in_confirm:
            self._render_confirm(display)
        elif self.in_all_menu:
            self._render_all_menu(display)
        elif self.in_detail:
            self._render_detail(display)
        else:
            self._render_home(display)

    def _row_y(self, row: int) -> int:
        """Get Y position for a row (0-3)."""
        return row * self.ROW_H

    def _render_home(self, display: Display) -> None:
        """Home screen: 4-row grid with DNS1, DNS2, ALL, blank."""
        # Build list: instances + ALL
        items = []
        for inst in self.instances:
            items.append({
                "name": inst.get("name", "?"),
                "status": "ON" if inst.get("enabled", False) else "OFF",
                "queries": fmt_num(inst.get("queries", 0)),
                "pct": f"{inst.get('blocked_pct', 0):.0f}%",
            })

        # ALL row with totals
        all_on = all(i.get("enabled", False) for i in self.instances) if self.instances else False
        total_queries = sum(i.get("queries", 0) for i in self.instances)
        total_blocked = sum(i.get("blocked", 0) for i in self.instances)
        total_pct = (total_blocked / total_queries * 100) if total_queries > 0 else 0
        items.append({
            "name": "ALL",
            "status": "ON" if all_on else "OFF",
            "queries": fmt_num(total_queries),
            "pct": f"{total_pct:.0f}%",
        })

        def draw(d):
            # Rows 0-2: DNS1, DNS2, ALL (row 3 is blank)
            for row in range(min(len(items), 3)):
                item = items[row]
                y = self._row_y(row)
                sel = row == self.selected

                if sel:
                    d.rectangle([0, y, WIDTH - 1, y + self.ROW_H - 1], fill="white")
                    fill = "black"
                else:
                    fill = "white"

                # Layout: NAME  QUERIES(right)  PCT%(right)  STATUS(right)
                d.text((4, y + 2), item["name"], font=display.font, fill=fill)

                # Right-align queries at x=70
                q_bbox = d.textbbox((0, 0), item["queries"], font=display.font)
                d.text((70 - q_bbox[2], y + 2), item["queries"], font=display.font, fill=fill)

                # Right-align pct at x=100
                p_bbox = d.textbbox((0, 0), item["pct"], font=display.font)
                d.text((100 - p_bbox[2], y + 2), item["pct"], font=display.font, fill=fill)

                # Right-align status at right edge
                status = item["status"]
                s_bbox = d.textbbox((0, 0), status, font=display.font)
                d.text((WIDTH - s_bbox[2] - 4, y + 2), status, font=display.font, fill=fill)

            # Row 3: blank (could add hint or leave empty)

        display.render(draw)

    def _render_detail(self, display: Display) -> None:
        """Detail screen: 4-row grid with name, stats, and scrollable menu."""
        if self.selected >= len(self.instances):
            return  # ALL doesn't have detail view

        inst = self.instances[self.selected]
        name = inst.get("name", "?")
        enabled = inst.get("enabled", False)
        queries = inst.get("queries", 0)
        blocked = inst.get("blocked", 0)
        blocked_pct = inst.get("blocked_pct", 0)

        # Calculate which 2 menu items to show (scroll window)
        menu_len = len(self.DETAIL_MENU)
        if self.detail_selected == 0:
            visible_start = 0
        elif self.detail_selected == menu_len - 1:
            visible_start = menu_len - 2
        else:
            visible_start = self.detail_selected - 1

        def draw(d):
            # Row 0: Name + status
            y = self._row_y(0)
            d.text((4, y + 2), name, font=display.font, fill="white")
            status_text = "ON" if enabled else "OFF"
            bbox = d.textbbox((0, 0), status_text, font=display.font)
            d.text((WIDTH - bbox[2] - 4, y + 2), status_text, font=display.font, fill="white")

            # Row 1: Queries + blocked stats
            y = self._row_y(1)
            stats = f"Q:{fmt_num(queries)}  B:{fmt_num(blocked)} ({blocked_pct:.0f}%)"
            d.text((4, y + 2), stats, font=display.font, fill="white")

            # Rows 2-3: Scrollable menu (show 2 items)
            for i, menu_idx in enumerate([visible_start, visible_start + 1]):
                if menu_idx >= menu_len:
                    break
                y = self._row_y(2 + i)
                item = self.DETAIL_MENU[menu_idx]
                selected = menu_idx == self.detail_selected

                if selected:
                    d.rectangle([0, y, WIDTH - 1, y + self.ROW_H - 1], fill="white")
                    d.text((4, y + 2), item, font=display.font, fill="black")
                else:
                    d.text((4, y + 2), item, font=display.font, fill="white")

        display.render(draw)

    def _render_all_menu(self, display: Display) -> None:
        """ALL menu screen: status summary and action options."""
        all_on = all(i.get("enabled", False) for i in self.instances) if self.instances else False
        total_queries = sum(i.get("queries", 0) for i in self.instances)
        total_blocked = sum(i.get("blocked", 0) for i in self.instances)
        total_pct = (total_blocked / total_queries * 100) if total_queries > 0 else 0

        # Calculate which 2 menu items to show (scroll window)
        menu_len = len(self.ALL_MENU)
        if self.all_menu_selected == 0:
            visible_start = 0
        elif self.all_menu_selected == menu_len - 1:
            visible_start = menu_len - 2
        else:
            visible_start = self.all_menu_selected - 1

        def draw(d):
            # Row 0: ALL + status
            y = self._row_y(0)
            d.text((4, y + 2), "ALL", font=display.font, fill="white")
            status_text = "ON" if all_on else "OFF"
            bbox = d.textbbox((0, 0), status_text, font=display.font)
            d.text((WIDTH - bbox[2] - 4, y + 2), status_text, font=display.font, fill="white")

            # Row 1: Stats summary
            y = self._row_y(1)
            stats = f"Q:{fmt_num(total_queries)}  B:{fmt_num(total_blocked)} ({total_pct:.0f}%)"
            d.text((4, y + 2), stats, font=display.font, fill="white")

            # Rows 2-3: Scrollable menu (show 2 items)
            for i, menu_idx in enumerate([visible_start, visible_start + 1]):
                if menu_idx >= menu_len:
                    break
                y = self._row_y(2 + i)
                item = self.ALL_MENU[menu_idx]
                selected = menu_idx == self.all_menu_selected

                if selected:
                    d.rectangle([0, y, WIDTH - 1, y + self.ROW_H - 1], fill="white")
                    d.text((4, y + 2), item, font=display.font, fill="black")
                else:
                    d.text((4, y + 2), item, font=display.font, fill="white")

        display.render(draw)

    def _render_loading(self, display: Display) -> None:
        """Loading screen: centered icon and text in 4-row grid."""
        def draw(d):
            # Rows 0-1: blank/icon area
            # Row 1: Sync icon (centered)
            y = self._row_y(1)
            icon = ICON["sync"]
            icon_bbox = d.textbbox((0, 0), icon, font=display.icons_lg)
            icon_w = icon_bbox[2] - icon_bbox[0]
            d.text(((WIDTH - icon_w) // 2, y), icon, font=display.icons_lg, fill="white")

            # Row 2: "WORKING..." text (centered)
            y = self._row_y(2) + 4
            text = "WORKING..."
            text_bbox = d.textbbox((0, 0), text, font=display.font_bold)
            text_w = text_bbox[2] - text_bbox[0]
            d.text(((WIDTH - text_w) // 2, y), text, font=display.font_bold, fill="white")

            # Row 3: blank

        display.render(draw)

    def _render_confirm(self, display: Display) -> None:
        """Confirmation screen: 4-row grid with prompt and YES/NO."""
        target = self.confirm_target if self.confirm_target else "ALL"
        action = "Flush" if self.confirm_action == "flush" else "Enable"

        def draw(d):
            # Row 0: "Action X?"
            y = self._row_y(0)
            d.text((4, y + 2), f"{action} {target}?", font=display.font, fill="white")

            # Row 1: blank

            # Row 2: YES option
            y = self._row_y(2)
            if self.confirm_selected == 0:
                d.rectangle([0, y, WIDTH - 1, y + self.ROW_H - 1], fill="white")
                d.text((4, y + 2), "YES", font=display.font, fill="black")
            else:
                d.text((4, y + 2), "YES", font=display.font, fill="white")

            # Row 3: NO option
            y = self._row_y(3)
            if self.confirm_selected == 1:
                d.rectangle([0, y, WIDTH - 1, y + self.ROW_H - 1], fill="white")
                d.text((4, y + 2), "NO", font=display.font, fill="black")
            else:
                d.text((4, y + 2), "NO", font=display.font, fill="white")

        display.render(draw)

    def _render_duration(self, display: Display) -> None:
        """Duration selection screen: 4-row grid with disable options."""
        target = self.confirm_target if self.confirm_target else "ALL"

        def draw(d):
            # Row 0: "Disable X?"
            y = self._row_y(0)
            d.text((4, y + 2), f"Disable {target}?", font=display.font, fill="white")

            # Rows 1-3: Duration options (show 3 at a time, scroll if needed)
            num_opts = len(self.DURATION_OPTIONS)
            if self.duration_selected <= 1:
                visible_start = 0
            elif self.duration_selected >= num_opts - 1:
                visible_start = num_opts - 3
            else:
                visible_start = self.duration_selected - 1

            for i in range(3):
                opt_idx = visible_start + i
                if opt_idx >= num_opts:
                    break
                y = self._row_y(1 + i)
                label = self.DURATION_OPTIONS[opt_idx][0]
                selected = opt_idx == self.duration_selected

                if selected:
                    d.rectangle([0, y, WIDTH - 1, y + self.ROW_H - 1], fill="white")
                    d.text((4, y + 2), label, font=display.font, fill="black")
                else:
                    d.text((4, y + 2), label, font=display.font, fill="white")

        display.render(draw)

    def on_k1(self) -> None:
        """Navigate up."""
        if self.in_duration:
            self.duration_selected = (self.duration_selected - 1) % len(self.DURATION_OPTIONS)
        elif self.in_confirm:
            self.confirm_selected = (self.confirm_selected - 1) % 2
        elif self.in_all_menu:
            self.all_menu_selected = (self.all_menu_selected - 1) % len(self.ALL_MENU)
        elif self.in_detail:
            self.detail_selected = (self.detail_selected - 1) % len(self.DETAIL_MENU)
        else:
            n = len(self.instances) + 1  # instances + ALL
            self.selected = (self.selected - 1) % n

    def on_k2(self) -> None:
        """Select current item."""
        if self.in_duration:
            # Duration option selected
            _, duration_ms = self.DURATION_OPTIONS[self.duration_selected]
            if duration_ms == -1:
                # CANCEL
                self.in_duration = False
                self.duration_selected = 0
                self.confirm_target = None
            else:
                # Do the disable
                self._show_loading()
                if self.confirm_target:
                    if self.on_disable:
                        self.on_disable(self.confirm_target, duration_ms)
                else:
                    if self.on_disable_all:
                        self.on_disable_all(duration_ms)
                self.loading = False
                self.in_duration = False
                self.in_detail = False
                self.in_all_menu = False
                self.duration_selected = 0
                self.confirm_target = None
        elif self.in_confirm:
            if self.confirm_selected == 0:
                # YES - do the action
                self._show_loading()
                if self.confirm_action == "flush":
                    if self.confirm_target:
                        if self.on_flush:
                            self.on_flush(self.confirm_target)
                    else:
                        if self.on_flush_all:
                            self.on_flush_all()
                else:
                    # Enable
                    if self.confirm_target:
                        if self.on_enable:
                            self.on_enable(self.confirm_target)
                    else:
                        if self.on_enable_all:
                            self.on_enable_all()
                self.loading = False
                self.in_confirm = False
                self.in_detail = False
                self.in_all_menu = False  # Return to home after action
                self.confirm_target = None
                self.confirm_action = "enable"
            else:
                # NO - cancel
                self.in_confirm = False
                self.confirm_target = None
                self.confirm_action = "enable"
        elif self.in_detail:
            inst = self.instances[self.selected]
            name = inst.get("name", "")
            enabled = inst.get("enabled", False)
            if self.detail_selected == 0:
                # TOGGLE - check current state
                self.confirm_target = name
                if enabled:
                    # Currently ON -> show duration options to disable
                    self.duration_selected = 0
                    self.in_duration = True
                else:
                    # Currently OFF -> show simple enable confirmation
                    self.confirm_action = "enable"
                    self.confirm_selected = 0
                    self.in_confirm = True
            elif self.detail_selected == 1:
                # FLUSH - show confirmation
                self.confirm_target = name
                self.confirm_action = "flush"
                self.confirm_selected = 0
                self.in_confirm = True
            else:
                # BACK
                self.in_detail = False
                self.detail_selected = 0
        elif self.in_all_menu:
            if self.all_menu_selected == 0:
                # TOGGLE - check if all are on or some off
                all_on = all(i.get("enabled", False) for i in self.instances) if self.instances else False
                self.confirm_target = None
                if all_on:
                    # All ON -> show duration options to disable
                    self.duration_selected = 0
                    self.in_duration = True
                else:
                    # Some OFF -> show enable confirmation
                    self.confirm_action = "enable"
                    self.confirm_selected = 0
                    self.in_confirm = True
            elif self.all_menu_selected == 1:
                # FLUSH - show confirmation
                self.confirm_target = None
                self.confirm_action = "flush"
                self.confirm_selected = 0
                self.in_confirm = True
            else:
                # BACK
                self.in_all_menu = False
                self.all_menu_selected = 0
        else:
            if self.selected < len(self.instances):
                # Drill into detail
                self.in_detail = True
                self.detail_selected = 0
            else:
                # ALL - show menu
                self.in_all_menu = True
                self.all_menu_selected = 0

    def _show_loading(self) -> None:
        """Show loading screen immediately."""
        self.loading = True
        if self._display:
            self.render(self._display)

    def on_k3(self) -> None:
        """Navigate down."""
        if self.in_duration:
            self.duration_selected = (self.duration_selected + 1) % len(self.DURATION_OPTIONS)
        elif self.in_confirm:
            self.confirm_selected = (self.confirm_selected + 1) % 2
        elif self.in_all_menu:
            self.all_menu_selected = (self.all_menu_selected + 1) % len(self.ALL_MENU)
        elif self.in_detail:
            self.detail_selected = (self.detail_selected + 1) % len(self.DETAIL_MENU)
        else:
            n = len(self.instances) + 1  # instances + ALL
            self.selected = (self.selected + 1) % n
