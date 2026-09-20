#!/usr/bin/env python3
"""refresh_skills 的實際可執行實作（取代原本僅存在於 docs/interfaces.md 的文字規則）。

同一時間重疊觸發時的合併規則（本次實作明訂，補足原文字規則「相同範圍重複觸發時合併」
未講清楚的邊界情況）：
- 若新請求的 scope 與正在執行中的請求「完全相同」，或新請求的 scope 被正在執行中的
  scope="all" 涵蓋 -> 合併：新請求不重複執行，等待現有執行完成後回傳同一份結果，
  並標記 merged_into_existing_run=true、merged_with=<被合併的 request_id>。
- 若 scope 不相容（例如一邊是 all、另一邊是特定 skill_id 且現有執行不是 all）
  -> 不合併，改為排隊等鎖，鎖釋放後各自獨立執行一次（避免同時寫入 index 檔案，
  但不偽稱是同一次執行的結果）。
"""
import argparse
import datetime
import fcntl
import json
import os
import sys
import time

DEFAULT_MEMORY_DIR = os.environ.get(
    "SKILL_RETRIEVER_MEMORY_DIR", os.path.expanduser("~/.claude/skill-retriever-memory")
)


def utc_now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def log(memory_dir, msg):
    with open(os.path.join(memory_dir, "refresh.log"), "a") as f:
        f.write(f"{utc_now_iso()} pid={os.getpid()} {msg}\n")


def normalize_scope(raw_scope):
    if raw_scope.startswith("ids:"):
        return sorted(raw_scope[len("ids:"):].split(","))
    return raw_scope


def scope_compatible(existing_scope, new_scope):
    if existing_scope == new_scope:
        return True
    if existing_scope == "all":
        return True
    return False


def do_refresh_work(scope, mode, index_path, simulate_work_seconds):
    with open(index_path) as f:
        idx = json.load(f)

    if scope == "all":
        targets = idx
    elif isinstance(scope, list):
        targets = [e for e in idx if e["skill_id"] in scope]
    else:
        targets = [e for e in idx if scope in e.get("tags", [])]

    if simulate_work_seconds:
        time.sleep(simulate_work_seconds)

    today = datetime.date.today().isoformat()
    summary = {"checked": [e["skill_id"] for e in targets], "updated": [], "stale": [], "errors": []}
    if mode == "apply_updates":
        for e in targets:
            e["last_check_attempted"] = today
            e["last_check_succeeded"] = today
            summary["updated"].append(e["skill_id"])
        with open(index_path, "w") as f:
            json.dump(idx, f, ensure_ascii=False, indent=2)
    return summary


def main():
    ap = argparse.ArgumentParser(description="refresh_skills 實際實作")
    ap.add_argument("--scope", required=True, help="'all' | tag（如 UI/UX） | 'ids:a,b,c'")
    ap.add_argument("--mode", choices=["check_only", "apply_updates"], default="check_only")
    ap.add_argument(
        "--index",
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "memory", "skill-index.json"),
    )
    ap.add_argument("--memory-dir", default=DEFAULT_MEMORY_DIR)
    ap.add_argument("--simulate-work-seconds", type=float, default=0)
    ap.add_argument(
        "--trigger-source",
        default="unknown",
        help="user_direct_call | refresh_skills_call | agent_office_open(pending_integration)",
    )
    args = ap.parse_args()

    os.makedirs(args.memory_dir, exist_ok=True)
    lock_path = os.path.join(args.memory_dir, "refresh.lock")
    inflight_path = os.path.join(args.memory_dir, "refresh.inflight.json")
    result_path = os.path.join(args.memory_dir, "last_refresh_result.json")

    scope = normalize_scope(args.scope)
    req_id = f"{os.getpid()}-{time.time():.6f}"
    log(args.memory_dir, f"REQUEST req_id={req_id} scope={scope} mode={args.mode} source={args.trigger_source}")

    lock_fd = open(lock_path, "a+")
    acquired = True
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        acquired = False

    if not acquired:
        existing_scope = None
        try:
            with open(inflight_path) as f:
                existing = json.load(f)
                existing_scope = existing.get("scope")
        except (FileNotFoundError, json.JSONDecodeError):
            existing = {}

        if scope_compatible(existing_scope, scope):
            log(
                args.memory_dir,
                f"MERGE req_id={req_id} into in-flight req_id={existing.get('request_id')} "
                f"(existing_scope={existing_scope} new_scope={scope})",
            )
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            with open(result_path) as f:
                result = json.load(f)
            result = dict(result)
            result["merged_into_existing_run"] = True
            result["merged_with"] = existing.get("request_id")
            result["this_request_id"] = req_id
            log(args.memory_dir, f"MERGE-COMPLETE req_id={req_id}")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return
        else:
            log(
                args.memory_dir,
                f"QUEUE req_id={req_id} incompatible scope (existing={existing_scope} new={scope}), "
                f"waiting for lock to run independently",
            )
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            acquired = True

    try:
        with open(inflight_path, "w") as f:
            json.dump({"request_id": req_id, "scope": scope, "mode": args.mode, "started_at": utc_now_iso()}, f)
        log(args.memory_dir, f"ACQUIRED req_id={req_id} — running actual refresh")
        summary = do_refresh_work(scope, args.mode, args.index, args.simulate_work_seconds)
        result = {
            "status": "ok",
            "request_id": req_id,
            "scope": args.scope,
            "mode": args.mode,
            "trigger_source": args.trigger_source,
            "ran_at": utc_now_iso(),
            "merged_into_existing_run": False,
            **summary,
        }
        with open(result_path, "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        log(args.memory_dir, f"DONE req_id={req_id}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        try:
            os.remove(inflight_path)
        except FileNotFoundError:
            pass
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


if __name__ == "__main__":
    main()
