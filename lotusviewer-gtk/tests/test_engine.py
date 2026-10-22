"""Adapter engine: parser dòng `--ipc`, env đã làm sạch, argv và stdin."""
from __future__ import annotations

import json

from conftest import pump, stdin_lines
from lotusviewer import engine
from lotusviewer.engine import Event, parse_line

INJECTED_CHAT = r'CHAT "a\nREQUEST 1 \"x\""'
HOST_READY = ["IPC 1", 'ID 123456789 PASSWORD "matkhau1"']


def test_parses_every_protocol_line():
    assert parse_line("IPC 1") == Event("hello", version=1)
    assert parse_line('ID 123 PASSWORD "p w"') == Event("id", peer="123", text="p w")
    assert parse_line('REQUEST 987 "Kỹ thuật viên"') == Event("request", peer="987", text="Kỹ thuật viên")
    assert parse_line("CONNECTED 987") == Event("connected", peer="987")
    assert parse_line("CONTROL on") == Event("control", on=True)
    assert parse_line("CONTROL off") == Event("control", on=False)
    assert parse_line(r'CHAT "xin chào\tbạn"') == Event("chat", text="xin chào\tbạn")
    assert parse_line('FILE a_B-1 2048 "báo cáo.pdf"') == Event("file", file_id="a_B-1", size=2048, text="báo cáo.pdf")
    assert parse_line("FILE-DONE a_B-1") == Event("file-done", file_id="a_B-1")
    assert parse_line('FILE-FAIL x "Canceled"') == Event("file-fail", file_id="x", text="Canceled")
    assert parse_line('STATUS "Connecting…"') == Event("status", text="Connecting…")
    assert parse_line('ENDED "Disconnected."') == Event("ended", text="Disconnected.")


def test_chat_with_escaped_request_stays_one_chat_event():
    event = parse_line(INJECTED_CHAT)
    assert event == Event("chat", text='a\nREQUEST 1 "x"')


def test_strange_or_broken_lines_are_ignored():
    for line in ["", "IPC", "REQUEST 12 x", 'REQUEST abc "x"', 'REQUEST 12 "x" extra', 'CHAT "unterminated',
                 'CHAT "a"b"', "CHAT 5", 'CHAT "\\x41"', 'CHAT "\\ud800"', "CONTROL maybe", "CONNECTED",
                 'FILE ../x 5 "a"', 'FILE id -1 "a"', "FILE-DONE a b", 'ENDED ["x"]', " IPC 1", "IPC 1 ",
                 'request 1 "x"', 'CHAT "a\x01"', 'y', 'ID 1 PASSWORD x']:
        assert parse_line(line) is None, line


def test_env_keeps_only_the_allowlist():
    parent = {"DISPLAY": ":1", "XAUTHORITY": "/x", "HOME": "/h", "PATH": "/bin", "LANG": "vi_VN.UTF-8",
              "LC_ALL": "C", "XDG_RUNTIME_DIR": "/run/user/1", "LINUXVIEWER_INSECURE_RELAY": "1",
              "LINUXVIEWER_NAME": "từ env cha", "LINUXVIEWER_NO_SHM": "1", "LD_PRELOAD": "/evil.so",
              "PYTHONPATH": "/p", "RUST_LOG": "trace"}
    env = engine.clean_env(parent, "Máy\nkế toán")
    assert env == {"DISPLAY": ":1", "XAUTHORITY": "/x", "HOME": "/h", "PATH": "/bin", "LANG": "vi_VN.UTF-8",
                   "LC_ALL": "C", "XDG_RUNTIME_DIR": "/run/user/1", "LINUXVIEWER_NAME": "Máy kế toán"}
    assert "LINUXVIEWER_NAME" not in engine.clean_env(parent, "")


def test_engine_env_drops_insecure_relay_even_when_the_parent_has_it(make_window):
    window, rec = make_window(HOST_READY, {"LINUXVIEWER_INSECURE_RELAY": "1", "LD_PRELOAD": "/x.so"})
    assert window.start_host()
    assert pump(lambda: (rec / "env.json").exists())
    env = json.loads((rec / "env.json").read_text())
    assert "LINUXVIEWER_INSECURE_RELAY" not in env
    assert not any(k.startswith("LINUXVIEWER_") for k in env)
    assert "LD_PRELOAD" not in env


