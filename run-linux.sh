#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
venv_dir="${project_dir}/.venv-linux"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required. Install python3, python3-venv, and python3-tk." >&2
  exit 1
fi

if [[ ! -x "${venv_dir}/bin/python" ]]; then
  python3 -m venv "${venv_dir}"
  "${venv_dir}/bin/python" -m pip install --upgrade pip
  "${venv_dir}/bin/python" -m pip install -r "${project_dir}/requirements-topdock-linux.txt"
fi

if [[ "${XDG_SESSION_TYPE:-}" == "wayland" ]]; then
  echo "Warning: Wayland may restrict global hotkeys and full-screen overlays." >&2
  echo "Use an X11/Xorg desktop session for complete TopDock behavior." >&2
fi

exec "${venv_dir}/bin/python" "${project_dir}/linux_topdock.py" "$@"
