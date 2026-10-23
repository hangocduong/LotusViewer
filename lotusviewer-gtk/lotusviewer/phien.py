"""Bảng phiên: dòng trạng thái, quyền điều khiển, chat, tệp, clipboard và nút Kết thúc."""
from __future__ import annotations

from typing import Callable

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk  # noqa: E402

from . import chuoi  # noqa: E402
from .engine import one_line  # noqa: E402
from .model import Phien  # noqa: E402


class HopNhanTep(Gtk.Dialog):
    """«Nhận tệp ‹tên› (‹cỡ›)?». Engine chỉ ghi tệp sau `a <id>`; Từ chối hay đóng hộp gửi `r <id>`."""

    def __init__(self, parent: Gtk.Window | None, file_id: str, name: str, size: int,
                 send: Callable[[str], None]):
        super().__init__(title=chuoi.TEP_TIEU_DE, transient_for=parent, modal=False, destroy_with_parent=True)
        self.file_id, self._send, self._answered = file_id, send, False
        self.add_button(chuoi.TEP_TU_CHOI, Gtk.ResponseType.REJECT)
        self.add_button(chuoi.TEP_NHAN, Gtk.ResponseType.ACCEPT)
        self.set_default_response(Gtk.ResponseType.REJECT)
        label = Gtk.Label(label=chuoi.TEP_NOI_DUNG.format(ten=name, co=chuoi.co_tep(size)), xalign=0,
                          wrap=True, max_width_chars=48, margin=12)
        self.get_content_area().add(label)
        self.connect("response", self._on_response)
        self.set_keep_above(True)
        self.show_all()
        self.present()

    def _on_response(self, _dialog, response: int) -> None:
        self.answer(response == Gtk.ResponseType.ACCEPT)

    def answer(self, accept: bool) -> None:
        if self._answered:
            return
        self._answered = True
        self._send(f"{'a' if accept else 'r'} {self.file_id}")
        self.destroy()

    def dismiss(self) -> None:
        """Phiên đã kết thúc: engine tự huỷ tệp, chỉ đóng hộp."""
        self._answered = True
        self.destroy()


class BangPhien(Gtk.Box):
    def __init__(self, send: Callable[[str], None], choose_file: Callable[[], None], end: Callable[[], None]):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self._send = send
        self._syncing = False

        self.headline = Gtk.Label(xalign=0, wrap=True)
        self.headline.get_style_context().add_class("lv-headline")
        self.pack_start(self.headline, False, False, 0)

        self.control_row = Gtk.Box(spacing=12)
        self.control_row.pack_start(Gtk.Label(label=chuoi.PHIEN_CHO_PHEP_DIEU_KHIEN, xalign=0), True, True, 0)
        self.control = Gtk.Switch(valign=Gtk.Align.CENTER)
        self.control.connect("state-set", self._on_control)
        self.control_row.pack_end(self.control, False, False, 0)
        self.pack_start(self.control_row, False, False, 0)
        self.control_note = Gtk.Label(xalign=0, wrap=True)
        self.pack_start(self.control_note, False, False, 0)
        self.clipboard_note = Gtk.Label(xalign=0)
        self.pack_start(self.clipboard_note, False, False, 0)

        self.chat_view = Gtk.TextView(editable=False, cursor_visible=False, wrap_mode=Gtk.WrapMode.WORD_CHAR,
                                      left_margin=6, right_margin=6)
        scroll = Gtk.ScrolledWindow(min_content_height=160, shadow_type=Gtk.ShadowType.IN)
        scroll.add(self.chat_view)
        self.pack_start(scroll, True, True, 0)

        compose = Gtk.Box(spacing=8)
        self.entry = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR, accepts_tab=False, left_margin=6,
                                  right_margin=6, top_margin=4, bottom_margin=4)
        self.entry.connect("key-press-event", self._on_key)
        entry_scroll = Gtk.ScrolledWindow(min_content_height=48, shadow_type=Gtk.ShadowType.IN)
        entry_scroll.add(self.entry)
        compose.pack_start(entry_scroll, True, True, 0)
        self.send_button = Gtk.Button(label=chuoi.PHIEN_GUI, valign=Gtk.Align.END)
        self.send_button.connect("clicked", lambda _b: self.send_chat())
        compose.pack_start(self.send_button, False, False, 0)
        self.pack_start(compose, False, False, 0)

        buttons = Gtk.Box(spacing=8)
        self.file_button = Gtk.Button(label=chuoi.PHIEN_GUI_TEP)
        self.file_button.connect("clicked", lambda _b: choose_file())
        buttons.pack_start(self.file_button, False, False, 0)
        self.end_button = Gtk.Button(label=chuoi.PHIEN_KET_THUC)
        self.end_button.get_style_context().add_class("destructive-action")
        self.end_button.connect("clicked", lambda _b: end())
        buttons.pack_end(self.end_button, False, False, 0)
        self.pack_start(buttons, False, False, 0)

    def show_state(self, phien: Phien) -> None:
        self.headline.set_text(phien.headline())
        host = phien.mode == "host"
        self.control_row.set_visible(host)
        self.control_note.set_visible(not host)
        self.control_note.set_text(chuoi.PHIEN_DUOC_DIEU_KHIEN if phien.control else chuoi.PHIEN_CHI_XEM)
        self._syncing = True
        self.control.set_active(phien.control)
        self.control.set_state(phien.control)
        self._syncing = False
        self.clipboard_note.set_text(chuoi.PHIEN_CLIPBOARD_BAT if phien.clipboard else chuoi.PHIEN_CLIPBOARD_TAT)

    def _on_control(self, _switch, _state: bool) -> bool:
        if not self._syncing:
            self._send("c")
        return True  # công tắc chỉ đổi khi engine báo dòng CONTROL

    def _on_key(self, view, event) -> bool:
        # Enter gửi tin, Shift+Enter xuống dòng. Bộ gõ (fcitx5) xử lý phím trước để không cắt ngang chữ đang gõ.
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) and not event.state & Gdk.ModifierType.SHIFT_MASK:
            if not view.im_context_filter_keypress(event):
                self.send_chat()
            return True
        return False

    def send_chat(self) -> None:
        buf = self.entry.get_buffer()
        text = one_line(buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False))
        if not text:
            return
        self._send(f"t {text}")
        self.add_line(chuoi.PHIEN_BAN, text)
        buf.set_text("")

    def add_line(self, who: str, text: str) -> None:
        buf = self.chat_view.get_buffer()
        buf.insert(buf.get_end_iter(), f"{who}: {text}\n")
        self.chat_view.scroll_to_mark(buf.get_insert(), 0, False, 0, 0)

    def clear(self) -> None:
        self.chat_view.get_buffer().set_text("")
        self.entry.get_buffer().set_text("")
