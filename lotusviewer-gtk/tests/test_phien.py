"""Hộp nhận tệp nổi trên cửa sổ phiên độc lập, vẫn chờ người dùng duyệt."""
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from lotusviewer.phien import HopNhanTep
from conftest import pump


def test_file_offer_requests_above_and_present_without_accepting(monkeypatch):
    calls = []
    show_all, present, keep_above = Gtk.Widget.show_all, Gtk.Window.present, Gtk.Window.set_keep_above

    def show(window):
        calls.append("show")
        show_all(window)

    def above(window, on):
        calls.append(("above", on))
        keep_above(window, on)

    def raise_window(window):
        assert window.get_visible()
        calls.append("present")
        present(window)

    monkeypatch.setattr(HopNhanTep, "show_all", show)
    monkeypatch.setattr(HopNhanTep, "set_keep_above", above)
    monkeypatch.setattr(HopNhanTep, "present", raise_window)
    sent = []
    dialog = HopNhanTep(None, "offer", "report.pdf", 2048, sent.append)
    assert ("above", True) in calls
    assert calls.index("show") < calls.index("present")
    pump(timeout=0.1)
    assert sent == []
    dialog.response(Gtk.ResponseType.REJECT)
    assert sent == ["r offer"]
