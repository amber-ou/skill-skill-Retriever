#!/usr/bin/env bash
# 從本 repo（amber-ou/skill-skill-Retriever, v1.0）還原 Skill Retriever 到目前工作階段。
# 用途：跨專案使用 —— 讓任一 Claude Code 工作階段都能載入 skill-retriever 這個 subagent
# 與它的持久記憶，而不需要每個專案各自保存一份。
#
# 用法： bash scripts/bootstrap.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AGENTS_DIR="${HOME}/.claude/agents"
MEMORY_DIR="${HOME}/.claude/skill-retriever-memory"
CACHE_DIR="${HOME}/.claude/skill-retriever-cache"

mkdir -p "$AGENTS_DIR" "$MEMORY_DIR" "$CACHE_DIR"

cp "$REPO_ROOT/agent/skill-retriever.md" "$AGENTS_DIR/skill-retriever.md"

for f in state.json skill-index.json relationships.json; do
  if [ -f "$REPO_ROOT/memory/$f" ] && [ ! -f "$MEMORY_DIR/$f" ]; then
    cp "$REPO_ROOT/memory/$f" "$MEMORY_DIR/$f"
  elif [ -f "$REPO_ROOT/memory/$f" ]; then
    # 本地已存在則不覆寫（避免蓋掉尚未備份回去的新狀態）；由使用者/agent 自行判斷是否要覆蓋。
    echo "[bootstrap] $f 本地已存在，未覆寫（如需強制還原請手動刪除後重跑）" >&2
  fi
done

cp -n "$REPO_ROOT/docs/scoring-rules.md" "$MEMORY_DIR/scoring-rules.md" 2>/dev/null || true
cp -n "$REPO_ROOT/docs/notion-schema.md" "$MEMORY_DIR/notion-schema.md" 2>/dev/null || true

echo "[bootstrap] 已還原 skill-retriever agent 定義至 $AGENTS_DIR/skill-retriever.md"
echo "[bootstrap] 記憶工作副本位於 $MEMORY_DIR"
echo "[bootstrap] 下載快取目錄 $CACHE_DIR"
