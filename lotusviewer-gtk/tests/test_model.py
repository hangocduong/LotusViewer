"""Trạng thái phiên, chuỗi tiếng Việt, màu nhấn từ gui.conf và tệp cài đặt."""
from __future__ import annotations

import json
import os
import stat

from lotusviewer import chuoi, model
from lotusviewer.cai_dat import CaiDat
from lotusviewer.engine import Event


def test_host_session_flow():
    p = model.Phien("host")
    assert p.apply(Event("hello", version=1)) is None
    assert p.apply(Event("id", peer="123456789", text="pw")) == "id"
    assert p.apply(Event("chat", text="trước phiên")) is None
    assert p.apply(Event("request", peer="987", text="KTV")) == "request"
    assert p.apply(Event("connected", peer="987")) == "connected"
    assert p.request is None and p.headline() == "Đang được hỗ trợ bởi KTV"
    assert p.apply(Event("request", peer="1", text="x")) is None
    assert p.apply(Event("control", on=True)) == "control" and p.control
    assert p.apply(Event("file", file_id="f", size=3, text="a.txt")) == "file"
    assert p.file_name("f") == "a.txt"
    assert p.apply(Event("ended", text="The Windows computer disconnected.")) == "ended"
    assert not p.connected and not p.control and p.files == {}
    assert p.ended == "Máy kia đã ngắt kết nối." and p.headline() == ""


def test_request_ended_by_engine_is_reported():
    p = model.Phien("host")
    p.apply(Event("request", peer="9", text=""))
    assert p.apply(Event("ended", text="The incoming request was declined.")) == "ended-request"
    assert p.ended == "Đã từ chối kết nối."


def test_connect_ignores_requests_and_names_the_partner():
    p = model.Phien("connect")
    assert p.apply(Event("request", peer="9", text="x")) is None
    p.apply(Event("connected", peer="123456789"))
    assert p.headline() == "Đang điều khiển 123 456 789"


def test_other_protocol_versions_are_refused():
    assert model.Phien("host").apply(Event("hello", version=2)) == "mismatch"


def test_engine_english_never_reaches_the_user():
    p = model.Phien("connect")
    p.apply(Event("status", text="Finding the partner computer…"))
    assert p.status == "Đang tìm máy kia…"
    p.apply(Event("status", text="Something new from upstream"))
    assert p.status == "Đang tìm máy kia…"
    p.apply(Event("ended", text="panic: something odd"))
    assert p.ended == chuoi.KET_THUC_MAC_DINH
    assert chuoi.ly_do("UltraViewer rejected the partner password.") == "Sai mật khẩu."
    assert chuoi.ly_do("Connected directly over the local network.") == "Đã kết nối."


def test_request_text_and_id_grouping():
    assert model.request_text(Event("request", peer="1234567890", text="  ")) == (
        "Một máy không rõ tên (ID do máy kia tự khai: 1 234 567 890) muốn kết nối vào máy này.")
    assert model.group_id("123") == "123" and model.group_id("12") == "12" and model.group_id("") == ""


def test_file_size_in_vietnamese():
    assert chuoi.co_tep(512) == "512 B"
    assert chuoi.co_tep(2048) == "2,0 KB"
    assert chuoi.co_tep(5 * 1024 * 1024 + 1) == "5,0 MB"


def test_accent_comes_only_from_gui_conf(tmp_path):
    assert model.read_accent(tmp_path) is None
    conf = tmp_path / "usr/share/lotusviewer/gui.conf"
    conf.parent.mkdir(parents=True)
    conf.write_text("# sinh lúc đóng gói\nACCENT_HEX=#087f72\nACCENT_FG_HEX=#F6F8F3\n")
    assert model.read_accent(tmp_path) == ("#087F72", "#F6F8F3")
    conf.write_text("ACCENT_HEX=red\nACCENT_FG_HEX=#F6F8F3\n")
    assert model.read_accent(tmp_path) is None


def test_css_only_overrides_suggested_action_and_labels():
    from lotusviewer.window import css
    text = css(("#087F72", "#F6F8F3")).decode()
    selectors = [line.split("{")[0].strip() for line in text.splitlines() if "{" in line]
    assert selectors == [".lv-headline", ".lv-id", "button.suggested-action:not(:disabled)"]
    assert "#087F72" in text and "#" not in css(None).decode()


def test_wayland_detection():
    assert model.wayland_session({"XDG_SESSION_TYPE": "wayland"})
    assert not model.wayland_session({"XDG_SESSION_TYPE": "x11"})
    assert not model.wayland_session({})


def test_settings_round_trip_is_private(tmp_path):
    path = tmp_path / "cfg/lotusviewer/gui.json"
    s = CaiDat.load(path)
    assert s == CaiDat() and not s.clipboard
    s.ten_hien_thi = "Kế toán"
    s.remember("111")
    s.remember("222")
    s.remember("111")
    s.save(path)
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    assert stat.S_IMODE(os.stat(path.parent).st_mode) == 0o700
    loaded = CaiDat.load(path)
    assert loaded.gan_day == ["111", "222"] and loaded.ten_hien_thi == "Kế toán"
    assert "password" not in json.loads(path.read_text()) and "mat_khau" not in path.read_text()


def test_settings_ignore_bad_values(tmp_path):
    path = tmp_path / "gui.json"
    path.write_text(json.dumps({"ten_hien_thi": "a\nb", "clipboard": "yes", "gan_day": ["12", "x1", 5, "1 2"]}))
    s = CaiDat.load(path)
    assert s.ten_hien_thi == "a b" and s.clipboard is False and s.gan_day == ["12"]
    path.write_text("[1, 2]")
    assert CaiDat.load(path) == CaiDat()
    for _ in range(15):
        s.remember(str(_))
    assert len(s.gan_day) == 10
