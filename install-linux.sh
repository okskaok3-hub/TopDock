#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
venv_dir="${project_dir}/.venv-linux"
applications_dir="${XDG_DATA_HOME:-${HOME}/.local/share}/applications"
icons_dir="${XDG_DATA_HOME:-${HOME}/.local/share}/icons/hicolor/scalable/apps"
bin_dir="${HOME}/.local/bin"
launcher_path="${bin_dir}/topdock-vdi"
desktop_path="${applications_dir}/topdock-vdi.desktop"

missing=()
for command_name in python3 wmctrl xprop xclip scrot; do
  command -v "${command_name}" >/dev/null 2>&1 || missing+=("${command_name}")
done

if ((${#missing[@]})); then
  echo "Missing system tools: ${missing[*]}" >&2
  echo "Ubuntu/Debian: sudo apt install python3 python3-venv python3-tk wmctrl x11-utils xclip scrot" >&2
  echo "Fedora: sudo dnf install python3 python3-tkinter wmctrl xprop xclip scrot" >&2
  exit 1
fi

python3 -m venv "${venv_dir}"
"${venv_dir}/bin/python" -m pip install --upgrade pip
"${venv_dir}/bin/python" -m pip install -r "${project_dir}/requirements-topdock-linux.txt"

mkdir -p "${applications_dir}" "${icons_dir}" "${bin_dir}"
cp "${project_dir}/assets/topdock-vdi.svg" "${icons_dir}/topdock-vdi.svg"

printf '%s\n' \
  '#!/usr/bin/env bash' \
  'set -euo pipefail' \
  "exec \"${venv_dir}/bin/python\" \"${project_dir}/linux_topdock.py\" \"\$@\"" \
  > "${launcher_path}"
chmod +x "${launcher_path}"

desktop_exec="\"${venv_dir}/bin/python\" \"${project_dir}/linux_topdock.py\""
cat > "${desktop_path}" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=TopDock VDI
Comment=Floating application switcher and VDI productivity tools
Exec=${desktop_exec}
Icon=topdock-vdi
Terminal=false
Categories=Utility;RemoteAccess;
StartupNotify=false
EOF
chmod +x "${desktop_path}"

echo "TopDock VDI installed."
echo "Launch it from your application menu or run: topdock-vdi"
echo "Inside TopDock, select START to enable login startup."
