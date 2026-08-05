#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$root_dir"

build_python=true
if [[ "${1:-}" == "--no-python-build" ]]; then
  build_python=false
  shift
fi
if [[ $# -ne 0 ]]; then
  echo "Usage: $0 [--no-python-build]" >&2
  exit 2
fi

version="$(python -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')"
arch="${DEB_ARCH:-all}"
work_dir="${BUILD_DIR:-$root_dir/build/debian}"
package_root="$work_dir/plasma-dynamic-wallpaper_${version}_${arch}"
wheel="$root_dir/dist/plasma_dynamic_wallpaper-${version}-py3-none-any.whl"
output="$root_dir/dist/plasma-dynamic-wallpaper_${version}_${arch}.deb"

if [[ "$build_python" == true ]]; then
  rm -rf "$root_dir/build"
  rm -f "$root_dir/dist"/*.whl "$root_dir/dist"/*.tar.gz
  python -m build
fi

if [[ ! -f "$wheel" ]]; then
  echo "Expected wheel not found: $wheel" >&2
  echo "Run python -m build first or omit --no-python-build." >&2
  exit 1
fi

rm -rf "$package_root"
mkdir -p "$package_root/DEBIAN" "$package_root/usr"
python -m pip install \
  --no-deps \
  --no-compile \
  --root "$package_root" \
  --prefix /usr \
  "$wheel"

cat > "$package_root/DEBIAN/control" <<CONTROL
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
CONTROL

mkdir -p "$root_dir/dist"
rm -f "$output"
dpkg-deb --build --root-owner-group "$package_root" "$output"
printf '%s\n' "$output"
