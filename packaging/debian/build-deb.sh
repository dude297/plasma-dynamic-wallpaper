#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root_dir"

version="$(python -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')"
arch="${DEB_ARCH:-all}"
work_dir="${BUILD_DIR:-$root_dir/build/debian}"
package_root="$work_dir/plasma-dynamic-wallpaper_${version}_${arch}"

rm -rf "$package_root"
mkdir -p "$package_root/DEBIAN" "$package_root/usr"
python -m build --wheel
python -m pip install --no-deps --no-compile --root "$package_root" --prefix /usr dist/*.whl

cat > "$package_root/DEBIAN/control" <<EOF
Package: plasma-dynamic-wallpaper
Version: $version
Section: utils
Priority: optional
Architecture: $arch
Maintainer: Plasma Dynamic Wallpaper contributors
Depends: python3 (>= 3.12), libimage-exiftool-perl, libheif-examples, qdbus-qt6
Description: Apple Dynamic Desktop HEIC support for KDE Plasma
 Decodes Apple's embedded h24 schedule, extracts frames, and keeps KDE Plasma
 synchronized across login, resume, and Plasma Shell restarts.
EOF

mkdir -p "$root_dir/dist"
dpkg-deb --build --root-owner-group "$package_root" \
  "$root_dir/dist/plasma-dynamic-wallpaper_${version}_${arch}.deb"
