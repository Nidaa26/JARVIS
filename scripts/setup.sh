#!/usr/bin/env bash

# Setup for macOS / Linux. Usage: ./scripts/setup.sh [--voice]

set -euo pipefail
cd "$(dirname "$0")/.."





PYTHON=${PYTHON:-python3}

if [ ! -d .venv ]; then
  echo "Creating virtual environment..."
  "$PYTHON" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

pip install --upgrade pip >/dev/null
pip install -r requirements.txt

if [ "${1:-}" = "--voice" ]; then
  echo "Installing voice extras..."
  if [ "$(uname)" = "Darwin" ]; then
    command -v brew >/dev/null && brew list portaudio >/dev/null 2>&1 || \
      echo "Note: PyAudio needs portaudio (brew install portaudio) if the install below fails."
  else
    echo "Note: on Debian/Ubuntu you may need: sudo apt-get install portaudio19-dev espeak"
  fi
  pip install -r requirements-voice.txt
fi

if [ ! -f .env ]; then
  cp .env.example .env
  echo ""
  echo ">>> Created .env — edit it and add your ANTHROPIC_API_KEY. <<<"
fi

echo ""
echo "Setup complete. Run the assistant with:  ./scripts/run.sh [--voice]"
