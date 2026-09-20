#!/usr/bin/env bash
# 將本地記憶工作副本的可備份內容同步回本 repo，並提示提交。
# 不包含：憑證、完整對話、敏感任務內容、除錯日誌、下載的第三方套件快取。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MEMORY_DIR="${HOME}/.claude/skill-retriever-memory"

for f in state.json skill-index.json relationships.json; do
  if [ -f "$MEMORY_DIR/$f" ]; then
    cp "$MEMORY_DIR/$f" "$REPO_ROOT/memory/$f"
  fi
done

cd "$REPO_ROOT"
if git diff --quiet && git diff --cached --quiet; then
  echo "[backup] 無實質變更，不建立空提交"
  exit 0
fi

echo "[backup] 偵測到變更，請檢查後自行執行 git add / commit / push 到 v1.0 分支"
git status --short
