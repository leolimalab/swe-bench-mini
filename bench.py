#!/usr/bin/env python3
"""
swe-bench-mini — Lightweight local AI code benchmark.
Benchmarks local LLMs (via llama.cpp) on code generation, bug fixing,
and refactoring tasks.

Usage:
    python bench.py                          # Run all models, all tasks
    python bench.py --model "Qwen 3.5"       # Run specific model
    python bench.py --task generation        # Run specific task category
    python bench.py --list-models            # List configured models
    python bench.py --list-tasks             # List available tasks
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml


def load_config(path="config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def load_tasks(task_dir="tasks"):
    """Load all task JSON files from tasks/ directory."""
    tasks_dir = Path(task_dir)
    all_tasks = {}
    for f in sorted(tasks_dir.glob("*.json")):
        category = f.stem  # generation, bug_fixing, refactoring
        with open(f) as fh:
            tasks = json.load(fh)
        all_tasks[category] = tasks
    return all_tasks


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


def main():
    parser = argparse.ArgumentParser(
        description="swe-bench-mini — Benchmark local LLMs on code tasks"
    )
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    parser.add_argument("--model", "-m", help="Run only a specific model (name or partial match)")
    parser.add_argument("--task", "-t", choices=["generation", "bug_fixing", "refactoring", "all"],
                        default="all", help="Task category to run")
    parser.add_argument("--list-models", action="store_true", help="List configured models")
    parser.add_argument("--list-tasks", action="store_true", help="List available tasks")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    args = parser.parse_args()

    config = load_config(args.config)
    models = config["models"]
    tasks = load_tasks()
    task_order = ["generation", "bug_fixing", "refactoring"]

    # --- List commands ---
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
                print(f"    {diff_emoji.get(t['difficulty'], '⚪')} {t['id']}: {t['name']}")
        return

    # --- Filter models ---
    if args.model:
        filtered = [m for m in models if args.model.lower() in m["name"].lower()]
        if not filtered:
            print(f"❌ Model '{args.model}' not found. Use --list-models to see available models.")
            sys.exit(1)
        models = filtered

    # --- Filter tasks ---
    if args.task != "all":
        task_order = [args.task]

    # --- Run benchmark ---
    print(f"\n{'='*60}")
    print(f"  🧪 SWE-BENCH-MINI")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    print(f"  Models: {', '.join(m['name'] for m in models)}")
    print(f"  Tasks:  {', '.join(task_order)}")
    print(f"{'='*60}\n")

    from core.runner import Runner
    from core.evaluator import Evaluator
    from core.reporter import Reporter

    runner = Runner(config)
    evaluator = Evaluator()
    reporter = Reporter(config)

    all_results = []

    for model_cfg in models:
        print(f"\n🔷 {model_cfg['name']}")
        print(f"{'─'*50}")

        for cat in task_order:
            cat_tasks = tasks.get(cat, [])
            if not cat_tasks:
                continue

            print(f"\n  📝 {cat.replace('_', ' ').title()} ({len(cat_tasks)})")

            for task in cat_tasks:
                label = f"{task['id']}: {task['name']}"
                print(f"    {label}... ", end="", flush=True)

                t0 = time.time()

                # Run model on task
                response = runner.run(model_cfg, task)
                if response is None:
                    print("❌ Failed (connection)")
                    continue

                # Evaluate
                score = evaluator.evaluate(task, response["text"])
                elapsed = time.time() - t0

                result = {
                    "model": model_cfg["name"],
                    "task": cat,
                    "case": task["name"],
                    "task_id": task["id"],
                    "difficulty": task.get("difficulty", "unknown"),
                    "response": response["text"],
                    "response_time": round(response["elapsed"], 2),
                    "total_elapsed": round(elapsed, 2),
                    "prompt_tokens": response.get("prompt_tokens", 0),
                    "completion_tokens": response.get("completion_tokens", 0),
                    **score,
                }
                all_results.append(result)

                # Show score
                total = result["total_score"]
                if total >= 80:
                    emoji = "✅"
                elif total >= 40:
                    emoji = "⚠️"
                else:
                    emoji = "❌"

                detail = f"{emoji} {total}/100"
                if result.get("tests_total", 0) > 0:
                    detail += f" | tests: {result['tests_passed']}/{result['tests_total']}"
                detail += f" | {result['response_time']}s"
                print(detail)

                if args.verbose:
                    print(f"       Code:\n{result.get('code', '(none)')[:500]}")

    # --- Generate report ---
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


if __name__ == "__main__":
    main()
