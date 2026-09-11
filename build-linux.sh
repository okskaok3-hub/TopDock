#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
build_venv="${project_dir}/.venv-linux-build"

python3 -m venv "${build_venv}"
"${build_venv}/bin/python" -m pip install --upgrade pip
"${build_venv}/bin/python" -m pip install -r "${project_dir}/requirements-topdock-linux.txt" pyinstaller

cd "${project_dir}"
"${build_venv}/bin/pyinstaller" \
  --noconfirm \
  --clean \
  --onefile \
  --windowed \
  --name TopDock-VDI \
  --distpath dist-linux \
  --workpath build-linux \
  --specpath build-linux \
  --hidden-import pynput.keyboard._xorg \
  --hidden-import pynput.mouse._xorg \
  --exclude-module PyQt5 \
  --exclude-module numpy \
  --exclude-module cv2 \
  linux_topdock.py

echo "Linux executable created at: ${project_dir}/dist-linux/TopDock-VDI"
