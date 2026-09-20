# 驗證紀錄

本文件記錄每次「已實測通過」的驗證，區別於文件層級的設計說明。日期一律為執行當下的環境日期。

## 2026-09-20（第二輪：核心功能端到端）

### 1. 完整來源讀取限制的成因與解法

**現象**：`mcp__github__get_file_contents`（GitHub MCP 內容讀取工具）只能存取本工作階段已明確 `add_repo` 的 repo（僅 `amber-ou/agent-office`、`amber-ou/skill-skill-Retriever`），對其餘公開 repo 一律回傳存取拒絕。

**成因**：該工具走 GitHub App／API 認證路徑，範圍由工作階段的 Repository Scope 設定決定，屬該工具本身的授權邊界，不是「使用者未授權讀取公開 GitHub」造成的限制。

**解法（已在既有授權範圍內完成，未新增任何權限）**：改用純 `git clone --depth 1 <公開 repo 的 HTTPS URL>` 取得內容。這條路徑走的是一般 HTTPS 智慧協定（經環境既有的 outbound proxy），不受該 GitHub MCP 工具的 Repository Scope 限制，且完全落在規格書「搜尋及讀取核准來源」的既有授權範圍內——**沒有請求任何新權限**。已用此方法完整讀取 5 個公開 repo（tommygeoco/ui-audit、sboghossian/design-skill、migueljnew-droid/ui-ux-gold-standard、konopkja/ethux-design、aaldere1/awesome-design-systems）。

`agent/skill-retriever.md` 與 `docs/interfaces.md` 已更新為以 `git clone` 作為 `get_skill` 與完整內容分析的標準方法，`mcp__github__search_code`／`search_repositories` 僅用於「搜尋候選」與「取得 stars/forks 等 API 專屬指標」。

### 2. 端到端試點：tommygeoco/ui-audit（skill_id `bc9c284e5a10`）

