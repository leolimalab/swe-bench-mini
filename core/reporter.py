"""
Reporter — Generates HTML and Markdown reports from benchmark results.
"""

import json
import os
from datetime import datetime
from pathlib import Path


RESULTS_DIR = Path(__file__).parent.parent / "results"
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class Reporter:
    def __init__(self, config):
        self.config = config

    def generate(self, all_results, task_ids):
        """Generate reports from all results."""
        os.makedirs(RESULTS_DIR, exist_ok=True)

        # Save raw JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_path = RESULTS_DIR / f"bench_{timestamp}.json"
        with open(raw_path, "w") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)

        # Generate reports
        md_path = self._generate_markdown(all_results, timestamp)
        html_path = self._generate_html(all_results, timestamp)

        return {"raw": str(raw_path), "md": str(md_path), "html": str(html_path)}

    def _generate_markdown(self, results, timestamp):
        """Generate Markdown report."""
        models = sorted(set(r["model"] for r in results))
        tasks = sorted(set(r["task"] for r in results))
        task_labels = {
            "generation": "Geração",
            "bug_fixing": "Correção",
            "refactoring": "Refatoração",
        }

        lines = []
        lines.append(f"# 🧪 Swe-Bench-Mini Report")
        lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"**Tasks:** {len(results)}")
        lines.append("")

        # Summary table
        lines.append("## 📊 Summary")
        header = "| Model | " + " | ".join(
            task_labels.get(t, t) for t in tasks
        ) + " | **Total** |"
        sep = "|" + "|".join("---" for _ in range(len(tasks) + 2)) + "|"
        lines.append(header)
        lines.append(sep)

        for model in models:
            model_results = [r for r in results if r["model"] == model]
            scores = []
            for t in tasks:
                t_results = [r for r in model_results if r["task"] == t]
                avg = (
                    sum(r["total_score"] for r in t_results) / len(t_results)
                    if t_results
                    else 0
                )
                scores.append(f"{avg:.0f}")
            total_avg = (
                sum(r["total_score"] for r in model_results) / len(model_results)
                if model_results
                else 0
            )
            lines.append(f"| {model} | " + " | ".join(scores) + f" | **{total_avg:.0f}** |")

        lines.append("")

        # Detail per model
        for model in models:
            lines.append(f"## 🤖 {model}")
            model_results = [r for r in results if r["model"] == model]

            for r in model_results:
                emoji = (
                    "✅" if r["total_score"] >= 80
                    else "⚠️" if r["total_score"] >= 40
                    else "❌"
                )
                lines.append(f"\n### {emoji} {r['case']} ({r['task']})")
                lines.append(f"- **Score:** {r['total_score']}/100")
                lines.append(
                    f"- **Tests:** {r.get('tests_passed', 0)}/{r.get('tests_total', 0)}"
                )
                if r.get("exec_time"):
                    lines.append(f"- **Time:** {r['exec_time']}s")
                if r.get("error"):
                    lines.append(f"- **Error:** {r['error']}")
                if r.get("code"):
                    lines.append(f"\n```python\n{r['code']}\n```")

        md_path = RESULTS_DIR / f"report_{timestamp}.md"
        with open(md_path, "w") as f:
            f.write("\n".join(lines))
        return md_path

    def _generate_html(self, results, timestamp):
        """Generate HTML report with embedded styles."""
        models = sorted(set(r["model"] for r in results))
        tasks = sorted(set(r["task"] for r in results))
        task_labels = {
            "generation": "Geração",
            "bug_fixing": "Correção",
            "refactoring": "Refatoração",
        }

        # Build summary rows
        summary_rows = ""
        for model in models:
            model_results = [r for r in results if r["model"] == model]
            scores = []
            for t in tasks:
                t_results = [r for r in model_results if r["task"] == t]
                avg = (
                    sum(r["total_score"] for r in t_results) / len(t_results)
                    if t_results
                    else 0
                )
                scores.append(f"{avg:.0f}")
            total_avg = (
                sum(r["total_score"] for r in model_results) / len(model_results)
                if model_results
                else 0
            )
            color = "green" if total_avg >= 80 else "orange" if total_avg >= 40 else "red"
            summary_rows += (
                f"<tr><td>{model}</td>"
                + "".join(f"<td>{s}</td>" for s in scores)
                + f'<td style="color:{color};font-weight:bold">{total_avg:.0f}</td></tr>'
            )

        # Build detail rows
        detail_rows = ""
        for r in results:
            emoji = "✅" if r["total_score"] >= 80 else "⚠️" if r["total_score"] >= 40 else "❌"
            color = "green" if r["total_score"] >= 80 else "orange" if r["total_score"] >= 40 else "red"
            detail_rows += f"""
            <tr>
                <td>{r['model']}</td>
                <td>{task_labels.get(r['task'], r['task'])}</td>
                <td>{emoji} {r['case']}</td>
                <td style="color:{color};font-weight:bold">{r['total_score']}</td>
                <td>{r.get('tests_passed', 0)}/{r.get('tests_total', 0)}</td>
                <td>{r.get('exec_time', 0):.1f}s</td>
                <td>{ (r.get('error') or '—')[:50] }</td>
            </tr>"""

        html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Swe-Bench-Mini Report</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       background: #0f0f1a; color: #e0e0e0; padding: 2rem; }}
h1 {{ color: #8b5cf6; margin-bottom: 0.5rem; }}
h2 {{ color: #a78bfa; margin: 1.5rem 0 1rem; }}
p {{ color: #888; margin-bottom: 1rem; }}
table {{ width: 100%; border-collapse: collapse; margin-bottom: 2rem; }}
th, td {{ padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #1e1e2e; }}
th {{ background: #1a1a2e; color: #a78bfa; font-weight: 600; }}
tr:hover {{ background: #1a1a2e; }}
code {{ background: #1e1e2e; padding: 0.2rem 0.4rem; border-radius: 4px; font-size: 0.9em; }}
pre {{ background: #1e1e2e; padding: 1rem; border-radius: 8px; overflow-x: auto; margin: 0.5rem 0; }}
.footer {{ color: #555; font-size: 0.85rem; margin-top: 2rem; text-align: center; }}
</style>
</head>
<body>
<h1>🧪 Swe-Bench-Mini Report</h1>
<p>{datetime.now().strftime('%Y-%m-%d %H:%M')} — {len(results)} tasks</p>

<h2>📊 Summary</h2>
<table>
<thead><tr><th>Model</th>
{"".join(f'<th>{task_labels.get(t, t)}</th>' for t in tasks)}
<th><strong>Total</strong></th>
</tr></thead>
<tbody>{summary_rows}</tbody>
</table>

<h2>📋 Details</h2>
<table>
<thead><tr>
<th>Model</th><th>Task</th><th>Case</th><th>Score</th><th>Tests</th><th>Time</th><th>Error</th>
</tr></thead>
<tbody>{detail_rows}</tbody>
</table>

<div class="footer">Generated by swe-bench-mini</div>
</body>
</html>"""

        html_path = RESULTS_DIR / f"report_{timestamp}.html"
        with open(html_path, "w") as f:
            f.write(html)
        return html_path
