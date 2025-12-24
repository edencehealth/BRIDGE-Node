#!/bin/bash
set -e

# 1. Install uv if not found
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
fi

# 2. Run the app
# 'uv run' will automatically:
#  - Download the correct Python version (if missing)
#  - Create a virtual environment
#  - Install dependencies
#  - Run the registration code
echo "Launching BRIDGE Node Registration App..."
uv run --project registration-cli python -m registration_cli.main register