# Skill Retriever — 持久記憶與 Agent 定義備份

本 repo 是個人 Agent **skill Retriever**（技術識別名 `skill-retriever`）的持久記憶與定義備份位置，
對應建置規格第 4 節。它不是可獨立執行的服務，而是「Agent 定義 + 可還原記憶」的
GitHub 備份庫，供任一 Claude Code 工作階段還原後使用。

## 目錄結構

- `agent/skill-retriever.md` — Claude Code subagent 定義（system prompt、工具權限）。
- `docs/scoring-rules.md` — 熱門度／實用度／可信度／可行度評分規則（含版本號）。
- `docs/interfaces.md` — 供其他 Agent 呼叫的 `find_skills` / `compare_skills` / `get_skill` /
  `refresh_skills` 介面規格。
- `docs/notion-schema.md` — Notion 資料庫欄位與檢視設計。
- `memory/state.json` — 已確認設定、Agent Office 觸發機制、掃描進度、同步狀態（已去敏感化）。
- `memory/skill-index.json` — 輕量 Skill 索引（id、來源、Notion 頁面對應、最後查核時間）。
- `memory/relationships.json` — 重複／重疊／衝突等關係紀錄。
- `scripts/bootstrap.sh` — 從本 repo 還原 agent 定義與記憶到目前工作階段。
- `scripts/backup.sh` — 將本地記憶工作副本同步回本 repo（供後續 commit/push）。

## 如何在新的 Claude Code 工作階段中恢復

```bash
git clone --depth 1 -b v1.0 https://github.com/amber-ou/skill-skill-Retriever /tmp/skill-skill-retriever
bash /tmp/skill-skill-retriever/scripts/bootstrap.sh
```

執行後：
- `~/.claude/agents/skill-retriever.md` 會出現，可用 Agent 工具以
  `subagent_type: skill-retriever` 呼叫。
- `~/.claude/skill-retriever-memory/` 會有 `state.json`／`skill-index.json`／
  `relationships.json` 的工作副本。
- `~/.claude/skill-retriever-cache/` 為按需下載 Skill 套件的專用快取（初始為空）。

## 完整目錄與最新分析

以 Notion 為主要人類可讀目錄，資料庫連結見 `memory/state.json` 的 `notion_database_url`
（建置完成後回填）；本 repo 只保存可還原記憶摘要，不重複保存完整分析內容。

## 安全界線

不備份憑證、完整對話、敏感任務內容、除錯日誌、第三方套件快取。來源 URL 不含存取權杖。
