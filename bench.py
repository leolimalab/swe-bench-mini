#!/usr/bin/env python3
"""
swe-bench-mini — Lightweight local AI code benchmark.
Benchmarks local LLMs (via llama.cpp) on code tasks using F2P/P2P evaluation.

Usage:
    python bench.py                          # Run all models, all tasks
    python bench.py --model "Qwen 3.5"       # Run specific model
    python bench.py --task generation        # Run specific task category
    python bench.py --task-id fix-101         # Run a single task
    python bench.py --checkpoint results/run.json
    python bench.py --resume results/run.json
    python bench.py --dry-run results/bench.json
    python bench.py --consolidate a.json b.json
    python bench.py --compare a.json b.json
    python bench.py --list-models
    python bench.py --list-tasks
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

DEFAULT_TASK_ORDER = [
    "generation", "bug_fixing", "refactoring", "sql", "data_processing",
]


def load_config(path="config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def load_tasks(task_dir="tasks"):
    """Load all task JSON files from tasks/ directory."""
    tasks_dir = Path(task_dir)
    all_tasks = {}
    for f in sorted(tasks_dir.glob("*.json")):
        category = f.stem
        with open(f) as fh:
            all_tasks[category] = json.load(fh)
    return all_tasks


def load_results_json(path):
    with open(path) as f:
        return json.load(f)


def save_results_json(path, results):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


def task_key(model_name, task_id):
    return f"{model_name}::{task_id}"


def completed_keys(results):
    return {task_key(r["model"], r["task_id"]) for r in results}


def check_model(model_cfg):
    """Quick connectivity check for a model endpoint."""
    import urllib.request
    endpoint = model_cfg["endpoint"].rstrip("/")
    try:
        headers = {"Content-Type": "application/json"}
        api_key = model_cfg.get("api_key", "")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        req = urllib.request.Request(
            f"{endpoint}/models",
            headers=headers,
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return True
    except Exception:
        return False


def format_short(result):
    """Short one-line format for per-task display."""
    res = result.get("resolution", "NO")
    cat = result.get("failure_category", "")
    f2p = f"{result.get('f2p_passed', 0)}/{result.get('f2p_total', 0)}"
    p2p = f"{result.get('p2p_passed', 0)}/{result.get('p2p_total', 0)}"
    score = result.get("total_score", 0)

    emoji = {"FULL": "✅", "PARTIAL": "⚠️", "REGRESSION": "🔴"}.get(res, "❌")
    parts = [f"{emoji} {res} {score}/100"]
    if result.get("f2p_total", 0) > 0:
        parts.append(f"F2P:{f2p}")
    if result.get("p2p_total", 0) > 0:
        parts.append(f"P2P:{p2p}")
    if cat:
        parts.append(f"({cat})")
    parts.append(f"| {result.get('response_time', 0):.1f}s")
    return " ".join(parts)


def build_result(model_cfg, cat, task, response, score, elapsed):
    return {
        "model": model_cfg["name"],
        "task": cat,
        "case": task["name"],
        "task_id": task["id"],
        "difficulty": task.get("difficulty", "unknown"),
        "response": response.get("text", ""),
        "response_time": round(response.get("elapsed", 0), 2),
        "total_elapsed": round(elapsed, 2),
        "prompt_tokens": response.get("prompt_tokens", 0),
        "completion_tokens": response.get("completion_tokens", 0),
        "reasoning_content": response.get("reasoning_content"),
        **score,
    }


def run_dry_run(path, verbose):
    from core.evaluator import Evaluator

    saved = load_results_json(path)
    tasks = load_tasks()
    task_by_id = {}
    for cat, cat_tasks in tasks.items():
        for t in cat_tasks:
            task_by_id[t["id"]] = (cat, t)

    evaluator = Evaluator()
    results = []
    print(f"\n🔄 Dry-run re-evaluation: {path}\n")

    for entry in saved:
        tid = entry.get("task_id")
        if tid not in task_by_id:
            print(f"  ⚠️  Skipping unknown task_id: {tid}")
            continue
        cat, task = task_by_id[tid]
        score = evaluator.evaluate(task, entry.get("response", ""))
        result = {
            "model": entry.get("model", "unknown"),
            "task": cat,
            "case": task["name"],
            "task_id": tid,
            "difficulty": task.get("difficulty", "unknown"),
            "response": entry.get("response", ""),
            "response_time": entry.get("response_time", 0),
            "total_elapsed": entry.get("total_elapsed", 0),
            "prompt_tokens": entry.get("prompt_tokens", 0),
            "completion_tokens": entry.get("completion_tokens", 0),
            **score,
        }
        results.append(result)
        print(f"  {tid}: {format_short(result)}")
        if verbose and result.get("error"):
            print(f"       Error: {result['error']}")

    return results


def run_consolidate(paths, config):
    merged = []
    seen = set()
    for path in paths:
        for r in load_results_json(path):
            key = task_key(r["model"], r["task_id"])
            if key not in seen:
                merged.append(r)
                seen.add(key)
            else:
                print(f"  ⚠️  Duplicate skipped: {r['model']} / {r['task_id']} from {path}")

    print(f"\n📦 Consolidated {len(merged)} unique results from {len(paths)} file(s)")
    from core.reporter import Reporter
    reporter = Reporter(config)
    task_order = sorted(set(r.get("task", "unknown") for r in merged))
    paths_out = reporter.generate(merged, task_order)
    print("  Reports saved:")
    for fmt, p in paths_out.items():
        print(f"     • {fmt.upper()}: {p}")
    return merged


def run_compare(baseline_path, current_path, config):
    baseline = load_results_json(baseline_path)
    current = load_results_json(current_path)
    from core.reporter import Reporter
    reporter = Reporter(config)
    out_path = reporter.compare(baseline, current, baseline_path, current_path)
    print(f"\n📊 Comparison report: {out_path}")
    return out_path


def run_benchmark(args, config, models, tasks, task_order):
    from core.runner import Runner
    from core.evaluator import Evaluator
    from core.reporter import Reporter

    runner = Runner(config)
    evaluator = Evaluator()
    reporter = Reporter(config)

    all_results = []
    if args.resume:
        all_results = load_results_json(args.resume)
        print(f"  Resuming from {args.resume} ({len(all_results)} results loaded)")

    done = completed_keys(all_results)
    checkpoint_path = args.checkpoint or args.resume

    print(f"\n{'='*60}")
    print(f"  SWE-BENCH-MINI v2")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    print(f"  Models: {', '.join(m['name'] for m in models)}")
    print(f"  Tasks:  {', '.join(task_order)}")
    if checkpoint_path:
        print(f"  Checkpoint: {checkpoint_path}")
    print(f"{'='*60}\n")

    for model_cfg in models:
        print(f"\n🔷 {model_cfg['name']}")
        print(f"{'─'*50}")

        for cat in task_order:
            cat_tasks = tasks.get(cat, [])
            if not cat_tasks:
                continue

            if args.task_id:
                cat_tasks = [t for t in cat_tasks if t["id"] == args.task_id]
                if not cat_tasks:
                    continue

            print(f"\n  📝 {cat.replace('_', ' ').title()} ({len(cat_tasks)} tasks)")

            for task in cat_tasks:
                key = task_key(model_cfg["name"], task["id"])
                if key in done:
                    print(f"    {task['id']}: {task['name']}... ⏭️  skipped (done)")
                    continue

                label = f"{task['id']}: {task['name']}"
                print(f"    {label}... ", end="", flush=True)

                t0 = time.time()
                response = runner.run(model_cfg, task)

                if response is None or response.get("error"):
                    err = response.get("error", "connection failed") if response else "connection failed"
                    print(f"❌ Failed ({err})")
                    if args.verbose:
                        print(f"       API error: {err}")
                    continue

                score = evaluator.evaluate(task, response["text"])
                elapsed = time.time() - t0
                result = build_result(model_cfg, cat, task, response, score, elapsed)
                all_results.append(result)
                done.add(key)

                print(format_short(result))

                if args.verbose:
                    code = result.get("code", "")
                    if code:
                        print(f"       Code ({len(code)} chars):\n{code[:300]}")
                    reasoning = result.get("reasoning_content")
                    if reasoning:
                        print(f"       Thinking ({len(reasoning)} chars): {reasoning[:200]}...")
                    if task.get("hints"):
                        print(f"       💡 Dica: {task['hints']}")

                if checkpoint_path:
                    save_results_json(checkpoint_path, all_results)

    if all_results:
        print(f"\n{'='*60}")
        print(f"  📊 Generating Report...")
        report_paths = reporter.generate(all_results, task_order)
        print(f"  ✅ Reports saved:")
        for fmt, path in report_paths.items():
            print(f"     • {fmt.upper()}: {path}")
        print(f"{'='*60}")
    else:
        print("\n❌ No results to report.")

    return all_results


def main():
    parser = argparse.ArgumentParser(
        description="swe-bench-mini — Benchmark local LLMs on code tasks"
    )
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    parser.add_argument("--model", "-m", help="Run only a specific model (name or partial match)")
    parser.add_argument(
        "--task", "-t",
        choices=["generation", "bug_fixing", "refactoring", "sql", "data_processing", "all"],
        default="all",
        help="Task category to run",
    )
    parser.add_argument("--task-id", help="Run only a specific task by id (e.g. fix-101)")
    parser.add_argument("--list-models", action="store_true", help="List configured models")
    parser.add_argument("--list-tasks", action="store_true", help="List available tasks")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    parser.add_argument("--checkpoint", help="Save results to this JSON file after each task")
    parser.add_argument("--resume", help="Resume from a checkpoint JSON file")
    parser.add_argument("--dry-run", metavar="FILE", help="Re-evaluate saved responses without calling LLM")
    parser.add_argument("--consolidate", nargs="+", metavar="FILE", help="Merge result files and generate report")
    parser.add_argument("--compare", nargs=2, metavar=("BASELINE", "CURRENT"), help="Compare two result files")
    args = parser.parse_args()

    config = load_config(args.config)
    models = config["models"]
    tasks = load_tasks()
    task_order = list(DEFAULT_TASK_ORDER)

    if args.list_models:
        print("\n📋 Configured Models:")
        for i, m in enumerate(models):
            status = "✅" if check_model(m) else "❌"
            print(f"  {i}. {status} {m['name']}")
            print(f"     Endpoint: {m['endpoint']}")
            print(f"     Model ID: {m.get('model_id', '(default)')}")
            print(f"     {m.get('description', '')}")
        return

    if args.list_tasks:
        print("\n📋 Available Tasks:")
        for cat in task_order:
            cat_tasks = tasks.get(cat, [])
            print(f"\n  📁 {cat.replace('_', ' ').title()} ({len(cat_tasks)})")
            for t in cat_tasks:
                diff_emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}
                f2p = len(t.get("fail_to_pass", []))
                p2p = len(t.get("pass_to_pass", []))
                hints = " 💡" if t.get("hints") else ""
                print(
                    f"    {diff_emoji.get(t['difficulty'], '⚪')} {t['id']}: {t['name']}"
                    f" (F2P:{f2p} P2P:{p2p}){hints}"
                )
        return

    if args.compare:
        run_compare(args.compare[0], args.compare[1], config)
        return

    if args.consolidate:
        run_consolidate(args.consolidate, config)
        return

    if args.dry_run:
        results = run_dry_run(args.dry_run, args.verbose)
        if results:
            from core.reporter import Reporter
            reporter = Reporter(config)
            task_order_used = sorted(set(r["task"] for r in results))
            paths = reporter.generate(results, task_order_used)
            print("\n  Reports saved:")
            for fmt, p in paths.items():
                print(f"     • {fmt.upper()}: {p}")
        return

    if args.model:
        filtered = [m for m in models if args.model.lower() in m["name"].lower()]
        if not filtered:
            print(f"❌ Model '{args.model}' not found. Use --list-models to see available models.")
            sys.exit(1)
        models = filtered

    if args.task != "all":
        task_order = [args.task]

    if args.task_id:
        found = any(
            t["id"] == args.task_id
            for cat in task_order
            for t in tasks.get(cat, [])
        )
        if not found:
            print(f"❌ Task '{args.task_id}' not found. Use --list-tasks.")
            sys.exit(1)

    run_benchmark(args, config, models, tasks, task_order)


if __name__ == "__main__":
    main()
