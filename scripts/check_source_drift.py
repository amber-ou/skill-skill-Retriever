#!/usr/bin/env python3
"""真正的「來源是否變動」偵測（refresh_skills 維護流程的取得資料階段）。

對 memory/skill-index.json 內每一筆記錄，用 `git ls-remote <repo> HEAD`
取得該 repo 目前真實的 HEAD commit（真實網路呼叫，非模擬），與記錄的
analyzed_commit 比對。回傳結構化清單，供上層維護流程判斷是否需要重新
下載、重新評分、更新 Notion 與備份。

本腳本本身不呼叫 Notion／不寫入備份 repo——它沒有這些憑證。偵測到
changed=true 後的「重新取得資料、更新分析、Notion、記憶及備份」四個
動作，由持有 MCP 工具存取權的 skill-retriever Agent 執行（見
docs/interfaces.md「refresh_skills 的實際維護流程」一節），本腳本只負責
用真實方式回答「要不要做」。
"""
import argparse
import json
import subprocess
import sys


def live_head_commit(repo_url, timeout=20):
    try:
        out = subprocess.run(
            ["git", "ls-remote", repo_url, "HEAD"],
            capture_output=True, text=True, timeout=timeout, check=True,
        )
        line = out.stdout.strip().splitlines()[0] if out.stdout.strip() else ""
        return line.split("\t")[0] if line else None
    except Exception as exc:  # noqa: BLE001 - report, don't crash the batch
        return f"__error__:{exc}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", required=True)
    ap.add_argument("--skill-ids", help="comma-separated; omit for all")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.index) as f:
        idx = json.load(f)

    if args.skill_ids:
        wanted = set(args.skill_ids.split(","))
        idx = [e for e in idx if e["skill_id"] in wanted]

    results = []
    for e in idx:
        repo_url = f"https://github.com/{e['repo']}.git"
        live = live_head_commit(repo_url)
        recorded = e.get("analyzed_commit", "")
        if live is None:
            status = "error_no_output"
            changed = None
        elif isinstance(live, str) and live.startswith("__error__:"):
            status = live
            changed = None
        else:
            changed = not live.startswith(recorded) and not recorded.startswith(live[:len(recorded)])
            status = "ok"
        results.append({
            "skill_id": e["skill_id"],
            "repo": e["repo"],
            "recorded_analyzed_commit": recorded,
            "live_head_commit": live if isinstance(live, str) and not live.startswith("__error__:") else None,
            "changed": changed,
            "status": status,
        })

    with open(args.out, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    changed_count = sum(1 for r in results if r["changed"])
    error_count = sum(1 for r in results if r["status"] != "ok")
    print(json.dumps({
        "checked": len(results),
        "changed": changed_count,
        "errors": error_count,
        "out": args.out,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
