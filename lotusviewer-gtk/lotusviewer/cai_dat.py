"""Cài đặt ở `~/.config/lotusviewer/gui.json` và hộp cài đặt. Không có master password ở v1."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

from . import chuoi  # noqa: E402
from .engine import normalize_id, one_line  # noqa: E402

MAX_RECENT = 10


def config_dir(env: dict[str, str]) -> Path:
    base = env.get("XDG_CONFIG_HOME") or os.path.join(env.get("HOME", os.path.expanduser("~")), ".config")
    return Path(base) / "lotusviewer"


def cache_dir(env: dict[str, str]) -> Path:
    base = env.get("XDG_CACHE_HOME") or os.path.join(env.get("HOME", os.path.expanduser("~")), ".cache")
    return Path(base) / "lotusviewer"


def default_download_dir() -> str:
    return GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD) or str(Path.home() / "Downloads")


@dataclass
class CaiDat:
    ten_hien_thi: str = ""
    thu_muc_nhan: str = ""
    clipboard: bool = False
    gan_day: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "CaiDat":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        recent = data.get("gan_day")
        return cls(
            ten_hien_thi=one_line(data["ten_hien_thi"]) if isinstance(data.get("ten_hien_thi"), str) else "",
            thu_muc_nhan=data["thu_muc_nhan"] if isinstance(data.get("thu_muc_nhan"), str) else "",
            clipboard=data.get("clipboard") is True,
            gan_day=[i for i in recent if isinstance(i, str) and normalize_id(i) == i][:MAX_RECENT]
            if isinstance(recent, list) else [],
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        tmp = path.with_suffix(".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with open(fd, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)

    def download_dir(self) -> str:
        return self.thu_muc_nhan or default_download_dir()

    def remember(self, partner_id: str) -> None:
        self.gan_day = [partner_id] + [i for i in self.gan_day if i != partner_id][:MAX_RECENT - 1]


class HopCaiDat(Gtk.Dialog):
    def __init__(self, parent: Gtk.Window, cai_dat: CaiDat):
        super().__init__(title=chuoi.CD_TIEU_DE, transient_for=parent, modal=True, destroy_with_parent=True)
        self.add_button(chuoi.CD_HUY, Gtk.ResponseType.CANCEL)
        luu = self.add_button(chuoi.CD_LUU, Gtk.ResponseType.OK)
        luu.get_style_context().add_class("suggested-action")
        self.set_default_response(Gtk.ResponseType.OK)

        grid = Gtk.Grid(row_spacing=10, column_spacing=12, border_width=12)
        self.get_content_area().add(grid)
        self.ten = Gtk.Entry(text=cai_dat.ten_hien_thi, placeholder_text=chuoi.CD_TEN_GOI_Y, max_length=64,
                             activates_default=True, hexpand=True)
        self.thu_muc = Gtk.FileChooserButton(title=chuoi.CD_THU_MUC, action=Gtk.FileChooserAction.SELECT_FOLDER)
        self.thu_muc.set_filename(cai_dat.download_dir())
        self.clipboard = Gtk.Switch(active=cai_dat.clipboard, halign=Gtk.Align.START)
        for row, (text, widget) in enumerate(((chuoi.CD_TEN, self.ten), (chuoi.CD_THU_MUC, self.thu_muc),
                                              (chuoi.CD_CLIPBOARD, self.clipboard))):
            grid.attach(Gtk.Label(label=text, xalign=0), 0, row, 1, 1)
            grid.attach(widget, 1, row, 1, 1)
        self.show_all()

    def apply_to(self, cai_dat: CaiDat) -> None:
        cai_dat.ten_hien_thi = one_line(self.ten.get_text())
        folder = self.thu_muc.get_filename()
        if folder:
            cai_dat.thu_muc_nhan = folder
        cai_dat.clipboard = self.clipboard.get_active()
