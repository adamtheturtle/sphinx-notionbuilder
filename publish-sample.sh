#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

set -a
# The committed sample.env provides the Notion object IDs referenced by the
# sample documentation; the gitignored .env provides the integration token.
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/sample.env"
# shellcheck source=/dev/null
source "${SCRIPT_DIR}/.env"
set +a

rm -rf "${SCRIPT_DIR}/build-sample"
uv run --extra=sample sphinx-build -W -b notion "${SCRIPT_DIR}/sample" "${SCRIPT_DIR}/build-sample"

uv run --all-extras notion-upload \
    --parent-database-id "$NOTION_SAMPLE_DATABASE_ID" \
    --file "${SCRIPT_DIR}/build-sample/index.json" \
    --title "Test page title during testing" \
    --icon "🐍"

rm -rf "${SCRIPT_DIR}/build-sample_warnings"
uv run --extra=sample sphinx-build -W -b notion "${SCRIPT_DIR}/sample_warnings" "${SCRIPT_DIR}/build-sample_warnings"

uv run --all-extras notion-upload \
    --parent-database-id "$NOTION_SAMPLE_DATABASE_ID" \
    --file "${SCRIPT_DIR}/build-sample_warnings/index.json" \
    --title "Test suppressed warnings page title during testing" \
    --icon "🐍"
