#!/usr/bin/env python3
"""Validate task JSON files against the swe-bench-mini schema."""

import ast
import json
import sys
from pathlib import Path

REQUIRED_FIELDS = {
    "id", "name", "category", "difficulty", "description",
    "instruction", "fail_to_pass", "pass_to_pass", "timeout",
}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_EVAL_MODES = {"generation", "bug_fixing"}
CODE_CONTEXT_REQUIRED = {"bug_fixing", "refactoring"}


def validate_assert(assert_code, task_id, index, list_name):
    """Check that an assert string is syntactically valid in a wrapper."""
    wrapper = f"{assert_code}\n"
    try:
        ast.parse(wrapper)
    except SyntaxError as e:
        return f"{task_id}: {list_name}[{index}] syntax error: {e}"
    return None


def validate_task(task, filepath):
    errors = []
    warnings = []
    task_id = task.get("id", "?")

    missing = REQUIRED_FIELDS - set(task.keys())
    if missing:
        errors.append(f"{task_id}: missing fields: {sorted(missing)}")

    if task.get("difficulty") not in VALID_DIFFICULTIES:
        errors.append(f"{task_id}: invalid difficulty '{task.get('difficulty')}'")

    mode = task.get("evaluation_mode")
    if mode is not None and mode not in VALID_EVAL_MODES:
        errors.append(f"{task_id}: invalid evaluation_mode '{mode}'")

    category = task.get("category", "")
    code_ctx = task.get("code_context")
    if category in CODE_CONTEXT_REQUIRED and not code_ctx:
        errors.append(f"{task_id}: code_context required for {category}")
    if category == "generation" and code_ctx is not None:
        warnings.append(f"{task_id}: generation task has non-null code_context")

    f2p = task.get("fail_to_pass", [])
    p2p = task.get("pass_to_pass", [])
    if not f2p:
        errors.append(f"{task_id}: fail_to_pass is empty")

    if f2p == p2p and category not in ("generation",):
        warnings.append(
            f"{task_id}: F2P==P2P in category '{category}' "
            "(expected only for generation)"
        )

    for i, a in enumerate(f2p):
        err = validate_assert(a, task_id, i, "fail_to_pass")
        if err:
            errors.append(err)

    for i, a in enumerate(p2p):
        err = validate_assert(a, task_id, i, "pass_to_pass")
        if err:
            errors.append(err)

    expected_category = filepath.stem
    if category != expected_category:
        errors.append(
            f"{task_id}: category '{category}' != file '{expected_category}'"
        )

    return errors, warnings


def main():
    tasks_dir = Path("tasks")
    if not tasks_dir.exists():
        print("❌ tasks/ directory not found")
        sys.exit(1)

    all_ids = {}
    all_errors = []
    all_warnings = []
    total = 0

    for filepath in sorted(tasks_dir.glob("*.json")):
        with open(filepath) as f:
            tasks = json.load(f)
        if not isinstance(tasks, list):
            all_errors.append(f"{filepath}: root must be a JSON array")
            continue
        for task in tasks:
            total += 1
            tid = task.get("id", "?")
            if tid in all_ids:
                all_errors.append(f"{tid}: duplicate id (also in {all_ids[tid]})")
            else:
                all_ids[tid] = filepath.name
            errs, warns = validate_task(task, filepath)
            all_errors.extend(errs)
            all_warnings.extend(warns)

    print(f"Validated {total} tasks in {len(list(tasks_dir.glob('*.json')))} files\n")

    if all_warnings:
        print(f"⚠️  {len(all_warnings)} warning(s):")
        for w in all_warnings:
            print(f"  {w}")
        print()

    if all_errors:
        print(f"❌ {len(all_errors)} error(s):")
        for e in all_errors:
            print(f"  {e}")
        sys.exit(1)

    print(f"✅ All {total} tasks valid")
    if all_warnings:
        print(f"   ({len(all_warnings)} warnings — non-blocking)")


if __name__ == "__main__":
    main()
