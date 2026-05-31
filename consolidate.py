#!/usr/bin/env python3
"""Consolidate all partial results and generate final report."""
import json, yaml, time, sys, os, glob
sys.path.insert(0, '.')
from core.reporter import Reporter

# 1) Load latest bug_fixing results
with open('results/bench_20260531_145308.json') as f:
    bugfix_results = json.load(f)

# 2) Filter out gen and refac from that file (we only want bug_fixing)
bugfix_only = [r for r in bugfix_results if r['task'] == 'bug_fixing']

# 3) Get gen and refac results from separate files
# The gen results are in bench_20260531_134145.json
with open('results/bench_20260531_134145.json') as f:
    gen_results = json.load(f)

# 4) Get refac results
with open('results/bench_20260531_144019.json') as f:
    refac_results = json.load(f)

# 5) Merge all results (replace bug_fixing in bugfix_results with our clean run)
all_results = gen_results + bugfix_only + refac_results

print(f'Total consolidated results: {len(all_results)}')
by_task = {}
for r in all_results:
    by_task[r['task']] = by_task.get(r['task'], 0) + 1
for t, c in sorted(by_task.items()):
    print(f'  {t}: {c}')

# 6) Replace fix-106 and fix-304 with the corrected versions
# The results are already in bugfix_only, which ran fix-106 and fix-304
# But let's verify
fix106 = [r for r in all_results if r['task_id'] == 'fix-106']
fix304 = [r for r in all_results if r['task_id'] == 'fix-304']
print(f'\nfix-106: {fix106[0]["resolution"]} {fix106[0]["total_score"]}/100' if fix106 else 'fix-106 not found!')
print(f'fix-304: {fix304[0]["resolution"]} {fix304[0]["total_score"]}/100' if fix304 else 'fix-304 not found!')

# 7) Generate report
with open('config.yaml') as f:
    config = yaml.safe_load(f)

reporter = Reporter(config)
task_order = ['generation', 'bug_fixing', 'refactoring']
paths = reporter.generate(all_results, task_order)

print(f'\nReports generated:')
for fmt, path in paths.items():
    print(f'  {fmt.upper()}: {path}')

# 8) Show summary
models = sorted(set(r['model'] for r in all_results))
print(f'\n=== SUMMARY ===')
for model in models:
    model_results = [r for r in all_results if r['model'] == model]
    total = len(model_results)
    full = sum(1 for r in model_results if r.get('resolution') == 'FULL')
    partial = sum(1 for r in model_results if r.get('resolution') == 'PARTIAL')
    no = sum(1 for r in model_results if r.get('resolution') == 'NO')
    regression = sum(1 for r in model_results if r.get('resolution') == 'REGRESSION')
    avg = sum(r['total_score'] for r in model_results) / total
    print(f'\n{model}:')
    print(f'  Total: {total} tasks')
    print(f'  ✅ FULL: {full} | ⚠️ PARTIAL: {partial} | ❌ NO: {no} | 🔴 REGRESSION: {regression}')
    print(f'  Média: {avg:.0f}/100')
