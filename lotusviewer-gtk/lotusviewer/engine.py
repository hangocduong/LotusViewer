"""Chạy `lotusviewer-engine` ở chế độ `--ipc` và nói chuyện với nó qua stdin/stdout.

Hợp đồng dòng nằm ở `LinuxViewer/src/ipc.rs`. Parser ở đây chặt: dòng lạ hoặc JSON hỏng chỉ được ghi
log rồi bỏ qua, không bao giờ thành sự kiện. Không hàm nào ở đây gửi `y`/`v`/`n`; chỉ hộp duyệt làm
việc đó qua `Engine.send`.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import threading
from typing import Callable

ENGINE_PATH = "/usr/lib/lotusviewer/lotusviewer-engine"
IPC_VERSION = 1

_ENV_EXACT = {"DISPLAY", "XAUTHORITY", "HOME", "LANG", "PATH"}
_ENV_PREFIX = ("XDG_", "LC_")
_DIGITS = r"[0-9]{1,64}"
_TOKEN = r"[A-Za-z0-9_-]{1,64}"
_JSON = r'"(?:[^"\\\x00-\x1f]|\\.)*"'
_RULES = (
    ("hello", re.compile(r"IPC ([0-9]{1,9})")),
    ("id", re.compile(rf"ID ({_DIGITS}) PASSWORD ({_JSON})")),
    ("request", re.compile(rf"REQUEST ({_DIGITS}) ({_JSON})")),
    ("connected", re.compile(rf"CONNECTED ({_DIGITS})")),
    ("control", re.compile(r"CONTROL (on|off)")),
    ("chat", re.compile(rf"CHAT ({_JSON})")),
    ("file", re.compile(rf"FILE ({_TOKEN}) ([0-9]{{1,20}}) ({_JSON})")),
    ("file-done", re.compile(rf"FILE-DONE ({_TOKEN})")),
    ("file-fail", re.compile(rf"FILE-FAIL ({_TOKEN}) ({_JSON})")),
    ("status", re.compile(rf"STATUS ({_JSON})")),
    ("ended", re.compile(rf"ENDED ({_JSON})")),
)


@dataclass(frozen=True)
class Event:
    kind: str
    peer: str = ""
    text: str = ""
    file_id: str = ""
    size: int = 0
    on: bool = False
    version: int = 0


def _json_text(raw: str) -> str | None:
    try:
        value = json.loads(raw)
        value.encode("utf-8")
    except (ValueError, AttributeError):
        return None
    return value if isinstance(value, str) else None


def parse_line(line: str) -> Event | None:
    """Một dòng stdout (không kèm `\\n`) → sự kiện, hoặc None khi dòng không đúng hợp đồng."""
    for kind, rule in _RULES:
        m = rule.fullmatch(line)
        if not m:
            continue
        g = m.groups()
        if kind == "hello":
            return Event(kind, version=int(g[0]))
        if kind == "connected":
            return Event(kind, peer=g[0])
        if kind == "control":
            return Event(kind, on=g[0] == "on")
        if kind == "file-done":
            return Event(kind, file_id=g[0])
        text = _json_text(g[-1])
        if text is None:
            return None
        if kind in ("id", "request"):
            return Event(kind, peer=g[0], text=text)
        if kind == "file":
            return Event(kind, file_id=g[0], size=int(g[1]), text=text)
        if kind == "file-fail":
            return Event(kind, file_id=g[0], text=text)
        return Event(kind, text=text)
    return None


def clean_env(parent: dict[str, str], display_name: str = "") -> dict[str, str]:
    """Env cho engine: chỉ biến trong danh sách cho phép; `LINUXVIEWER_*` của env cha luôn bị loại."""
    env = {k: v for k, v in parent.items() if k in _ENV_EXACT or k.startswith(_ENV_PREFIX)}
    name = one_line(display_name)
    if name:
        env["LINUXVIEWER_NAME"] = name
    return env


def one_line(text: str) -> str:
    """Bỏ ký tự điều khiển để một giá trị không mở được dòng lệnh mới trên stdin của engine."""
    return " ".join("".join(c if c.isprintable() else " " for c in text).split())


def normalize_id(text: str) -> str | None:
    digits = "".join(text.split())
    return digits if re.fullmatch(_DIGITS, digits) else None


def host_argv(engine: str, download_dir: str, clipboard: bool) -> list[str]:
    argv = [engine, "host", "--ipc", "--backend", "x11", "--download-dir", download_dir]
    return argv + ["--clipboard"] if clipboard else argv


def connect_argv(engine: str, partner_id: str, download_dir: str, clipboard: bool) -> list[str]:
    argv = [engine, "connect", partner_id, "--ipc", "--password-stdin", "--no-lan", "--download-dir", download_dir]
    return argv + ["--clipboard"] if clipboard else argv


class Engine:
    """Một tiến trình engine. `on_event` và `on_exit` được gọi ở luồng đọc; GUI tự chuyển về luồng chính."""

    def __init__(self, argv: list[str], env: dict[str, str], log_path: Path,
                 on_event: Callable[[Event], None], on_exit: Callable[[int], None],
                 first_line: str | None = None):
        self._log_path = log_path
        self._secrets: list[str] = [first_line] if first_line else []
        self._lock = threading.Lock()
        self._on_event, self._on_exit = on_event, on_exit
        log_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._log = open(os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600), "a",
                         encoding="utf-8", errors="replace")
        try:
            self.proc = subprocess.Popen(argv, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
                                         bufsize=1, close_fds=True)
        except OSError as e:
            self.log(f"không chạy được engine: {e}")
            self._log.close()
            raise
        if first_line is not None:
            self.send(first_line)
        self._stderr = threading.Thread(target=self._read_stderr, daemon=True)
        self._stderr.start()
        self._stdout = threading.Thread(target=self._read_stdout, daemon=True)
        self._stdout.start()

    def log(self, text: str) -> None:
        with self._lock:
            for secret in self._secrets:
                text = text.replace(secret, "***")
            self._log.write(text.rstrip("\n") + "\n")
            self._log.flush()

    def send(self, command: str) -> bool:
        """Ghi một lệnh một dòng; False khi stdin đã đóng."""
        if "\n" in command or "\r" in command:
            raise ValueError("lệnh engine phải nằm trên một dòng")
        try:
            self.proc.stdin.write(command + "\n")
            self.proc.stdin.flush()
            return True
        except (BrokenPipeError, ValueError, OSError):
            return False

    def close_stdin(self) -> None:
        """Đóng stdin: engine ở `--ipc` kết thúc phiên và thoát."""
        try:
            self.proc.stdin.close()
        except OSError:
            pass

    def running(self) -> bool:
        return self.proc.poll() is None

    def _read_stdout(self) -> None:
        for raw in self.proc.stdout:
            line = raw.rstrip("\n")
            event = parse_line(line)
            if event is None:
                self.log(f"bỏ qua dòng lạ: {line[:200]!r}" if not line.startswith("ID ") else "bỏ qua dòng ID hỏng")
                continue
            if event.kind == "id" and event.text:
                with self._lock:
                    self._secrets.append(event.text)
            self._on_event(event)
        code = self.proc.wait()
        self._stderr.join(timeout=2)
        self.log(f"engine thoát rc {code}")
        self._on_exit(code)

    def _read_stderr(self) -> None:
        for raw in self.proc.stderr:
            self.log(raw)
