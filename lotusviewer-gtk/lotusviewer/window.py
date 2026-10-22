"""Cửa sổ chính: tab Nhận hỗ trợ, tab Điều khiển máy khác và bảng phiên.

Mỗi lúc chỉ có một engine. Sự kiện engine đến từ luồng đọc và được chuyển về luồng chính bằng `dispatch`.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from . import chuoi, model  # noqa: E402
from .cai_dat import CaiDat, HopCaiDat, cache_dir, config_dir  # noqa: E402
from .duyet import HopDuyet, glib_timer  # noqa: E402
from .engine import ENGINE_PATH, Engine, Event, clean_env, connect_argv, host_argv, normalize_id, one_line  # noqa: E402
from .phien import BangPhien, HopNhanTep  # noqa: E402


def css(accent: tuple[str, str] | None) -> bytes:
    text = """
.lv-headline { font-size: 120%; font-weight: bold; }
.lv-id { font-size: 200%; font-weight: bold; }
"""
    if accent is not None:
        text += ("button.suggested-action:not(:disabled) { background-image: none; "
                 f"background-color: {accent[0]}; color: {accent[1]}; }}\n")
    return text.encode()


def _once(fn, *args) -> bool:
    fn(*args)
    return False


def confirm_close(parent: Gtk.Window) -> bool:
    dialog = Gtk.MessageDialog(transient_for=parent, modal=True, message_type=Gtk.MessageType.QUESTION,
                               text=chuoi.DONG_TIEU_DE, secondary_text=chuoi.DONG_NOI_DUNG)
    dialog.add_buttons(chuoi.DONG_O_LAI, Gtk.ResponseType.CANCEL, chuoi.DONG_DONG, Gtk.ResponseType.OK)
    dialog.set_default_response(Gtk.ResponseType.CANCEL)
    response = dialog.run()
    dialog.destroy()
    return response == Gtk.ResponseType.OK


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, application=None, env: dict[str, str] | None = None, engine_path: str = ENGINE_PATH,
                 root: Path = Path("/"), timer=glib_timer,
                 confirm: Callable[[Gtk.Window], bool] = confirm_close):
        super().__init__(application=application, title=chuoi.TEN_APP)
        self.env = dict(os.environ if env is None else env)
        self.engine_path, self.timer, self.confirm = engine_path, timer, confirm
        self.settings_path = config_dir(self.env) / "gui.json"
        self.log_path = cache_dir(self.env) / "engine.log"
        self.cai_dat = CaiDat.load(self.settings_path)
        self.engine: Engine | None = None
        self.phien: model.Phien | None = None
        self.hop_duyet: HopDuyet | None = None
        self.hop_tep: dict[str, HopNhanTep] = {}
        self._pending_id = ""
        self.set_default_size(480, -1)
        self.set_border_width(18)
        self.set_icon_name("vn.lotusos.LotusViewer")

        provider = Gtk.CssProvider()
        provider.load_from_data(css(model.read_accent(root)))
        screen = Gdk.Screen.get_default()
        if screen is not None:
            Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.stack = Gtk.Stack()
        self.add(self.stack)
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.notebook = Gtk.Notebook()
        outer.pack_start(self.notebook, True, True, 0)
        settings_row = Gtk.Box()
        self.settings_button = Gtk.Button(label=chuoi.CAI_DAT)
        self.settings_button.connect("clicked", self._open_settings)
        settings_row.pack_end(self.settings_button, False, False, 0)
        outer.pack_start(settings_row, False, False, 0)
        self.stack.add_named(outer, "tabs")
        self.panel = BangPhien(self.send, self._choose_file, lambda: self.send("x"))
        self.stack.add_named(self.panel, "session")

        self._build_host_tab()
        self._build_connect_tab()
        self.connect("delete-event", self._on_delete)
        self.connect("destroy", self._on_destroy)
        self.show_all()
        self.stack.set_visible_child_name("tabs")
        self._refresh()

    # --- dựng tab ---------------------------------------------------------------------------
    @staticmethod
    def _label(parent: Gtk.Box, text: str = "", css_class: str | None = None) -> Gtk.Label:
        label = Gtk.Label(label=text, xalign=0, wrap=True)
        if css_class:
            label.get_style_context().add_class(css_class)
        parent.pack_start(label, False, False, 0)
        return label

    def _clipboard_row(self, parent: Gtk.Box) -> Gtk.Switch:
        row = Gtk.Box(spacing=12)
        caption = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._label(caption, chuoi.CLIPBOARD)
        self._label(caption, chuoi.CLIPBOARD_GHI_CHU).get_style_context().add_class("dim-label")
        row.pack_start(caption, True, True, 0)
        switch = Gtk.Switch(active=self.cai_dat.clipboard, valign=Gtk.Align.CENTER)
        row.pack_end(switch, False, False, 0)
        parent.pack_start(row, False, False, 0)
        return switch

    def _build_host_tab(self) -> None:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, border_width=12)
        self._label(box, chuoi.NHAN_GIOI_THIEU)
        self._label(box, chuoi.NHAN_ID)
        self.host_id = self._label(box, chuoi.NHAN_CHUA_CO, "lv-id")
        self.host_id.set_selectable(True)
        self._label(box, chuoi.NHAN_MAT_KHAU)
        self.host_password = self._label(box, chuoi.NHAN_CHUA_CO, "lv-id")
        self.host_password.set_selectable(True)
        self.host_clipboard = self._clipboard_row(box)
        self.host_status = self._label(box)
        self.host_button = Gtk.Button(label=chuoi.NHAN_BAT_DAU, halign=Gtk.Align.END)
        self.host_button.connect("clicked", self._on_host_button)
        box.pack_start(self.host_button, False, False, 0)
        self.notebook.append_page(box, Gtk.Label(label=chuoi.TAB_NHAN))

    def _build_connect_tab(self) -> None:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, border_width=12)
        self._label(box, chuoi.DK_GIOI_THIEU)
        grid = Gtk.Grid(row_spacing=8, column_spacing=12)
        self.connect_id = Gtk.ComboBoxText.new_with_entry()
        self.connect_id.set_hexpand(True)
        self.connect_id.get_child().set_placeholder_text(chuoi.DK_GAN_DAY)
        self.connect_password = Gtk.Entry(visibility=False, input_purpose=Gtk.InputPurpose.PASSWORD,
                                          activates_default=True)
        for row, (text, widget) in enumerate(((chuoi.DK_ID, self.connect_id),
                                              (chuoi.DK_MAT_KHAU, self.connect_password))):
            grid.attach(Gtk.Label(label=text, xalign=0), 0, row, 1, 1)
            grid.attach(widget, 1, row, 1, 1)
        box.pack_start(grid, False, False, 0)
        self.connect_clipboard = self._clipboard_row(box)
        self.connect_status = self._label(box)
        self.connect_button = Gtk.Button(label=chuoi.DK_KET_NOI, halign=Gtk.Align.END)
        self.connect_button.get_style_context().add_class("suggested-action")
        self.connect_button.connect("clicked", lambda _b: self.start_connect())
        box.pack_start(self.connect_button, False, False, 0)
        self.notebook.append_page(box, Gtk.Label(label=chuoi.TAB_DIEU_KHIEN))
        self._fill_recent()

    def _fill_recent(self) -> None:
        self.connect_id.remove_all()
        for partner_id in self.cai_dat.gan_day:
            self.connect_id.append_text(model.group_id(partner_id))

    # --- engine ----------------------------------------------------------------------------
    def _spawn(self, mode: str, argv: list[str], clipboard: bool, first_line: str | None = None) -> bool:
        phien = model.Phien(mode, clipboard=clipboard)
        engine_box: list[Engine] = []

        # Luồng đọc có thể chạy trước khi `engine_box` có phần tử; chỉ đọc nó trên luồng chính.
        def on_event(event: Event) -> None:
            GLib.idle_add(_once, lambda: self._on_event(engine_box[0], event))

        def on_exit(code: int) -> None:
            GLib.idle_add(_once, lambda: self._on_exit(engine_box[0], code))

        try:
            os.makedirs(self.cai_dat.download_dir(), exist_ok=True)
            engine = Engine(argv, clean_env(self.env, self.cai_dat.ten_hien_thi), self.log_path,
                            on_event, on_exit, first_line=first_line)
        except OSError:
            self._message(mode, chuoi.LOI_ENGINE.format(log=self.log_path))
            return False
        engine_box.append(engine)
        self.engine, self.phien = engine, phien
        self._refresh()
        return True

    def start_host(self) -> bool:
        if self.engine is not None or model.wayland_session(self.env):
            return False
        clipboard = self.host_clipboard.get_active()
        self.host_status.set_text(chuoi.NHAN_DANG_DANG_KY)
        return self._spawn("host", host_argv(self.engine_path, self.cai_dat.download_dir(), clipboard), clipboard)

    def stop_host(self) -> None:
        if self.engine is not None and self.phien is not None and self.phien.mode == "host":
            self.engine.close_stdin()

    def start_connect(self) -> bool:
        if self.engine is not None:
            return False
        partner_id = normalize_id(self.connect_id.get_child().get_text())
        if partner_id is None:
            self._message("connect", chuoi.DK_ID_SAI)
            return False
        password = self.connect_password.get_text().strip()
        if not password or one_line(password) != password:
            self._message("connect", chuoi.DK_THIEU_MAT_KHAU)
            return False
        clipboard = self.connect_clipboard.get_active()
        self._message("connect", chuoi.DK_DANG_KET_NOI)
        argv = connect_argv(self.engine_path, partner_id, self.cai_dat.download_dir(), clipboard)
        if not self._spawn("connect", argv, clipboard, first_line=password):
            return False
        self.connect_password.set_text("")
        self._pending_id = partner_id
        return True

    def send(self, command: str) -> None:
        if self.engine is not None:
            self.engine.send(command)

    def _on_destroy(self, _window) -> None:
        if self.engine is not None:
            self.engine.close_stdin()
        self.engine = None

    def _on_event(self, engine: Engine, event: Event) -> None:
        if engine is not self.engine or self.phien is None:
            return
        phien = self.phien
        action = phien.apply(event)
        if action == "mismatch":
            engine.close_stdin()
            self._message(phien.mode, chuoi.LOI_PHIEN_BAN)
        elif action == "id":
            self.host_id.set_text(model.group_id(phien.my_id))
            self.host_password.set_text(phien.my_password)
            self.host_status.set_text(chuoi.NHAN_DANG_CHO)
        elif action == "request":
            self._close_request()
            self.hop_duyet = HopDuyet(self, model.request_text(event), self.send, timer=self.timer)
        elif action == "connected":
            self._close_request()
            if phien.mode == "connect":
                self.cai_dat.remember(self._pending_id)
                self.cai_dat.save(self.settings_path)
                self._fill_recent()
            self.panel.clear()
            self.stack.set_visible_child_name("session")
        elif action == "chat":
            self.panel.add_line(chuoi.PHIEN_MAY_KIA, event.text)
        elif action == "file":
            self.hop_tep[event.file_id] = HopNhanTep(self, event.file_id, event.text, event.size,
                                                     lambda cmd, fid=event.file_id: self._answer_file(fid, cmd))
        elif action in ("file-done", "file-fail"):
            self._file_finished(event, action)
        elif action == "status":
            self._message(phien.mode, phien.status)
        elif action in ("ended", "ended-request"):
            self._close_request()
            self._close_file_dialogs()
            self.stack.set_visible_child_name("tabs")
            self._message(phien.mode, phien.ended)
        self.panel.show_state(phien)
        self._refresh()

    def _answer_file(self, file_id: str, command: str) -> None:
        self.hop_tep.pop(file_id, None)
        self.send(command)

    def _file_finished(self, event: Event, action: str) -> None:
        dialog = self.hop_tep.pop(event.file_id, None)
        if dialog is not None:
            dialog.dismiss()
        name = self.phien.files.pop(event.file_id, ("", 0))[0]
        if action == "file-done":
            text = chuoi.PHIEN_TEP_XONG.format(ten=name) if name else chuoi.PHIEN_TEP_GUI_XONG
        elif name:
            text = (chuoi.PHIEN_TEP_HUY if event.text == "Canceled" else chuoi.PHIEN_TEP_LOI).format(ten=name)
        else:
            text = chuoi.LOI_GUI_TEP
        self.panel.add_line(chuoi.TEN_APP, text)

    def _on_exit(self, engine: Engine, code: int) -> None:
        if engine is not self.engine:
            return
        mode = self.phien.mode if self.phien else "host"
        clean = self.phien is not None and (self.phien.ended or self.phien.mismatch)
        self._close_request()
        self._close_file_dialogs()
        self.engine, self.phien = None, None
        self.stack.set_visible_child_name("tabs")
        if mode == "host":
            self.host_id.set_text(chuoi.NHAN_CHUA_CO)
            self.host_password.set_text(chuoi.NHAN_CHUA_CO)
            if code == 0:
                self.host_status.set_text("")
        if code != 0 and not clean:
            self._message(mode, chuoi.LOI_ENGINE.format(log=self.log_path))
        self._refresh()

    def _close_request(self) -> None:
        if self.hop_duyet is not None:
            self.hop_duyet.dismiss()
            self.hop_duyet = None

    def _close_file_dialogs(self) -> None:
        for dialog in self.hop_tep.values():
            dialog.dismiss()
        self.hop_tep.clear()

    # --- giao diện ---------------------------------------------------------------------------
    def _message(self, mode: str, text: str) -> None:
        (self.host_status if mode == "host" else self.connect_status).set_text(text)

    def _refresh(self) -> None:
        busy = self.engine is not None
        hosting = busy and self.phien is not None and self.phien.mode == "host"
        if model.wayland_session(self.env):
            self.host_button.set_sensitive(False)
            self.host_status.set_text(chuoi.NHAN_CHI_X11)
        else:
            self.host_button.set_sensitive(hosting or not busy)
        self.host_button.set_label(chuoi.NHAN_DUNG if hosting else chuoi.NHAN_BAT_DAU)
        style = self.host_button.get_style_context()
        (style.remove_class if hosting else style.add_class)("suggested-action")
        self.connect_button.set_sensitive(not busy)
        self.host_clipboard.set_sensitive(not busy)
        self.connect_clipboard.set_sensitive(not busy)
        self.settings_button.set_sensitive(not busy)

    def _on_host_button(self, _button) -> None:
        if self.engine is not None:
            self.stop_host()
        else:
            self.start_host()

    def _choose_file(self) -> None:
        chooser = Gtk.FileChooserDialog(title=chuoi.PHIEN_CHON_TEP, transient_for=self,
                                        action=Gtk.FileChooserAction.OPEN, modal=True)
        chooser.add_buttons(chuoi.PHIEN_HUY, Gtk.ResponseType.CANCEL, chuoi.PHIEN_CHON, Gtk.ResponseType.ACCEPT)
        chooser.set_local_only(True)
        response = chooser.run()
        path = chooser.get_filename() if response == Gtk.ResponseType.ACCEPT else None
        chooser.destroy()
        if path:
            self.send_file(path)

    def send_file(self, path: str) -> bool:
        if one_line(path) != path or not os.path.isfile(path):
            self.panel.add_line(chuoi.TEN_APP, chuoi.LOI_GUI_TEP)
            return False
        self.send(f"f {path}")
        self.panel.add_line(chuoi.TEN_APP, chuoi.PHIEN_DA_GUI_TEP.format(ten=os.path.basename(path)))
        return True

    def _open_settings(self, _button) -> None:
        dialog = HopCaiDat(self, self.cai_dat)
        if dialog.run() == Gtk.ResponseType.OK:
            dialog.apply_to(self.cai_dat)
            self.cai_dat.save(self.settings_path)
            if self.engine is None:
                self.host_clipboard.set_active(self.cai_dat.clipboard)
                self.connect_clipboard.set_active(self.cai_dat.clipboard)
        dialog.destroy()

    def _on_delete(self, *_args) -> bool:
        if self.engine is None:
            return False
        if self.phien is not None and (self.phien.connected or self.phien.request is not None):
            if not self.confirm(self):
                return True
        self.engine.close_stdin()
        return False
