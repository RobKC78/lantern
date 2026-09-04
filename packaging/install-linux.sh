#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
target="${XDG_DATA_HOME:-$HOME/.local/share}/lantern"
mkdir -p "$target" "${XDG_DATA_HOME:-$HOME/.local/share}/applications"
cp -R Lantern/. "$target/"
chmod +x "$target/Lantern"
escaped=${target//\\/\\\\}
escaped=${escaped//\"/\\\"}
escaped=${escaped//\$/\\$}
escaped=${escaped//\x60/\\\x60}
printf '[Desktop Entry]\nType=Application\nName=Lantern Diagnostics\nExec="%s/Lantern"\nTerminal=true\nCategories=System;\n' "$escaped" > "${XDG_DATA_HOME:-$HOME/.local/share}/applications/lantern.desktop"
printf 'Installed Lantern. Open Lantern Diagnostics from your application menu.\n'
