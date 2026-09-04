#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-build.txt
.venv/bin/python -m PyInstaller --noconfirm --clean --onedir --name Lantern --add-data 'lantern/ui:lantern/ui' run.py
mkdir -p dist/linux-bundle
cp -R dist/Lantern dist/linux-bundle/
cp packaging/install-linux.sh dist/linux-bundle/Install-Lantern.sh
chmod +x dist/linux-bundle/Install-Lantern.sh
tar -C dist/linux-bundle -czf dist/Lantern-Linux-0.1.0.tar.gz .
if command -v dpkg-deb >/dev/null; then
  stage=$(mktemp -d)
  mkdir -p "$stage/opt/lantern" "$stage/usr/share/applications" "$stage/DEBIAN"
  cp -R dist/Lantern/. "$stage/opt/lantern/"
  printf 'Package: lantern-diagnostics\nVersion: 0.1.0\nArchitecture: %s\nMaintainer: Lantern local build\nDepends: libc6, libgcc-s1, zlib1g\nDescription: Local read-only diagnostics dashboard\n' "$(dpkg --print-architecture)" > "$stage/DEBIAN/control"
  printf '[Desktop Entry]\nType=Application\nName=Lantern Diagnostics\nExec=/opt/lantern/Lantern\nTerminal=true\nCategories=System;\n' > "$stage/usr/share/applications/lantern.desktop"
  dpkg-deb --root-owner-group --build "$stage" dist/Lantern-0.1.0.deb
fi
