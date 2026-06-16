"""
Reporter — Generates HTML, Markdown, CSV reports and run comparisons.
Updated for F2P/P2P resolution status.
"""

import csv
import json
import os
from collections import Counter
from datetime import datetime
from pathlib import Path


RESULTS_DIR = Path(__file__).parent.parent / "results"

TASK_LABELS = {
    "generation": "Geração",
    "bug_fixing": "Correção",
    "refactoring": "Refatoração",
    "sql": "SQL (BigQuery)",
    "data_processing": "Data Processing",
}


class Reporter:
    def __init__(self, config):
        self.config = config

    def generate(self, all_results, task_ids):
        """Generate reports from all results."""
        os.makedirs(RESULTS_DIR, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_path = RESULTS_DIR / f"bench_{timestamp}.json"
        with open(raw_path, "w") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)

        md_path = self._generate_markdown(all_results, timestamp)
        html_path = self._generate_html(all_results, timestamp)
        csv_path = self._generate_csv(all_results, timestamp)

        return {
            "raw": str(raw_path),
            "md": str(md_path),
            "html": str(html_path),
            "csv": str(csv_path),
        }

    def compare(self, baseline, current, baseline_label="", current_label=""):
        """Generate a comparison report between two runs."""
        os.makedirs(RESULTS_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        base_map = {task_key(r): r for r in baseline}
        curr_map = {task_key(r): r for r in current}
        all_keys = sorted(set(base_map) | set(curr_map))

        lines = []
        lines.append("# Swe-Bench-Mini — Run Comparison")
        lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"**Baseline:** {baseline_label or 'baseline'}")
        lines.append(f"**Current:** {current_label or 'current'}")
        lines.append("")

        improved, regressed, unchanged, new_tasks, removed = [], [], [], [], []

        lines.append("| Task | Model | Baseline | Current | Delta |")
        lines.append("|------|-------|----------|---------|-------|")

        for key in all_keys:
            b = base_map.get(key)
            c = curr_map.get(key)
            if b and not c:
                removed.append(key)
                continue
            if c and not b:
                new_tasks.append(key)
                lines.append(
                    f"| {c['task_id']} | {c['model']} | — | "
                    f"{c.get('resolution', 'NO')} {c['total_score']}/100 | NEW |"
                )
                continue

            b_score = b["total_score"]
            c_score = c["total_score"]
            b_res = b.get("resolution", "NO")
            c_res = c.get("resolution", "NO")
            delta = c_score - b_score
            delta_str = f"+{delta}" if delta > 0 else str(delta)

            if c_score > b_score:
                improved.append(key)
            elif c_score < b_score:
                regressed.append(key)
            else:
                unchanged.append(key)

            marker = ""
            if c_score > b_score:
                marker = " ⬆️"
            elif c_score < b_score:
                marker = " ⬇️"

            lines.append(
                f"| {c['task_id']} | {c['model']} | {b_res} {b_score}/100 | "
                f"{c_res} {c_score}/100 | {delta_str}{marker} |"
            )

        lines.append("")
        lines.append("## Summary")
        lines.append(f"- Improved: {len(improved)}")
        lines.append(f"- Regressed: {len(regressed)}")
        lines.append(f"- Unchanged: {len(unchanged)}")
        lines.append(f"- New tasks: {len(new_tasks)}")
        lines.append(f"- Removed: {len(removed)}")

        def _avg(results):
            return sum(r["total_score"] for r in results) / len(results) if results else 0

        def _full_count(results):
            return sum(1 for r in results if r.get("resolution") == "FULL")

        lines.append(f"- Baseline avg: {_avg(baseline):.1f}/100 ({_full_count(baseline)}/{len(baseline)} FULL)")
        lines.append(f"- Current avg: {_avg(current):.1f}/100 ({_full_count(current)}/{len(current)} FULL)")

        out_path = RESULTS_DIR / f"compare_{timestamp}.md"
        with open(out_path, "w") as f:
            f.write("\n".join(lines))
        return out_path

    def _resolution_emoji(self, resolution):
        mapping = {
            "FULL": "✅",
            "PARTIAL": "⚠️",
            "NO": "❌",
            "REGRESSION": "🔴",
        }
        return mapping.get(resolution, "❓")

    def _difficulty_stats(self, results):
        stats = {}
        for diff in ("easy", "medium", "hard"):
            subset = [r for r in results if r.get("difficulty") == diff]
            if not subset:
                continue
            stats[diff] = {
                "count": len(subset),
                "avg": sum(r["total_score"] for r in subset) / len(subset),
                "full": sum(1 for r in subset if r.get("resolution") == "FULL"),
            }
        return stats

    def _failure_stats(self, results):
        failed = [r for r in results if r.get("resolution") != "FULL"]
        return Counter(r.get("failure_category") or "unknown" for r in failed)

    def _generate_csv(self, results, timestamp):
        csv_path = RESULTS_DIR / f"report_{timestamp}.csv"
        fields = [
            "model", "task", "task_id", "case", "difficulty", "resolution",
            "total_score", "f2p_passed", "f2p_total", "p2p_passed", "p2p_total",
            "failure_category", "response_time", "exec_time",
            "prompt_tokens", "completion_tokens",
        ]
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for r in results:
                writer.writerow(r)
        return csv_path

    def _generate_markdown(self, results, timestamp):
        models = sorted(set(r["model"] for r in results))
        tasks = sorted(set(r["task"] for r in results))

        lines = []
        lines.append("# Swe-Bench-Mini Report v2")
        lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"**Tasks:** {len(results)}")
        lines.append("")

        lines.append("## Summary")
        header = "| Model | " + " | ".join(
            TASK_LABELS.get(t, t) for t in tasks
        ) + " | **Total** | **Resolução** |"
        sep = "|" + "|".join("---" for _ in range(len(tasks) + 3)) + "|"
        lines.append(header)
        lines.append(sep)

        for model in models:
            model_results = [r for r in results if r["model"] == model]
            scores = []
            for t in tasks:
                t_results = [r for r in model_results if r["task"] == t]
                avg = (
                    sum(r["total_score"] for r in t_results) / len(t_results)
                    if t_results else 0
                )
                scores.append(f"{avg:.0f}")
            total_avg = (
                sum(r["total_score"] for r in model_results) / len(model_results)
                if model_results else 0
            )
            total_full = sum(1 for r in model_results if r.get("resolution") == "FULL")
            lines.append(
                f"| {model} | " + " | ".join(scores)
                + f" | **{total_avg:.0f}** | **{total_full}/{len(model_results)} FULL** |"
            )

        lines.append("")

        for model in models:
            lines.append(f"## {model}")
            model_results = [r for r in results if r["model"] == model]
            for r in model_results:
                emoji = self._resolution_emoji(r.get("resolution", "NO"))
                lines.append(f"\n### {emoji} {r['case']} ({r['task']})")
                lines.append(f"- **Resolution:** {r.get('resolution', 'NO')}")
                lines.append(f"- **Score:** {r['total_score']}/100")
                lines.append(f"- **F2P:** {r.get('f2p_passed', 0)}/{r.get('f2p_total', 0)}")
                lines.append(f"- **P2P:** {r.get('p2p_passed', 0)}/{r.get('p2p_total', 0)}")
                if r.get("failure_category"):
                    lines.append(f"- **Failure:** {r['failure_category']}")
                if r.get("exec_time"):
                    lines.append(f"- **Time:** {r['exec_time']}s")
                if r.get("response_time"):
                    lines.append(f"- **Response:** {r['response_time']}s")
                if r.get("prompt_tokens"):
                    lines.append(
                        f"- **Tokens:** {r.get('prompt_tokens', 0)} in / "
                        f"{r.get('completion_tokens', 0)} out"
                    )
                if r.get("error"):
                    lines.append(f"- **Error:** {r['error']}")
                if r.get("code"):
                    lines.append(f"\n```python\n{r['code']}\n```")

        md_path = RESULTS_DIR / f"report_{timestamp}.md"
        with open(md_path, "w") as f:
            f.write("\n".join(lines))
        return md_path

    def _generate_html(self, results, timestamp):
        models = sorted(set(r["model"] for r in results))
        tasks = sorted(set(r["task"] for r in results))
        diff_stats = self._difficulty_stats(results)
        fail_stats = self._failure_stats(results)

        summary_rows = ""
        for model in models:
            model_results = [r for r in results if r["model"] == model]
            scores = []
            for t in tasks:
                t_results = [r for r in model_results if r["task"] == t]
                avg = (
                    sum(r["total_score"] for r in t_results) / len(t_results)
                    if t_results else 0
                )
                scores.append(f"{avg:.0f}")
            total_avg = (
                sum(r["total_score"] for r in model_results) / len(model_results)
                if model_results else 0
            )
            total_full = sum(1 for r in model_results if r.get("resolution") == "FULL")
            color = "green" if total_avg >= 80 else "orange" if total_avg >= 40 else "red"
            summary_rows += (
                f"<tr><td>{model}</td>"
                + "".join(f"<td>{s}</td>" for s in scores)
                + f'<td style="color:{color};font-weight:bold">{total_avg:.0f}</td>'
                + f"<td>{total_full}/{len(model_results)} FULL</td></tr>"
            )

        detail_rows = ""
        for r in results:
            res = r.get("resolution", "NO")
            cat = r.get("failure_category", "")
            emoji = self._resolution_emoji(res)
            score = r["total_score"]
            color = {"FULL": "green", "PARTIAL": "orange", "REGRESSION": "darkred"}.get(res, "red")
            f2p = f"{r.get('f2p_passed', 0)}/{r.get('f2p_total', 0)}"
            p2p = f"{r.get('p2p_passed', 0)}/{r.get('p2p_total', 0)}"
            fail_display = cat if cat else "—"
            time_display = f"{r.get('exec_time', 0):.1f}s" if r.get("exec_time") else "—"
            resp_display = f"{r.get('response_time', 0):.1f}s"
            detail_rows += f"""
            <tr>
                <td>{r['model']}</td>
                <td>{TASK_LABELS.get(r['task'], r['task'])}</td>
                <td>{emoji} {r['case']}</td>
                <td>{r.get('difficulty', '—')}</td>
                <td style="color:{color};font-weight:bold">{res}</td>
                <td style="color:{color};font-weight:bold">{score}</td>
                <td>{f2p}</td>
                <td>{p2p}</td>
                <td>{fail_display}</td>
                <td>{resp_display}</td>
                <td>{time_display}</td>
            </tr>"""

        diff_rows = ""
        max_avg = max((s["avg"] for s in diff_stats.values()), default=100) or 100
        for diff, s in diff_stats.items():
            bar_w = int(s["avg"] / max_avg * 200)
            diff_rows += (
                f"<tr><td>{diff}</td><td>{s['count']}</td>"
                f"<td>{s['avg']:.0f}/100</td>"
                f"<td>{s['full']}/{s['count']} FULL</td>"
                f'<td><svg width="210" height="16"><rect x="0" y="2" width="{bar_w}" '
                f'height="12" fill="#8b5cf6" rx="2"/></svg></td></tr>'
            )

        fail_rows = ""
        for cat, count in fail_stats.most_common():
            fail_rows += f"<tr><td>{cat}</td><td>{count}</td></tr>"

        html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Swe-Bench-Mini Report v2</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       background: #0f0f1a; color: #e0e0e0; padding: 2rem; }}
