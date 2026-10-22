#!/usr/bin/env bash
# Dựng lotusviewer_<VERSION>_amd64.deb: engine Rust cộng giao diện GTK3, nội dung theo manifest.txt.
set -euo pipefail
export LC_ALL=C TZ=UTC PYTHONDONTWRITEBYTECODE=1
umask 022
die() { printf 'build-deb: %s\n' "$*" >&2; exit 1; }
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
gui_conf= out=
while (($#)); do
  case "$1" in
    --gui-conf) (($# >= 2)) || die 'thiếu --gui-conf'; gui_conf=$2; shift 2 ;;
    --out) (($# >= 2)) || die 'thiếu --out'; out=$2; shift 2 ;;
    *) die "tham số không hợp lệ: $1" ;;
  esac
done
[[ -n "$gui_conf" && -n "$out" ]] || die 'cần --gui-conf <tệp> --out <dir>'
[[ -f "$gui_conf" ]] || die "không thấy gui.conf: $gui_conf"
: "${SOURCE_DATE_EPOCH:?Cần giờ commit đã ghim}"
version=$(<"$root/packaging/VERSION")
[[ "$version" =~ ^[0-9][0-9A-Za-z.+~-]*$ ]] || die "packaging/VERSION không hợp lệ: $version"
mkdir -p "$out"
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
chmod 755 "$stage"
(cd "$root/LinuxViewer" && cargo build --release --locked --offline --no-default-features)
while read -r mode dest src; do
  [[ -z "$mode" || "$mode" == \#* ]] && continue
  [[ -n "$src" && "$dest" == /* ]] || die "dòng manifest hỏng: $mode $dest $src"
  case "$src" in
    @engine) src=$root/LinuxViewer/target/release/linuxviewer ;;
    @gui-conf) src=$gui_conf ;;
    @*) die "nguồn sinh lạ trong manifest: $src" ;;
    *) src=$root/$src ;;
  esac
  install -D -m "$mode" "$src" "$stage$dest"
done < "$root/packaging/manifest.txt"
mkdir -p "$stage/DEBIAN"
sed "s/@VERSION@/$version/" "$root/packaging/control.in" > "$stage/DEBIAN/control"
if [[ -n $(find "$stage" \( -name __pycache__ -o -name '*.pyc' \) -print -quit) ]]; then
  die 'stage có bytecode Python'
fi
find "$stage" -exec touch -h -d "@$SOURCE_DATE_EPOCH" {} +
dpkg-deb --root-owner-group --uniform-compression -Zxz -z9 --build "$stage" "$out/lotusviewer_${version}_amd64.deb"
