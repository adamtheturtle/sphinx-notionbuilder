#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

set -a
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/.env"
set +a

rm -rf ./build-sample
uv run --extra=sample sphinx-build -W -b notion sample ./build-sample

uv run --all-extras notion-upload \
    --parent-database-id "$NOTION_SAMPLE_DATABASE_ID" \
    --file "./build-sample/index.json" \
    --title "Test page title during testing" \
    --icon "🐍"
