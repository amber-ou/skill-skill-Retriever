# Notion 資料庫欄位設計（Skill Retriever）

父頁面：https://app.notion.com/p/3e105064114a80b3b090f22503db8068
資料庫名稱：`Skill Retriever`
資料庫 URL／ID：見 `memory/state.json` 的 `notion.database_url`（建立後回填）

## 欄位

| 群組 | 欄位名稱 | 型別 | 說明 |
| --- | --- | --- | --- |
| 基本識別 | Name | title | Skill 原始名稱（保留原文） |
| 基本識別 | Skill ID | rich_text | 內部穩定 ID，12 位十六進位亂數字串（建立時隨機產生，非來源資料的雜湊值），建立後終身不變 |
| 基本識別 | Tags | multi_select | **用途分類**（2026-09-20 起依完整內容標記，非僅名稱/描述）：`UI 設計`／`UX 研究`／`設計系統`／`無障礙`／`設計稽核`／`前端實作`／`行動介面`／`原型與互動`（可擴充；同一 Skill 可多個標籤；不得混入推薦狀態或授權疑慮） |
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
| 門檻與封存（2026-09-20 新增） | Archived | checkbox | 是否已封存（低於收錄門檻且無使用者例外）；封存**不是刪除**，原有分析內容全數保留 |
| 門檻與封存 | Archive Reason | rich_text | 封存原因（含查核到的實際數值與查核時間） |
| 門檻與封存 | Archived At | date | 封存時間 |
| 門檻與封存 | User Specified Exception | checkbox | 使用者是否明確指定此筆為低於門檻的例外收錄；**只有使用者本人指定才能勾選，Agent 自行選入不算** |
| 門檻與封存 | Exception Reason | rich_text | 例外原因 |
| 門檻與封存 | Exception Source | rich_text | 例外的確認來源（例如使用者哪一次訊息指定） |

頁面內容（每筆記錄詳細內容，不放進表格欄位）：
- 評分理由與證據（對應四個面向，逐項列出 `docs/scoring-rules.md` 的 JSON 紀錄）
- 依賴、授權全文摘要
- 與其他 Skill 的關係（重複／重疊／互補／衝突／衍生）
- 版本歷史（每次分析的 commit + 時間）
- 套件資訊（檔案清單、外部依賴）

## 檢視（Views）

1. **全部** — `Archived = false`，依 Last Check Succeeded 降冪。
2. **可推薦** — `Archived = false` 且 `Recommendation Status = 可推薦`。
3. **待處理** — `Archived = false` 且（`Recommendation Status in (待評估, 需人工確認)` 或 `Last Error is not empty`）。
4. **依 TAG 分類**（2026-09-20 新增）— board 視圖，依 `Tags` 分組，`Archived = false`。
5. **已移出**（2026-09-20 新增）— `Archived = true`，依 Archived At 降冪；獨立檢視供追溯封存項目，**不出現在上述 1–4 的預設檢視中**。

不設分數為預設排序依據（避免把熱門度當唯一推薦指標）。所有預設瀏覽／推薦／TAG 分類檢視
一律排除 `Archived = true` 的項目；查詢指定舊 Skill ID 時仍可查到封存記錄，但需明確告知
已封存及原因，不得當成有效推薦回傳。

## 去重規則

- 以 Skill ID（穩定 ID）為準更新既有記錄，避免改名/搬移造成重複。
- 同一 Repository 可有多個 Skill（不同 Skill Path → 不同 Skill ID）。
- Fork 視為獨立來源，建立「衍生自」關係於頁面內容中記錄，不自動合併為重複記錄。
