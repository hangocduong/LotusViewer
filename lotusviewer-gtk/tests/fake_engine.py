"""Engine giả cho test: ghi argv, env và từng dòng stdin vào thư mục ghi; phát các dòng kịch bản ra stdout.

Dòng kịch bản `@stdin` nghĩa là chờ đọc một dòng stdin rồi mới phát tiếp.

Mỗi dòng stdin cũng được in ra stderr, để test kiểm log của giao diện không chứa mật khẩu.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys


def main(record_dir: str, script_path: str) -> int:
    rec = Path(record_dir)
    (rec / "argv.json").write_text(json.dumps(sys.argv[1:]), encoding="utf-8")
    (rec / "env.json").write_text(json.dumps(dict(os.environ)), encoding="utf-8")
    with open(rec / "stdin.log", "a", encoding="utf-8") as log:
        def record(line: str) -> None:
            log.write(line)
            log.flush()
            print(f"fake engine got: {line.rstrip()}", file=sys.stderr, flush=True)

        for line in Path(script_path).read_text(encoding="utf-8").splitlines():
            if line == "@stdin":
                got = sys.stdin.readline()
                if not got:
                    break
                record(got)
            else:
                print(line, flush=True)
        for line in sys.stdin:
            record(line)
    (rec / "eof").write_text("1", encoding="utf-8")
    print('ENDED "Disconnected."', flush=True)
    return 0


def install(directory: Path, script: list[str]) -> tuple[str, Path]:
    """Tạo tệp thực thi `engine` trong `directory`; trả về (đường engine, thư mục ghi)."""
    rec = directory / "rec"
    rec.mkdir()
    script_path = directory / "script.txt"
    script_path.write_text("\n".join(script) + "\n", encoding="utf-8")
    engine = directory / "engine"
    engine.write_text(
        f"#!{sys.executable}\n"
        "import sys\n"
        f"sys.path.insert(0, {str(Path(__file__).parent)!r})\n"
        "import fake_engine\n"
        f"sys.exit(fake_engine.main({str(rec)!r}, {str(script_path)!r}))\n",
        encoding="utf-8")
    engine.chmod(0o755)
    return str(engine), rec
