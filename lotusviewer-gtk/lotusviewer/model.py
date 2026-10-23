"""Trạng thái phiên và ánh xạ sự kiện engine sang chuỗi tiếng Việt. Không phụ thuộc GTK."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

from . import chuoi
from .engine import Event

GUI_CONF_PATH = "/usr/share/lotusviewer/gui.conf"


@dataclass
class Phien:
    """Trạng thái của một engine. `mode` là "host" hoặc "connect"."""

    mode: str
    clipboard: bool = False
    my_id: str = ""
    my_password: str = ""
    request: Event | None = None
    peer_id: str = ""
    peer_name: str = ""
    connected: bool = False
    control: bool = False
    status: str = ""
    ended: str = ""
    files: dict[str, tuple[str, int]] = field(default_factory=dict)
    mismatch: bool = False

    def apply(self, event: Event) -> str | None:
        """Cập nhật trạng thái; trả về việc GUI cần làm thêm (mở/đóng hộp, thêm dòng chat…) hoặc None."""
        kind = event.kind
        if kind == "hello":
            if event.version != 1:
                self.mismatch = True
                return "mismatch"
            return None
        if kind == "id":
            self.my_id, self.my_password = event.peer, event.text
            return "id"
        if kind == "request":
            if self.mode != "host" or self.connected:
                return None
            self.request = event
            self.peer_id, self.peer_name = event.peer, event.text
            return "request"
        if kind == "connected":
            self.request = None
            self.connected = True
            self.peer_id = event.peer
            return "connected"
        if kind == "control":
            self.control = event.on
            return "control"
        if kind == "chat":
            return "chat" if self.connected else None
        if kind == "file":
            if not self.connected:
                return None
            self.files[event.file_id] = (event.text, event.size)
            return "file"
        if kind in ("file-done", "file-fail"):
            return kind
        if kind == "status":
            self.status = chuoi.ly_do(event.text, self.status or chuoi.DK_DANG_KET_NOI)
            return "status"
        if kind == "ended":
            had_request = self.request is not None
            self.request = None
            self.connected = False
            self.control = False
            self.files.clear()
            self.ended = chuoi.ly_do(event.text)
            return "ended-request" if had_request else "ended"
        return None

    def file_name(self, file_id: str) -> str:
        return self.files.get(file_id, ("", 0))[0]

    def headline(self) -> str:
        """Dòng trạng thái luôn hiện khi đang có phiên."""
        if not self.connected:
            return ""
        if self.mode == "host":
            return chuoi.PHIEN_DUOC_HO_TRO.format(ten=self.peer_name or chuoi.DUYET_TEN_TRONG)
        template = chuoi.PHIEN_DIEU_KHIEN if self.control else chuoi.PHIEN_CHI_XEM_DIEU_KHIEN
        return template.format(id=group_id(self.peer_id))


def request_text(event: Event) -> str:
    ten = event.text.strip() or chuoi.DUYET_TEN_TRONG
    return chuoi.DUYET_NOI_DUNG.format(ten=ten, id=group_id(event.peer))


def group_id(digits: str) -> str:
    """123456789 → «123 456 789», cách UltraViewer hiện ID."""
    head = len(digits) % 3 or 3
    parts = [digits[:head]] + [digits[i:i + 3] for i in range(head, len(digits), 3)]
    return " ".join(p for p in parts if p)


def wayland_session(env: dict[str, str]) -> bool:
    return env.get("XDG_SESSION_TYPE", "").lower() == "wayland"


def read_accent(root: Path = Path("/")) -> tuple[str, str] | None:
    """(ACCENT_HEX, ACCENT_FG_HEX) từ gui.conf của gói. Thiếu hoặc sai định dạng thì None: giữ màu theme."""
    try:
        text = (root / GUI_CONF_PATH.lstrip("/")).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    values = {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        value = value.strip().strip("\"'")
        if sep and re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
            values[key.strip()] = value.upper()
    if "ACCENT_HEX" in values and "ACCENT_FG_HEX" in values:
        return values["ACCENT_HEX"], values["ACCENT_FG_HEX"]
    return None
