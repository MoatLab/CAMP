#!/usr/bin/env bash

# set -e is intentionally omitted: sourcing a script with set -e would make
# any error exit the caller's shell (e.g. the tmux pane).
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Install uv if not already present
if ! command -v uv &>/dev/null; then
  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

# Create venv inside the project directory (idempotent)
uv venv "$SCRIPT_DIR/.venv"

# Install required packages
uv pip install --python "$SCRIPT_DIR/.venv" matplotlib numpy pandas

echo "Done. Activate with: source .venv/bin/activate"
