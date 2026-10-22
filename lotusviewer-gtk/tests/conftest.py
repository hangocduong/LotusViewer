"""Chỗ chung của bộ test: đường nạp gói, bơm vòng lặp GTK, dựng cửa sổ với engine giả."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import fake_engine  # noqa: E402


def pump(until=lambda: False, timeout: float = 5.0) -> bool:
    from gi.repository import Gtk
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        if until():
            return True
        time.sleep(0.01)
    return until()


def stdin_lines(rec: Path) -> list[str]:
    path = rec / "stdin.log"
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


class FakeTimer:
    """Đồng hồ giả: test tự gọi `tick()` thay cho từng giây trôi qua."""

    def __init__(self):
        self.callbacks = []
        self.cancelled = 0

    def __call__(self, seconds, callback):
        assert seconds == 1
        entry = [callback, True]
        self.callbacks.append(entry)

        def cancel():
            entry[1] = False
            self.cancelled += 1
        return cancel

    def tick(self, times: int = 1) -> None:
        for _ in range(times):
            for entry in list(self.callbacks):
                if entry[1] and not entry[0]():
                    entry[1] = False


@pytest.fixture
def home(tmp_path):
    home = tmp_path / "home"
    (home / "nhan").mkdir(parents=True)
    cfg = home / ".config" / "lotusviewer"
    cfg.mkdir(parents=True)
    (cfg / "gui.json").write_text(json.dumps({"thu_muc_nhan": str(home / "nhan")}), encoding="utf-8")
    return home


@pytest.fixture
def make_window(tmp_path, home):
    from lotusviewer.window import MainWindow
    windows = []

    def make(script: list[str], extra_env: dict[str, str] | None = None, **kwargs):
        engine, rec = fake_engine.install(tmp_path, script)
        env = {"DISPLAY": os.environ.get("DISPLAY", ""), "HOME": str(home), "PATH": os.environ["PATH"],
               "LANG": "C.UTF-8", "XDG_SESSION_TYPE": "x11"}
        env.update(extra_env or {})
        window = MainWindow(env=env, engine_path=engine, timer=kwargs.pop("timer", FakeTimer()), **kwargs)
        windows.append(window)
        return window, rec

    yield make
    for window in windows:
        if window.engine is not None:
            window.engine.close_stdin()
            window.engine.proc.wait(timeout=5)
        window.destroy()


@pytest.fixture(autouse=True)
def destroy_leftover_windows():
    """Hộp modal còn sót từ một test hỏng chặn sự kiện đóng cửa sổ của test sau; dọn hết sau mỗi test."""
    yield
    from gi.repository import Gtk
    for window in Gtk.Window.list_toplevels():
        window.destroy()
    pump(timeout=0.05)
