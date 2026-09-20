# 呼叫介面（供其他 Agent 使用）

實際呼叫方式：其他 Agent／CC 工作階段透過 Claude Code 的 Agent（Task）工具，以
`subagent_type: skill-retriever` 呼叫，並在 prompt 中以下列結構化格式描述請求。
Skill Retriever 本身不是獨立執行的 HTTP/CLI 服務，它是一個依附於呼叫者工作階段、
擁有 Notion／GitHub 工具存取權的 Claude Code Agent；純腳本無法直接呼叫 Notion，
因此四項操作皆由「以 skill-retriever 身分執行的一次 Agent 呼叫」完成，回傳結構化文字
（JSON code block）。已於 2026-09-20 用獨立的第二個 Agent 呼叫實測 `get_skill` 成功
（見 `docs/validation-log.md`）；本環境的 Agent 工具現在能動態辨識 `subagent_type:
skill-retriever`，先前版本文件中「此環境不支援動態 subagent_type」的說明已不成立，
但不同 Claude Code 執行環境的支援程度可能不同，實際呼叫前建議先確認。

## 完整內容取得方法（get_skill／深度分析共用）

`mcp__github__get_file_contents` 等 GitHub MCP 內容工具在部分工作階段只能存取已明確
`add_repo` 的 repo，對其餘公開 repo 會拒絕存取——**這是該工具本身的授權範圍設計，
不是使用者未授權讀取公開 GitHub**。解法是改用 `git clone --depth 1 <公開 repo 的
HTTPS URL>` 取得內容：這條路徑走一般 HTTPS 智慧協定，不受該工具的 Repository Scope
限制，完全落在「搜尋及讀取核准來源」的既有授權內，不需要新增任何權限。因此：

- `mcp__github__search_code` / `search_repositories`：用於搜尋候選、取得 stars／forks／
  `pushed_at` 等只有 API 才有的統計指標。
- `git clone --depth 1`：用於取得完整檔案內容（`get_skill`、完整四項評估、套件交付）。
  取得後只在專用快取或暫存目錄操作，不執行任何腳本、不安裝依賴。

**已知資料品質提醒**：`search_code` 回傳的 `sha` 是檔案 blob sha，不是 commit sha；
repo 的 `updated_at` 只要 metadata 異動就會更新，`pushed_at` 才是真正的程式碼推送
時間。記錄「Analyzed Commit」與「Source Updated At」時一律要用 `git rev-parse HEAD`
與 API 的 `pushed_at`，不要用 code-search 的 `sha` 或 `updated_at`。

共同回傳欄位：

```json
{
  "status": "ok|partial|needs_input|error",
  "skill_id": "...",
  "source": "...",
  "analysis_version": "...",
  "last_success_check": "ISO8601|null",
  "confidence": "high|medium|low|unknown",
  "pending": ["..."]
}
```

## find_skills

輸入：`{ "task": "...", "environment": "...", "constraints": [...], "enabled_skills": [...], "max_results": 5 }`

輸出：排序後的推薦清單，每項含：`skill_id`、選擇理由、使用前提、限制、必要使用順序、
替代方案、資料新鮮度（`last_success_check` 距今天數）。無合適項目時 `status: "ok"` 但清單為空，
並說明原因；關鍵資訊不足時 `status: "needs_input"` 並列出 `pending` 問題，交由主流程詢問使用者。

## compare_skills

輸入：`{ "skill_ids": ["a","b",...], "context": "..." }`（至少 2 個）

輸出：兩兩關係（重複／部分重疊／互補／衝突／無明顯關聯／待確認），含證據、信心程度、
查核時間，以及在給定情境下建議的組合方式。

## get_skill

輸入：`{ "skill_id": "...", "version": "latest|<commit>", "with_package": true|false }`

輸出：分析資料（見 Notion 欄位）。`with_package: true` 時另外：
1. 下載至專用快取 `~/.claude/skill-retriever-cache/<skill_id>/<version>/`（相對路徑保留原始目錄結構）。
2. 回傳快取路徑、檔案清單、完整性狀態（`complete|incomplete`，不完整時列出缺少的檔案）。
3. 另列需要另外安裝的執行環境／外部依賴，不得誤稱為已安裝。
4. 只寫入快取目錄，不執行腳本、不安裝依賴、不寫入其他專案目錄。

套件與分析必須對應同一版本；若版本已變更，先重新分析再回傳。

## refresh_skills

輸入：`{ "scope": "all|<tag>|[skill_ids]", "mode": "check_only|apply_updates" }`

輸出：新增、更新、失效、待確認、錯誤的摘要清單。`check_only` 僅比對來源狀態不寫入 Notion；
`apply_updates` 才實際更新記錄。相同範圍重複觸發且仍在執行中時合併請求，不重複執行。

## 錯誤與重試

暫時性錯誤（斷線、限流）最多自動重試 3 次，並遵守服務回傳的等待時間（如 `Retry-After`）；
仍失敗才回報，並保留舊有效資料、標示「查核失敗」與原因，不得偽裝成功或寫成零值。
已於 2026-09-20 用隔離沙盒模擬驗證：重試上限、舊資料保留、`last_error` 記錄皆如預期
（見 `docs/validation-log.md`）。

## 人工欄位保護

任何自動更新 Notion 屬性前，一律先呼叫 `scripts/guard_protected_fields.py` 的
`assert_no_protected_fields(properties)`，觸碰到「User Notes」「Manual Feedback」
會直接丟出例外中止該次更新。已用三組 payload（正常／夾帶 User Notes／夾帶 Manual
Feedback）驗證通過。