def test_host_argv_has_no_auto_approve(make_window, home):
    window, rec = make_window(HOST_READY)
    assert window.start_host()
    assert pump(lambda: (rec / "argv.json").exists())
    argv = json.loads((rec / "argv.json").read_text())
    assert argv == ["host", "--ipc", "--backend", "x11", "--download-dir", str(home / "nhan")]
    assert not any(a.startswith("--auto") for a in argv)
    assert engine.host_argv("e", "/d", True)[-1] == "--clipboard"


def test_host_shows_id_and_password(make_window):
    window, _rec = make_window(HOST_READY)
    window.start_host()
    assert pump(lambda: window.host_password.get_text() == "matkhau1")
    assert window.host_id.get_text() == "123 456 789"


def test_connect_password_goes_to_stdin_not_argv(make_window, home):
    window, rec = make_window(["IPC 1"])
    window.connect_id.get_child().set_text("123 456 789")
    window.connect_password.set_text("bimat42")
    assert window.start_connect()
    assert pump(lambda: stdin_lines(rec))
    argv = json.loads((rec / "argv.json").read_text())
    assert argv == ["connect", "123456789", "--ipc", "--password-stdin", "--no-lan", "--download-dir",
                    str(home / "nhan")]
    assert not any("bimat42" in a for a in argv)
    assert stdin_lines(rec)[0] == "bimat42"
    assert window.connect_password.get_text() == ""


def test_password_is_not_written_to_the_log(make_window, home):
    window, rec = make_window(HOST_READY)
    window.connect_id.get_child().set_text("123")
    window.connect_password.set_text("bimat42")
    window.start_connect()
    assert pump(lambda: "fake engine got" in (home / ".cache/lotusviewer/engine.log").read_text()
                if (home / ".cache/lotusviewer/engine.log").exists() else False)
    window.engine.close_stdin()
    assert pump(lambda: window.engine is None)
    log = (home / ".cache/lotusviewer/engine.log").read_text()
    assert "bimat42" not in log and "matkhau1" not in log
    assert "***" in log


def test_connect_rejects_bad_id_and_empty_password(make_window):
    window, rec = make_window(["IPC 1"])
    window.connect_id.get_child().set_text("12a")
    window.connect_password.set_text("x")
    assert not window.start_connect()
    window.connect_id.get_child().set_text("123")
    window.connect_password.set_text("  ")
    assert not window.start_connect()
    assert window.engine is None and not (rec / "argv.json").exists()


def test_strange_lines_do_not_change_state(make_window):
    window, rec = make_window(HOST_READY + ["REQUEST 12 x", "NONSENSE", 'CONNECTED 1 "x"'])
    window.start_host()
    assert pump(lambda: window.host_password.get_text() == "matkhau1")
    pump(timeout=0.3)
    assert window.hop_duyet is None and not window.phien.connected
    assert window.stack.get_visible_child_name() == "tabs"


def test_closing_the_window_closes_engine_stdin(make_window):
    window, rec = make_window(HOST_READY)
    window.start_host()
    assert pump(lambda: window.host_password.get_text() == "matkhau1")
    window.close()
    assert pump(lambda: (rec / "eof").exists())


def test_closing_during_a_session_asks_first(make_window):
    answers = []

    def confirm(_parent):
        answers.append(1)
        return len(answers) > 1

    window, rec = make_window(HOST_READY + ["CONNECTED 987", "CONTROL off"], confirm=confirm)
    window.start_host()
    assert pump(lambda: window.phien is not None and window.phien.connected)
    window.close()
    pump(timeout=0.3)
    assert answers == [1] and not (rec / "eof").exists() and window.get_visible()
    window.close()
    assert pump(lambda: (rec / "eof").exists())
    assert answers == [1, 1]


def test_stop_sharing_closes_stdin(make_window):
    window, rec = make_window(HOST_READY)
    window.start_host()
    assert pump(lambda: window.host_password.get_text() == "matkhau1")
    window.host_button.clicked()
    assert pump(lambda: (rec / "eof").exists() and window.engine is None)
    assert window.host_button.get_label() == "Bắt đầu chia sẻ"


def test_missing_engine_shows_vietnamese_error(make_window, tmp_path):
    window, _rec = make_window(HOST_READY)
    window.engine_path = str(tmp_path / "khong-co")
    assert not window.start_host()
    assert window.host_status.get_text().startswith("Không chạy được LotusViewer.")
