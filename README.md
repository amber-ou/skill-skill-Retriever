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

## 目前狀態（2026-09-20，第四輪：TAG 分類 + 1,000 星收錄門檻）

- **收錄規則變更**：改用 GitHub 實際 stars ≥ 1,000 的收錄門檻（取代先前「不設門檻」），
  詳見 `memory/state.json` 的 `confirmed_settings.star_threshold`。首批 20 個 Skill
  （皆為 Agent 首批自行選入、非使用者例外）重新查核後 stars 介於 0～886，全數低於門檻，
  已用「封存」（`Archived: true`，可恢復、非刪除）機制移出有效清單，原有完整四項評估
  內容全數保留在 Notion 頁面與 `memory/skill-index.json` 中。
- 廣泛搜尋（20+ 組關鍵字查詢）後找到 5 個符合新門檻的 Skill 並完成完整收錄：
  `design-doctrine`（plugin87/ux-ui-agent-skills, 1428★）、`scroll-craft`
  （nateherkai/scroll-craft, 2610★）、`baoyu-design`（JimLiu/baoyu-design, 4100★）、
  `design-taste-frontend`（Leonxlnx/taste-skill, 88755★）、`material-3`
  （hamen/material-3-skill, 1396★）。未達 20 個目標，已如實回報短缺與已排除的候選
  （見 `memory/state.json` 的 `scan_progress.star_threshold_batch_20260920`），未降低
  門檻或擴大類型湊數。
- Notion 資料庫新增：`Tags` 依完整內容重新標記為 8 類用途標籤（UI 設計／UX 研究／設計
  系統／無障礙／設計稽核／前端實作／行動介面／原型與互動）、「依 TAG 分類」與「已移出」
  兩個新檢視、`Archived`／`Archive Reason`／`Archived At`／`User Specified Exception`／
  `Exception Reason`／`Exception Source` 六個新欄位，詳見 `docs/notion-schema.md`。
- 已完成（歷史累積）：四輪完整內容分析（20 個舊項目 + 5 個新項目皆為 `git clone` 完整讀取，
  非僅 frontmatter）、`scoring-rules@1.1.0`（含授權一致性強制規則）、`refresh_skills`
  真實可執行實作（`scripts/refresh_skills.py`，含合併判斷）、關係分析共 16 組、
  bootstrap／backup 腳本端對端驗證。
- 「開啟 Agent Office 時自動觸發維護」尚未整合：`amber-ou/agent-office` 是有自己執行模型
  （Task → 指派 Agent → Run → Review）的控制平面應用程式，其 ADR 明確排除自動派工／
  背景常駐 Agent，目前沒有可掛載的「開啟」事件；已與使用者確認暫不建置替代方案，
  維護入口目前僅有「使用者直接呼叫」與「其他 Agent 呼叫 `refresh_skills`」兩種。

## 安全界線

不備份憑證、完整對話、敏感任務內容、除錯日誌、第三方套件快取。來源 URL 不含存取權杖。
