#!/usr/bin/env bash
# 各执行机安装 liskin（上游 CLI），并做版本检查
set -euo pipefail

REPO_URL="${LISKIN_REPO_URL:-https://github.com/Zhongye1/liskin_code_agent.git}"
TARGET_DIR="${LISKIN_INSTALL_DIR:-$HOME/.local/opt/liskin}"

git clone --depth 1 "$REPO_URL" "$TARGET_DIR"
cd "$TARGET_DIR"
pnpm install
pnpm build

if ! command -v liskin >/dev/null 2>&1; then
  echo "liskin 未在 PATH 中，请将 $TARGET_DIR/bin 加入 PATH" >&2
  exit 1
fi
liskin --version
