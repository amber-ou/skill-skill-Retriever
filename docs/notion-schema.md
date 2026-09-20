# Notion 資料庫欄位設計（Skill Retriever）

父頁面：https://app.notion.com/p/3e105064114a80b3b090f22503db8068
資料庫名稱：`Skill Retriever`
資料庫 URL／ID：見 `memory/state.json` 的 `notion.database_url`（建立後回填）

## 欄位

| 群組 | 欄位名稱 | 型別 | 說明 |
| --- | --- | --- | --- |
| 基本識別 | Name | title | Skill 原始名稱（保留原文） |
| 基本識別 | Skill ID | rich_text | 內部穩定 ID，格式 `sha1(repo_full_name + skill_path)[:12]` |
| 基本識別 | Tags | multi_select | 分類／標籤，如 UI/UX |
| 基本識別 | Summary | rich_text | 用途摘要 |
| 基本識別 | Repository | url | 來源 repo |
| 基本識別 | Skill Path | rich_text | repo 內路徑 |
| 版本 | Analyzed Commit | rich_text | 分析當下的 commit sha |
| 版本 | Source Updated At | date | 來源最後更新時間 |
| 版本 | Scoring Rule Version | rich_text | 對應 scoring-rules.md 版本 |
| 原始指標 | Stars | number | |
| 原始指標 | Forks | number | |
| 原始指標 | Metrics Captured At | date | |
| 評估 | Popularity Score | number | 缺值留空 |
| 評估 | Popularity Status | select | scored / unknown |
| 評估 | Utility Score | number | |
| 評估 | Utility Status | select | scored / unknown / scenario_undefined |
| 評估 | Trustworthiness Score | number | |
| 評估 | Trustworthiness Status | select | scored / unknown |
| 評估 | Feasibility Score | number | |
| 評估 | Feasibility Status | select | scored / unknown / scenario_undefined |
| 推薦與狀態 | Confidence | select | high / medium / low / unknown |
| 推薦與狀態 | Recommendation Status | select | 待評估 / 可推薦 / 需人工確認 / 已過期 / 不可用 |
| 維護 | First Discovered | date | |
| 維護 | Last Check Attempted | date | |
| 維護 | Last Check Succeeded | date | |
| 維護 | Update Summary | rich_text | 最近一次查核的摘要 |
| 維護 | Last Error | rich_text | 最近一次失敗原因（成功時清空） |
| 人工內容 | User Notes | rich_text | **自動流程禁止覆寫** |
| 人工內容 | Manual Feedback | rich_text | **自動流程禁止覆寫** |

頁面內容（每筆記錄詳細內容，不放進表格欄位）：
- 評分理由與證據（對應四個面向，逐項列出 `docs/scoring-rules.md` 的 JSON 紀錄）
- 依賴、授權全文摘要
- 與其他 Skill 的關係（重複／重疊／互補／衝突／衍生）
- 版本歷史（每次分析的 commit + 時間）
- 套件資訊（檔案清單、外部依賴）

## 檢視（Views）

1. **全部** — 無篩選，依 Last Check Succeeded 降冪。
2. **可推薦** — `Recommendation Status = 可推薦`。
3. **待處理** — `Recommendation Status in (待評估, 需人工確認)` 或 `Last Error is not empty`。

不設分數為預設排序依據（避免把熱門度當唯一推薦指標）。

## 去重規則

- 以 Skill ID（穩定 ID）為準更新既有記錄，避免改名/搬移造成重複。
- 同一 Repository 可有多個 Skill（不同 Skill Path → 不同 Skill ID）。
- Fork 視為獨立來源，建立「衍生自」關係於頁面內容中記錄，不自動合併為重複記錄。
