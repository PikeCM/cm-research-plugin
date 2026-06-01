#!/usr/bin/env bash
# Idempotent setup for cm-research-plugin document/spreadsheet conversion.
# Creates a local Python venv with the conversion libraries. On-device.
set -euo pipefail

DATA_HOME="${CM_RESEARCH_HOME:-$HOME/.cloudmasonry/cm-research}"
VENV="$DATA_HOME/venv"
mkdir -p "$DATA_HOME"

echo "== locating a compatible Python (<= 3.12) =="
PY_BIN=""
ver_ok() { "$1" -c 'import sys; sys.exit(0 if (3,9) <= sys.version_info[:2] <= (3,12) else 1)' >/dev/null 2>&1; }
for cand in python3.12 python3.11 python3.10 python3 python; do
  if command -v "$cand" >/dev/null 2>&1 && ver_ok "$cand"; then PY_BIN="$(command -v "$cand")"; break; fi
done
# Reuse the requirements-pipeline venv's interpreter base if present, else winget
if [ -z "$PY_BIN" ] && [ -x "$LOCALAPPDATA/Programs/Python/Python312/python.exe" ]; then
  PY_BIN="$LOCALAPPDATA/Programs/Python/Python312/python.exe"
fi
if [ -z "$PY_BIN" ]; then
  echo "No compatible Python (3.9-3.12) found. Installing Python 3.12 via winget..."
  if command -v winget >/dev/null 2>&1; then
    winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements \
      || { echo "ERROR: could not install Python 3.12. Install it manually, then re-run." >&2; exit 1; }
    echo "Python 3.12 installed. Open a NEW shell and re-run this script so it is on PATH."
    exit 0
  else
    echo "ERROR: no compatible Python and no winget. Install Python 3.12 manually." >&2
    exit 1
  fi
fi
echo "Using Python: $PY_BIN ($($PY_BIN --version 2>&1))"

echo "== creating venv and installing conversion libraries =="
if [ ! -e "$VENV/Scripts/python.exe" ] && [ ! -e "$VENV/bin/python" ]; then
  "$PY_BIN" -m venv "$VENV"
fi
if [ -e "$VENV/Scripts/python.exe" ]; then VPY="$VENV/Scripts/python.exe"; else VPY="$VENV/bin/python"; fi
"$VPY" -m pip install --upgrade pip >/dev/null
# pandas+openpyxl: xlsx/csv; xlrd: legacy .xls; python-docx: Word; pypdf: PDF text; tabulate: markdown tables
"$VPY" -m pip install pandas openpyxl xlrd python-docx pypdf tabulate

echo
echo "Setup complete."
echo "  venv python : $VPY"
echo "  data home   : $DATA_HOME"