h1 {{ color: #8b5cf6; margin-bottom: 0.5rem; }}
h2 {{ color: #a78bfa; margin: 1.5rem 0 1rem; }}
p {{ color: #888; margin-bottom: 1rem; }}
table {{ width: 100%; border-collapse: collapse; margin-bottom: 2rem; }}
th, td {{ padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #1e1e2e; }}
th {{ background: #1a1a2e; color: #a78bfa; font-weight: 600; white-space: nowrap; }}
tr:hover {{ background: #1a1a2e; }}
.footer {{ color: #555; font-size: 0.85rem; margin-top: 2rem; text-align: center; }}
</style>
</head>
<body>
<h1>Swe-Bench-Mini Report v2</h1>
<p>{datetime.now().strftime('%Y-%m-%d %H:%M')} — {len(results)} tasks — F2P/P2P evaluation</p>

<h2>Summary</h2>
<table>
<thead><tr><th>Model</th>
{"".join(f'<th>{TASK_LABELS.get(t, t)}</th>' for t in tasks)}
<th><strong>Total</strong></th>
<th><strong>Resolved</strong></th>
</tr></thead>
<tbody>{summary_rows}</tbody>
</table>

<h2>By Difficulty</h2>
<table>
<thead><tr><th>Difficulty</th><th>Tasks</th><th>Avg Score</th><th>FULL</th><th>Chart</th></tr></thead>
<tbody>{diff_rows or '<tr><td colspan="5">No data</td></tr>'}</tbody>
</table>

<h2>Failure Categories</h2>
<table>
<thead><tr><th>Category</th><th>Count</th></tr></thead>
<tbody>{fail_rows or '<tr><td colspan="2">No failures</td></tr>'}</tbody>
</table>

<h2>Details</h2>
<table>
<thead><tr>
<th>Model</th><th>Category</th><th>Case</th><th>Difficulty</th>
<th>Resolution</th><th>Score</th>
<th>F2P</th><th>P2P</th><th>Failure</th><th>Response</th><th>Exec</th>
</tr></thead>
<tbody>{detail_rows}</tbody>
</table>

<div class="footer">
Generated by swe-bench-mini v2 — FULL | PARTIAL | NO | REGRESSION
</div>
</body>
</html>"""

        html_path = RESULTS_DIR / f"report_{timestamp}.html"
        with open(html_path, "w") as f:
            f.write(html)
        return html_path


def task_key(r):
    return f"{r['model']}::{r['task_id']}"
