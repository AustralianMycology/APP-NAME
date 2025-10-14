#!/usr/bin/env bash
set -e
PY=${PYTHON:-python}; command -v "$PY" >/dev/null 2>&1 || PY="py -3"
$PY -m pip install -U pip >/dev/null
$PY -m pip install -q pytest pyyaml openai
$PY -m pytest -q
