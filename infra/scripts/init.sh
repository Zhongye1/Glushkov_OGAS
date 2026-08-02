#!/usr/bin/env bash
# monorepo 初始化：安装依赖 + 构建 + Go/Python 校验
set -euo pipefail

pnpm install
pnpm build

# Go
go work sync
(cd services/dispatcher && go build ./... && go vet ./...)

# Python（Arkhiv）
python3 -m pip install -e services/arkhiv 2>/dev/null || echo "arkhiv 依赖安装跳过（可改用 uv sync）"
