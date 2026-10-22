"""Gtk.Application một phiên bản: mở lần hai chỉ đưa cửa sổ cũ lên trước."""
from __future__ import annotations

import sys

APP_ID = "vn.lotusos.LotusViewer"


def main() -> int:
    import gi
    try:
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk
    except (ValueError, ImportError):
        print("LotusViewer: thiếu GTK3 (gói gir1.2-gtk-3.0).", file=sys.stderr)
        return 1
    ready = Gtk.init_check()
    if not (ready[0] if isinstance(ready, tuple) else ready):
        print("LotusViewer: cần phiên đồ họa (không có DISPLAY).", file=sys.stderr)
        return 1
    from .window import MainWindow

    class LotusViewerApp(Gtk.Application):
        def __init__(self):
            super().__init__(application_id=APP_ID)

        def do_activate(self):
            window = self.props.active_window or MainWindow(self)
            window.present()

    return LotusViewerApp().run([sys.argv[0]])


if __name__ == "__main__":
    sys.exit(main())
