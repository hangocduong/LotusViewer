"""Hộp duyệt kết nối và hộp nhận tệp: mặc định từ chối, chỉ thao tác người dùng mới gửi lệnh."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

from conftest import FakeTimer, pump, stdin_lines  # noqa: E402
from lotusviewer import duyet  # noqa: E402

HOST_READY = ["IPC 1", 'ID 123456789 PASSWORD "matkhau1"']
REQUEST = 'REQUEST 987654321 "Kỹ thuật viên Hải Anh"'


def make_dialog(timer=None):
    sent = []
    dialog = duyet.HopDuyet(None, "nội dung", sent.append, timer=timer or FakeTimer())
    return dialog, sent


def test_timeout_after_sixty_seconds_refuses():
    timer = FakeTimer()
    dialog, sent = make_dialog(timer)
    timer.tick(duyet.TIMEOUT_SECONDS - 1)
    assert sent == [] and dialog.countdown.get_text() == "Tự từ chối sau 1 giây."
    timer.tick()
    assert sent == ["n"]
    timer.tick(5)
    assert sent == ["n"]


def test_refuse_is_the_default_and_has_focus():
    dialog, sent = make_dialog()
    refuse = dialog.buttons[duyet.TU_CHOI]
    assert refuse.has_default() and refuse.is_focus()
    assert not dialog.buttons[duyet.DIEU_KHIEN].has_default()
    assert dialog.get_urgency_hint() and dialog.get_modal()
    assert dialog.activate_default()
    assert pump(lambda: sent == ["n"])


def test_closing_the_dialog_refuses():
    dialog, sent = make_dialog()
    dialog.response(Gtk.ResponseType.DELETE_EVENT)
    assert sent == ["n"]


def test_buttons_send_view_or_control():
    for choice, command in ((duyet.CHI_XEM, "v"), (duyet.DIEU_KHIEN, "y"), (duyet.TU_CHOI, "n")):
        dialog, sent = make_dialog()
        dialog.buttons[choice].clicked()
        assert sent == [command]


def test_dismiss_sends_nothing():
    timer = FakeTimer()
    dialog, sent = make_dialog(timer)
    dialog.dismiss()
    timer.tick(duyet.TIMEOUT_SECONDS)
    assert sent == [] and timer.cancelled == 1


def test_injected_chat_does_not_open_the_approval_dialog(make_window):
    window, rec = make_window(HOST_READY + [r'CHAT "a\nREQUEST 1 \"x\""', "CONNECTED 987654321",
                                            r'CHAT "a\nREQUEST 1 \"x\""'])
    window.start_host()
    assert pump(lambda: window.phien is not None and window.phien.connected)
    pump(timeout=0.3)
    assert window.hop_duyet is None
    buf = window.panel.chat_view.get_buffer()
    assert buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False) == 'Máy kia: a\nREQUEST 1 "x"\n'
    assert stdin_lines(rec) == []


def test_request_times_out_to_refuse_on_the_engine(make_window):
    timer = FakeTimer()
    window, rec = make_window(HOST_READY + [REQUEST], timer=timer)
    window.start_host()
    assert pump(lambda: window.hop_duyet is not None)
    assert window.hop_duyet.message.get_text() == (
        "Kỹ thuật viên Hải Anh (ID do máy kia tự khai: 987 654 321) muốn kết nối vào máy này.")
    assert stdin_lines(rec) == []
    timer.tick(duyet.TIMEOUT_SECONDS)
    assert pump(lambda: stdin_lines(rec) == ["n"])


def test_view_only_approval_reaches_the_engine(make_window):
    window, rec = make_window(HOST_READY + [REQUEST])
    window.start_host()
    assert pump(lambda: window.hop_duyet is not None)
    window.hop_duyet.buttons[duyet.CHI_XEM].clicked()
    assert pump(lambda: stdin_lines(rec) == ["v"])


def test_engine_ending_the_request_closes_the_dialog(make_window):
    timer = FakeTimer()
    window, rec = make_window(HOST_READY + [REQUEST, 'ENDED "The incoming connection timed out. Ask Windows to connect again."'],
                              timer=timer)
    window.start_host()
    assert pump(lambda: window.phien is not None and window.phien.ended)
    assert window.hop_duyet is None
    timer.tick(duyet.TIMEOUT_SECONDS)
    pump(timeout=0.2)
    assert stdin_lines(rec) == []
    assert window.host_status.get_text() == "Kết nối hết thời gian chờ. Hãy nhờ máy kia kết nối lại."


def test_session_panel_shows_who_is_helping_and_toggles_control(make_window):
    window, rec = make_window(HOST_READY + [REQUEST, "@stdin", "CONNECTED 987654321", "CONTROL off",
                                            "@stdin", "CONTROL on"])
    window.start_host()
    assert pump(lambda: window.hop_duyet is not None)
    window.hop_duyet.buttons[duyet.CHI_XEM].clicked()
    assert pump(lambda: window.stack.get_visible_child_name() == "session")
    assert window.panel.headline.get_text() == "Đang được hỗ trợ bởi Kỹ thuật viên Hải Anh"
    assert not window.panel.control.get_active()
    window.panel.control.set_active(True)
    assert pump(lambda: stdin_lines(rec) == ["v", "c"])
    assert pump(lambda: window.panel.control.get_state())


def test_chat_is_sent_on_one_line(make_window):
    window, rec = make_window(HOST_READY + ["CONNECTED 987654321"])
    window.start_host()
    assert pump(lambda: window.stack.get_visible_child_name() == "session")
    window.panel.entry.get_buffer().set_text("dòng một\ny\ndòng ba")
    window.panel.send_button.clicked()
    assert pump(lambda: stdin_lines(rec) == ["t dòng một y dòng ba"])
    window.panel.end_button.clicked()
    assert pump(lambda: stdin_lines(rec)[-1:] == ["x"])


def test_incoming_files_on_connect_wait_for_the_user(make_window, home):
    window, rec = make_window(["IPC 1", 'STATUS "Connecting…"', "CONNECTED 123456789", "CONTROL on",
                               'FILE nhan1 2048 "báo cáo.pdf"', 'FILE tuchoi 10 "b.txt"', 'FILE dong 5 "c.txt"'])
    window.connect_id.get_child().set_text("123456789")
    window.connect_password.set_text("bimat42")
    window.start_connect()
    assert pump(lambda: len(window.hop_tep) == 3)
    dialogs = dict(window.hop_tep)
    assert window.panel.headline.get_text() == "Đang điều khiển 123 456 789"
    pump(timeout=0.2)
    assert stdin_lines(rec) == ["bimat42"]
    dialogs["nhan1"].response(Gtk.ResponseType.ACCEPT)
    dialogs["tuchoi"].response(Gtk.ResponseType.REJECT)
    dialogs["dong"].response(Gtk.ResponseType.DELETE_EVENT)
    assert pump(lambda: stdin_lines(rec) == ["bimat42", "a nhan1", "r tuchoi", "r dong"])
    assert window.hop_tep == {}
    assert window.cai_dat.gan_day == ["123456789"]


def test_wayland_session_locks_hosting(make_window):
    window, rec = make_window(HOST_READY, {"XDG_SESSION_TYPE": "wayland"})
    assert not window.host_button.get_sensitive()
    assert window.host_status.get_text() == "Chỉ hỗ trợ phiên X11"
    assert not window.start_host()
    assert window.connect_button.get_sensitive()
