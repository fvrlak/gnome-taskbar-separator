#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./install.sh [--uninstall]

Installs or removes the taskbar-separator CLI entrypoint from ~/.local/bin.

Options:
  --uninstall   Remove ~/.local/bin/taskbar-separator symlink
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
TARGET="${BIN_DIR}/taskbar-separator"
SOURCE="${SCRIPT_DIR}/taskbar-separator.py"

install() {
  mkdir -p "${BIN_DIR}"
  chmod +x "${SOURCE}"
  ln -sf "${SOURCE}" "${TARGET}"
  echo "Installed ${TARGET} -> ${SOURCE}"
  echo "If this path is not in PATH, run: export PATH=\"\$HOME/.local/bin:\$PATH\""
}

uninstall() {
  if [[ -L "${TARGET}" ]]; then
    rm -f "${TARGET}"
    echo "Removed ${TARGET}"
  else
    echo "No symlink found at ${TARGET}"
  fi
}

case "${1:-}" in
  --uninstall)
    uninstall
    ;;
  "" )
    install
    ;;
  -h|--help)
    usage
    ;;
  *)
    usage >&2
    exit 1
    ;;
esac
