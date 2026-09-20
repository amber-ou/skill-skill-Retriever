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
- `~/.claude/agents/skill-retriever.md` 會出現。**注意**：在標準 Claude Code CLI 中，
  這個檔案可用 Agent／Task 工具以 `subagent_type: skill-retriever` 呼叫；但在部分雲端／
  遠端工作階段（例如本次建置所在的環境），Agent 工具的 `subagent_type` 清單是固定的，
  不會動態讀入使用者自訂的 `.claude/agents/*.md`。這種環境下，其他 Agent 目前的實際作法
  是：讀取本檔案作為操作指示直接執行（例如以 general-purpose Agent 載入本檔內容），
  而非透過 `subagent_type` 直接派工。
- `~/.claude/skill-retriever-memory/` 會有 `state.json`／`skill-index.json`／
  `relationships.json` 的工作副本。
- `~/.claude/skill-retriever-cache/` 為按需下載 Skill 套件的專用快取（初始為空）。

## 完整目錄與最新分析

Notion 資料庫（人類可讀目錄）：https://app.notion.com/p/2ff83cca1acb4e35830458bf33d63fe3
（`memory/state.json` 的 `notion_database_url` / `notion_data_source_url` 為同一份記錄）。
本 repo 只保存可還原記憶摘要，不重複保存完整分析內容。

## 目前狀態（2026-09-20）

- 已完成：Notion 資料庫與「全部／可推薦／待處理」三個檢視、UI/UX 首批 20 個 Skill 收錄
  （來源、commit、熱門度分數皆可追溯）、初步關係分析（重複／部分重疊／互補／無明顯關聯／
  待確認，共 9 組）、bootstrap／backup 腳本並已端對端驗證。
- 已知限制：本工作階段的 GitHub 內容讀取權限僅涵蓋明確 `add_repo` 的 repo，因此這批
  20 個 Skill 的實用度／可信度／可行度目前皆為 `unknown`（僅熱門度為真實評分），需要
  下一輪以 `get_skill` 下載完整套件後補齊，詳見 `memory/state.json` 的 `backlog`。
- 「開啟 Agent Office 時自動觸發維護」尚未整合：`amber-ou/agent-office` 是有自己執行模型
  （Task → 指派 Agent → Run → Review）的控制平面應用程式，其 ADR 明確排除自動派工／
  背景常駐 Agent，目前沒有可掛載的「開啟」事件；已與使用者確認暫不建置替代方案，
  維護入口目前僅有「使用者直接呼叫」與「其他 Agent 呼叫 `refresh_skills`」兩種。

## 安全界線

不備份憑證、完整對話、敏感任務內容、除錯日誌、第三方套件快取。來源 URL 不含存取權杖。
