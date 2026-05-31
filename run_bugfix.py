#!/usr/bin/env python3
"""Run all bug_fixing tasks and save results in v2 format."""
import json, yaml, time, sys
sys.path.insert(0, '.')
from core.runner import Runner
from core.evaluator import Evaluator
from core.reporter import Reporter

with open('config.yaml') as f:
    config = yaml.safe_load(f)

with open('tasks/bug_fixing.json') as f:
    tasks = json.load(f)

runner = Runner(config)
eval = Evaluator()
model_cfg = config['models'][0]

results = []
for task in tasks:
    print(f'{task["id"]}: {task["name"]}...', end=' ', flush=True)
    t0 = time.time()
    response = runner.run(model_cfg, task)
    if response is None:
        print('❌ FAIL')
        continue
    score = eval.evaluate(task, response['text'])
    elapsed = time.time() - t0
    result = {
        'model': model_cfg['name'],
        'task': 'bug_fixing',
        'case': task['name'],
        'task_id': task['id'],
        'difficulty': task.get('difficulty', 'unknown'),
        'response': response['text'],
        'response_time': round(response['elapsed'], 2),
        'total_elapsed': round(elapsed, 2),
        'prompt_tokens': response.get('prompt_tokens', 0),
        'completion_tokens': response.get('completion_tokens', 0),
        **score,
    }
    results.append(result)
    print(f'{result["resolution"]} {result["total_score"]}/100 ({elapsed:.0f}s)')

# Save
timestamp = time.strftime('%Y%m%d_%H%M%S')
with open(f'results/bench_{timestamp}.json', 'w') as f:
    json.dump(results, f, indent=2)

print(f'\n✅ {len(results)} results saved to results/bench_{timestamp}.json')
