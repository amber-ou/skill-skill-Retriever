#!/usr/bin/env python3
"""任何自動流程（find_skills / compare_skills / get_skill / refresh_skills）
在呼叫 Notion 的 update_properties 之前，都必須先過這一關。

用法（Agent 在組好 properties dict 之後，送出 API 呼叫之前）：

    from guard_protected_fields import assert_no_protected_fields
    assert_no_protected_fields(properties)  # 觸碰人工欄位會直接丟例外，中止該次更新

已由 memory/state.json 的 validation.manual_field_guard_test 記錄一次通過測試
（正常 payload 放行、夾帶 User Notes / Manual Feedback 的 payload 皆被拒絕）。
"""

PROTECTED_FIELDS = {"User Notes", "Manual Feedback"}


def assert_no_protected_fields(properties: dict, allow_override: bool = False) -> bool:
    hit = PROTECTED_FIELDS.intersection(properties.keys())
    if hit and not allow_override:
        raise ValueError(
            f"拒絕自動更新：payload 觸碰了人工欄位 {sorted(hit)}。"
            f"自動流程一律不得覆寫這些欄位；若真的需要修改，"
            f"必須是使用者本人明確要求的操作（allow_override=True 僅供這種情況使用）。"
        )
    return True
