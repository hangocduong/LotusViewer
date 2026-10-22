#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C TZ=UTC
umask 022
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
out=${1:?Cần thư mục output}
version=${2:?Cần version gói}
: "${SOURCE_DATE_EPOCH:?Cần giờ commit đã ghim}"
mkdir -p "$out"
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
cd "$root/LinuxViewer"
cargo build --release --locked --offline --no-default-features
install -Dm755 target/release/linuxviewer "$stage/usr/lib/lotusviewer/lotusviewer-engine"
install -Dm644 "$root/LICENSE" "$stage/usr/share/doc/lotusviewer/copyright"
cat "$root/LOTUSVIEWER.md" >> "$stage/usr/share/doc/lotusviewer/copyright"
install -Dm644 "$root/THIRD_PARTY_NOTICES.md" "$stage/usr/share/doc/lotusviewer/THIRD_PARTY_NOTICES.md"
mkdir -p "$stage/DEBIAN"
cat > "$stage/DEBIAN/control" <<CONTROL
Package: lotusviewer
Version: $version
Architecture: amd64
Maintainer: LotusOS <hotro@lotusos.vn>
Section: net
Priority: optional
Description: Engine hỗ trợ từ xa LotusViewer
 Fork DeanOpen/MacViewer; không phải sản phẩm chính thức UltraViewer.
CONTROL
find "$stage" -exec touch -h -d "@$SOURCE_DATE_EPOCH" {} +
dpkg-deb --root-owner-group --uniform-compression -Zxz -z9 --build "$stage" "$out/lotusviewer_${version}_amd64.deb"