- 完整取得：`git clone` 全部 6 個檔案 + 19 個 references/*.md（共 5595 行），非僅 frontmatter。
- 四項評估：熱門度 30（scored）、實用度 84（scored）、可信度 71（scored）、可行度 98（scored）——四項皆有完整證據，無「未知」。
- 發現並修正兩個系統性資料品質問題（詳見下方「資料品質修正」）。
- Notion 記錄已更新（`bc9c284e5a10` 頁面），建議狀態改為「需人工確認」（授權宣稱與實際檔案不符、逾 180 天未維護）。
- 套件已交付至 `~/.claude/skill-retriever-cache/bc9c284e5a10/eea862b35b6c/`，25 個檔案，`diff -rq` 與 SHA-256 比對均與來源一致，完整性 `complete`，無需額外安裝依賴。

### 3. 資料品質修正（適用於本輪之前收錄的其餘 19 筆）

1. **「Analyzed Commit」誤用檔案 blob sha，非 commit sha**——`mcp__github__search_code` 回傳的 `sha` 欄位是檔案內容的 blob sha，不是該次分析對應的 commit。已在 `bc9c284e5a10` 修正為真正的 commit sha；其餘 19 筆待下一輪比照修正（見 `memory/state.json` backlog）。
2. **「Source Updated At」誤用 `updated_at`，應為 `pushed_at`**——GitHub API 的 `updated_at` 只要 repo 任何 metadata（例如被加星）異動就會更新，`pushed_at` 才是真正的程式碼推送時間。已在 `bc9c284e5a10` 修正（原記錄誤差達 8 個月），並連帶重算熱門度（35 → 30，因「近期活動」加分不再成立）。其餘 19 筆待下一輪修正。

### 4. 跨 Agent 呼叫驗證：`get_skill`

由另一個獨立的 `skill-retriever` Agent 實例（此環境已能動態辨識自訂 `subagent_type`，取代先前的平台限制）執行：
- 自行 `git clone` 取得 `bc9c284e5a10` 的獨立副本，未使用、未覆寫既有快取。
- Commit sha 與既有快取的 `eea862b35b6c472590c6c72b91e0cc2c184f5326` 完全相符。
- `diff -rq` 比對兩份副本結果為零差異（檔案清單與內容逐一一致）。
- 明確聲明未執行任何腳本（含 postinstall）、未安裝任何依賴、未寫入快取以外的任何位置。
- 正確判斷該 Skill 不需要另外安裝外部依賴。

**結論**：`get_skill` 介面在跨 Agent 情境下可重複、可驗證地取得一致的套件內容。

### 5. 失敗情境模擬（皆在隔離沙盒中執行，未觸碰正式 Notion 資料或正式備份 repo）

| 測項 | 方法 | 結果 |
| --- | --- | --- |
| 重試上限 | 對保證不存在的 GitHub repo 執行 3 次 `git clone`，間隔依 2s/4s 遞增等待 | 恰好嘗試 3 次後停止，不再重試；模擬的舊資料（`popularity_score: 42`）保持不變，`last_check_succeeded` 不更新，`last_check_attempted` 更新為當次時間，`last_error` 記錄失敗原因，未寫成零值、未偽裝成功 |
| 人工欄位保護 | 以 `scripts/guard_protected_fields.py` 對三組 payload（正常更新／夾帶 User Notes／夾帶 Manual Feedback）跑保護邏輯 | 正常 payload 放行；兩組夾帶人工欄位的 payload 皆被正確拒絕並丟出例外 |
| 備份失敗待同步 | 在獨立沙盒 git repo 中，本地先產生一筆新 commit，再將遠端指向保證不存在的 repo 並嘗試推送 | 推送依預期失敗（403／找不到 repo）；本地兩筆 commit（含尚未同步的那筆）完整保留、內容未遺失；示範寫回 `sync` 區塊的 `pending_sync: true` 狀態記錄，含失敗原因與待同步的本地 commit sha |

## 2026-09-20（第三輪：其餘 19 個 Skill 全量分析、commit/時間欄位分離、refresh_skills 真實實作）

### 1. 其餘 19 個 Skill 的完整流程套用

對第二輪剩下的 19 個 Skill（20 個收錄項目扣除已完成端到端試點的 `bc9c284e5a10`）
逐一執行：`git clone`（非 shallow，以取得檔案層級 commit 歷史）→ 完整讀取
`SKILL.md`／`README`／`references`／`LICENSE`／可疑指令掃描 → 四項評估 → 寫回
`memory/skill-index.json` → 更新 Notion。四項評估均逐一檢查；`29483f6259ab`
（carmahhawwari/ui-design-brain）與 `44dd2a37f2cb`（albertzhangz10/design-system-skill）
在上一輪因時間因素可信度／可行度暫缺，本輪已補齊實際評分（分別為 80/98 與
100/100），不再是「證據不足」，已於各自 `notes` 中註明原因與計算依據。

授權不明確項目（`bc8f5c0bb74a` migueljnew-droid、`e4e5c026b7c1` awesome-skills，
以及 `aa8f8ab8cb24` aaldere1 的既有備註）維持保留證據、標示「需人工確認」，不強行
給可信度分數；其餘可執行的分析（熱門度／實用度／可行度、關係比對）照常完成。

### 2. commit 與時間欄位全面重整（20 筆）

對全部 20 筆記錄，一律改用：
- `analyzed_commit`：`git rev-parse HEAD`（該次分析對應的完整 repo 快照 commit），
  **不再使用** `search_code` 回傳的檔案 blob sha。
- `repo_pushed_at`：`git log -1 --format=%cI`（repo 層級最後一次 commit 時間，
  換算為 UTC 日期），作為 repo 推送時間的代理指標。
- `skill_file_last_modified_at` + `skill_file_last_commit`：
  `git log -1 --format=%cI -- <skill 檔案路徑>`，Skill 檔案本身最後被修改的
  commit 與時間，與上面的 repo 層級時間**分開記錄**（兩者可能差距很大，例如
  `bb21949b19c2` repo 最後推送 2026-08-09，但其頂層索引檔案本身最後修改於
  2026-05-14）。
- 舊有單一欄位 `source_updated_at`（混用 repo/檔案時間、且第一批曾誤用
  `updated_at`）已從全部 20 筆移除，含補溯修正先前僅完成端到端試點的
  `bc9c284e5a10`（新增分離後的 `repo_pushed_at`/`skill_file_last_modified_at`/
  `skill_file_last_commit`，並以完整 clone 重新驗證兩者確實對應不同 commit）。

驗證方式：對 `memory/skill-index.json` 全部 20 筆執行程式化檢查，確認
`source_updated_at` 已完全移除、`analyzed_commit` 長度與格式符合 commit sha
（非 40 字元 blob sha 誤植、非 URL）、四個新欄位皆存在。

### 3. refresh_skills 由文字規則改為真實可執行實作

新增 `scripts/refresh_skills.py`：以檔案鎖（`fcntl.flock`）實作「同一時間只有一個
實際執行」，並明訂 scope 相容性判斷規則（完全相同或被 `all` 涵蓋才合併，否則排隊後
各自獨立執行）。已用真實平行程序（非文字模擬、非單純循序呼叫）在隔離沙盒驗證：

| 測項 | 方法 | 結果 |
| --- | --- | --- |
| 使用者直接觸發維護 | 單一呼叫 `--trigger-source user_direct_call --scope all --mode check_only` | 正確執行，回傳 20 筆 `checked` |
| `refresh_skills` 介面呼叫 | 單一呼叫 `--trigger-source refresh_skills_call --scope UI/UX --mode apply_updates` | 正確執行並寫回 `last_check_attempted`/`last_check_succeeded` |
| 同時觸發＋相同範圍（合併） | 兩個 `--scope all` 請求相隔 0.3 秒觸發，第一個故意耗時 3 秒 | 第二個請求正確合併：回傳與第一個完全相同的 `request_id`／內容，僅多 `merged_into_existing_run: true`；log 顯示僅一次 `ACQUIRED`/`DONE` |
| 同時觸發＋不相容範圍（不應合併） | 一個 `--scope ids:bc9c284e5a10`、一個 `--scope UI/UX` 相隔 0.3 秒觸發 | 未誤判為合併，第二個請求排隊等鎖後獨立執行了自己的一次完整流程（各自 `request_id` 不同、皆為 `merged_into_existing_run: false`） |

沙盒操作對象為 `/tmp/refresh-test/` 下的獨立複製檔案（含獨立 `SKILL_RETRIEVER_MEMORY_DIR`），
未寫入正式 `memory/` 目錄或正式 Notion 資料。完整指令與原始輸出保留在本次工作階段紀錄中。

## 2026-09-20（關係重新檢視）

- 對所有僅由 SKILL.md frontmatter 片段支持的關係結論，信心一律下修為 `low`，並在 `evidence` 欄位註明「僅根據片段，未讀取完整內容」。
- `design`（sboghossian）↔`ux-designer`（szilu）：一側（design）已補齊完整內容，信心提升為 `medium`。
- `design`（sboghossian）↔`ui-ux-pro-max`（migueljnew-droid）：原「待確認」已調查釐清——完整讀取 design 全文並跨庫 grep，查無直接引用證據，改列「無明顯關聯」，信心 `medium`。
- `design-system-library`（aaldere1）↔ 外部來源 `VoltAgent/awesome-design-md`：新增「衍生自」關係，信心 `high`（作者在 README 明確聲明內容直接取自對方），並記錄雙方皆無 LICENSE 檔案的授權不明確風險。
- `ethux-design`（konopkja）的 8 個 SKILL.md 已確認：1 個頂層索引（已收錄）+ 7 個子 Skill（approvals／gas／multichain／onboarding／safety／signing／wallets），皆有獨立名稱、描述與範疇，結構上符合獨立建檔條件；但建檔會使總收錄數超過首次 20 個上限，已詢問使用者是否要建檔、建多少、或留到下一批次。
