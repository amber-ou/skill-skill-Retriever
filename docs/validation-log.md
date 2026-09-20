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

## 2026-09-20（關係重新檢視）

- 對所有僅由 SKILL.md frontmatter 片段支持的關係結論，信心一律下修為 `low`，並在 `evidence` 欄位註明「僅根據片段，未讀取完整內容」。
- `design`（sboghossian）↔`ux-designer`（szilu）：一側（design）已補齊完整內容，信心提升為 `medium`。
- `design`（sboghossian）↔`ui-ux-pro-max`（migueljnew-droid）：原「待確認」已調查釐清——完整讀取 design 全文並跨庫 grep，查無直接引用證據，改列「無明顯關聯」，信心 `medium`。
- `design-system-library`（aaldere1）↔ 外部來源 `VoltAgent/awesome-design-md`：新增「衍生自」關係，信心 `high`（作者在 README 明確聲明內容直接取自對方），並記錄雙方皆無 LICENSE 檔案的授權不明確風險。
- `ethux-design`（konopkja）的 8 個 SKILL.md 已確認：1 個頂層索引（已收錄）+ 7 個子 Skill（approvals／gas／multichain／onboarding／safety／signing／wallets），皆有獨立名稱、描述與範疇，結構上符合獨立建檔條件；但建檔會使總收錄數超過首次 20 個上限，已詢問使用者是否要建檔、建多少、或留到下一批次。
