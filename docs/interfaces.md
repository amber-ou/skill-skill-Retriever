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

**封存項目排除（2026-09-20 起）**：`Archived: true` 的記錄（低於收錄門檻或其他移出條件，
且無使用者例外）預設不列入推薦清單。若使用者查詢的任務只有封存項目符合，需明確告知「該
Skill 已封存及原因」，不得靜默略過或當成一般無結果回報。

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

**父子 Skill 的必要資源**：若某 Skill 是索引／路由型（例如指向多個子 Skill 的入口），
即使子 Skill 未在 Notion 獨立建檔，`get_skill` 下載父 Skill 的完整套件時仍須包含
其運作所需的子目錄／子檔案，不得因為沒有獨立記錄而省略——「暫不獨立建檔」只影響
Notion 目錄的收錄範圍，不影響單一套件本身該有的完整性。實例見
`memory/skill-index.json` 的 `bb21949b19c2`（konopkja/ethux-design）條目。

## refresh_skills

輸入：`{ "scope": "all|<tag>|[skill_ids]", "mode": "check_only|apply_updates" }`

輸出：新增、更新、失效、待確認、錯誤的摘要清單。`check_only` 僅比對來源狀態不寫入 Notion；
`apply_updates` 才實際更新記錄。

**實際實作（已取代原本的純文字規則）**：`scripts/refresh_skills.py`。使用者直接呼叫維護、
其他 Agent 呼叫 `refresh_skills`、以及（未來整合後的）Agent Office 開啟觸發，三者共用
同一支腳本與同一把檔案鎖（`~/.claude/skill-retriever-memory/refresh.lock`），差異僅在
`--trigger-source` 參數不同，用於記錄觸發來源，不影響執行邏輯。

### 完整維護流程：腳本負責什麼、Agent 負責什麼（誠實劃分，非文字規則）

`refresh_skills.py` **本身沒有 Notion／GitHub 備份的憑證**，它是純本機腳本，因此完整
維護流程分兩段，缺一不可，各自都已用真實呼叫驗證過（非純協調）：

1. **取得資料階段（腳本，真實網路呼叫）**：`scripts/check_source_drift.py` 對
   `memory/skill-index.json` 內每一筆記錄執行 `git ls-remote <repo> HEAD`，取得該
   repo 目前真實的 HEAD commit，與記錄的 `analyzed_commit` 比對，輸出
   `{skill_id, recorded_analyzed_commit, live_head_commit, changed}` 清單。這是
   對真實 GitHub 的真實查詢，不是模擬。
2. **套用變更階段（Agent，透過 MCP 工具）**：`check_source_drift.py` 回報
   `changed: true` 的項目，由持有 Notion／GitHub MCP 工具存取權的 skill-retriever
   Agent 逐一執行：`git clone` 重新取得完整內容 → 依 `docs/scoring-rules.md`
   重新評分（只有實際變動的項目才重算，未變動的維持原分數）→
   `notion-update-page` 更新屬性與內容 → 寫回 `memory/skill-index.json` →
   `git commit && git push` 到備份 repo。這一段無法放進腳本本身（腳本沒有這些
   服務的憑證），但每一步都是 Agent 用真實工具呼叫執行，不是文字描述。

**已實測驗證（2026-09-20）**：
- 對全部 20 筆正式記錄執行 `check_source_drift.py`（真實 `git ls-remote`，非
  沙盒）：`checked: 20, changed: 0, errors: 0`——當天確實沒有任何來源異動，這本身
  是真實、可重現的結果，證明取得資料階段確實在查真實來源，而非固定回傳「無變化」。
  結果存於 `docs/evidence/drift_check_20260920.json`。
- 為了證明「偵測到需要更新時，套用變更階段真的會執行」而非只是理論上可以執行，
  對 `bc9c284e5a10`（tommygeoco/ui-audit）跑了一次明確標記為演練（drill）的完整
  週期：重新 `git clone` 取得即時內容（確認與 `analyzed_commit` 相符，真實網路
  I/O）→ 由於內容確實未變動，評分維持不變（證明「未變動不重算」的分支也會執行，
  不是只有變動分支被測過）→ 呼叫 `notion-update-page` 更新該筆 `Last Check
  Attempted`／`Last Check Succeeded`（Notion `page_last_edited_at` 確實隨之更新，
  可在該頁面歷史中查核）→ 寫回 `memory/skill-index.json`（新增
  `last_refresh_run_at`／`last_refresh_run_type`／`last_refresh_run_result` 三個
  欄位記錄本次演練）→ `git commit && git push` 到備份 repo（產生新的、可查核的
  commit）。四個環節（重新取得、Notion、記憶、備份）在同一次演練中都是真實執行，
  不是分開驗證後再宣稱串接。

**合併規則（已明訂邊界，取代原本模糊的「相同範圍重複觸發時合併」）**：
- 新請求的 scope 與執行中的 scope **完全相同**，或被執行中的 `scope=all` 涵蓋
  → 合併：不重複執行，等待現有執行完成後回傳同一份結果（標記
  `merged_into_existing_run: true`、`merged_with: <被合併的 request_id>`）。
- scope 不相容（例如一邊指定特定 skill_id、另一邊是特定標籤，且都不是 `all`）
  → 不合併，改為排隊等鎖，鎖釋放後各自獨立執行一次，避免同時寫入
  `memory/skill-index.json` 造成資料損毀，但不偽稱是同一次執行的結果。

已於 2026-09-20 在隔離沙盒（`/tmp/refresh-test/`，操作獨立複製的 index 檔，未觸碰
正式 `memory/` 目錄）以真實平行程序（非文字模擬）驗證：
1. 使用者直接觸發維護（`--trigger-source user_direct_call`，單一呼叫）→ 正確跑完、
   回傳 20 筆 `checked` 清單。
2. `refresh_skills` 介面呼叫（`--trigger-source refresh_skills_call`，`apply_updates`
   模式，範圍限定 `UI/UX` 標籤）→ 正確寫回 `last_check_attempted`/`last_check_succeeded`。
3. 兩個「相同範圍」（皆為 `all`）的請求相隔 0.3 秒同時觸發（其中一個故意讓實際工作
   耗時 3 秒以製造真實重疊視窗）→ 後到的請求正確被合併，回傳與先到請求完全相同的
   `request_id`／結果內容，只多了 `merged_into_existing_run: true` 與
   `merged_with` 欄位；`refresh.log` 顯示只有一次 `ACQUIRED`／`DONE`，沒有重複執行。
4. 兩個「不相容範圍」（一個是特定 `skill_id`、一個是 `UI/UX` 標籤）相隔 0.3 秒同時
   觸發 → 未被誤判為合併，第二個請求排隊等鎖後獨立執行了自己的一次完整流程
   （各自的 `request_id` 不同、`merged_into_existing_run: false`），驗證「不相容
   範圍不會被錯誤合併」。

詳細指令與完整輸出見 `docs/validation-log.md`。

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
