#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="$PROJECT_ROOT/src"
python -m llmctg demo --output "$PROJECT_ROOT/output/demo"
