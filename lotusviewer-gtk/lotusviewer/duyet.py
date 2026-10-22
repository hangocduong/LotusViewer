"""Hộp duyệt kết nối đến. Đây là nơi duy nhất gửi `y`/`v`/`n` cho engine.

Mặc định là Từ chối: nút này giữ focus và là phản hồi mặc định; đóng hộp hay hết giờ đều gửi `n`.
"""
from __future__ import annotations

from typing import Callable

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

from . import chuoi  # noqa: E402

TIMEOUT_SECONDS = 60
TU_CHOI, CHI_XEM, DIEU_KHIEN = 1, 2, 3
COMMANDS = {TU_CHOI: "n", CHI_XEM: "v", DIEU_KHIEN: "y"}
MAC_DINH = TU_CHOI

# timer(giây, hàm) gọi hàm sau mỗi khoảng; hàm trả False thì dừng. Trả về hàm huỷ.
Timer = Callable[[int, Callable[[], bool]], Callable[[], None]]


def glib_timer(seconds: int, tick: Callable[[], bool]) -> Callable[[], None]:
    source = GLib.timeout_add_seconds(seconds, tick)
    return lambda: GLib.source_remove(source)


class HopDuyet(Gtk.Dialog):
    def __init__(self, parent: Gtk.Window | None, text: str, answer: Callable[[str], None],
                 timer: Timer = glib_timer):
        super().__init__(title=chuoi.DUYET_TIEU_DE, transient_for=parent, modal=True, destroy_with_parent=True)
        self._answer = answer
        self._answered = False
        self.remaining = TIMEOUT_SECONDS
        self.set_keep_above(True)
        self.set_urgency_hint(True)
        self.set_resizable(False)

        self.buttons = {
            TU_CHOI: self.add_button(chuoi.DUYET_TU_CHOI, TU_CHOI),
            CHI_XEM: self.add_button(chuoi.DUYET_CHI_XEM, CHI_XEM),
            DIEU_KHIEN: self.add_button(chuoi.DUYET_DIEU_KHIEN, DIEU_KHIEN),
        }
        self.set_default_response(MAC_DINH)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, border_width=12)
        self.get_content_area().add(box)
        self.message = Gtk.Label(label=text, xalign=0, wrap=True, max_width_chars=48, selectable=False)
        self.message.get_style_context().add_class("lv-headline")
        box.pack_start(self.message, False, False, 0)
        self.countdown = Gtk.Label(xalign=0)
        box.pack_start(self.countdown, False, False, 0)
        self._show_remaining()

        self.connect("response", self._on_response)
        self._cancel_timer = timer(1, self._tick)
        self.show_all()
        self.buttons[MAC_DINH].grab_focus()

    def _show_remaining(self) -> None:
        self.countdown.set_text(chuoi.DUYET_DEM_NGUOC.format(giay=self.remaining))

    def _tick(self) -> bool:
        if self._answered:
            return False
        self.remaining -= 1
        if self.remaining <= 0:
            self.choose(MAC_DINH)
            return False
        self._show_remaining()
        return True

    def _on_response(self, _dialog, response: int) -> None:
        # Esc, nút đóng cửa sổ hay phản hồi lạ đều là mặc định (Từ chối).
        self.choose(response if response in COMMANDS else MAC_DINH)

    def choose(self, choice: int) -> None:
        if self._answered:
            return
        self._answered = True
        self._cancel_timer()
        self._answer(COMMANDS[choice])
        self.destroy()

    def dismiss(self) -> None:
        """Engine đã tự kết thúc yêu cầu (hết giờ phía engine, máy kia huỷ): đóng hộp, không gửi gì."""
        if self._answered:
            return
        self._answered = True
        self._cancel_timer()
        self.destroy()
