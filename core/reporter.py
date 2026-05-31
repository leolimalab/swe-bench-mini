"""
Reporter — Generates HTML and Markdown reports from benchmark results.
Updated for F2P/P2P resolution status.
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

    def _resolution_emoji(self, resolution):
        mapping = {
            "FULL": "✅",
            "PARTIAL": "⚠️",
            "NO": "❌",
            "REGRESSION": "🔴",
        }
        return mapping.get(resolution, "❓")

    def _generate_markdown(self, results, timestamp):
        """Generate Markdown report with F2P/P2P details."""
        models = sorted(set(r["model"] for r in results))
        tasks = sorted(set(r["task"] for r in results))
        task_labels = {
            "generation": "Geração",
            "bug_fixing": "Correção",
            "refactoring": "Refatoração",
        }

        lines = []
        lines.append(f"# 🧪 Swe-Bench-Mini Report v2")
        lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"**Tasks:** {len(results)}")
        lines.append("")

        # Summary table
        lines.append("## 📊 Summary")
        header = "| Model | " + " | ".join(
            task_labels.get(t, t) for t in tasks
        ) + " | **Total** | **Resolução** |"
        sep = "|" + "|".join("---" for _ in range(len(tasks) + 3)) + "|"
        lines.append(header)
        lines.append(sep)

        for model in models:
            model_results = [r for r in results if r["model"] == model]
            scores = []
            resos = []
            for t in tasks:
                t_results = [r for r in model_results if r["task"] == t]
                avg = (
                    sum(r["total_score"] for r in t_results) / len(t_results)
                    if t_results
                    else 0
                )
                scores.append(f"{avg:.0f}")
                # Count resolutions
                full = sum(1 for r in t_results if r.get("resolution") == "FULL")
                resos.append(f"{full}/{len(t_results)}" if t_results else "-")
            total_avg = (
                sum(r["total_score"] for r in model_results) / len(model_results)
                if model_results
                else 0
            )
            total_full = sum(1 for r in model_results if r.get("resolution") == "FULL")
            lines.append(
                f"| {model} | " + " | ".join(scores)
                + f" | **{total_avg:.0f}** | **{total_full}/{len(model_results)} FULL** |"
            )

        lines.append("")

        # Detail per model
        for model in models:
            lines.append(f"## 🤖 {model}")
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
                    lines.append(f"- **Tokens:** {r.get('prompt_tokens', 0)} in / {r.get('completion_tokens', 0)} out")
                if r.get("error"):
                    lines.append(f"- **Error:** {r['error']}")
                if r.get("code"):
                    lines.append(f"\n```python\n{r['code']}\n```")

        md_path = RESULTS_DIR / f"report_{timestamp}.md"
        with open(md_path, "w") as f:
            f.write("\n".join(lines))
        return md_path

    def _generate_html(self, results, timestamp):
        """Generate HTML report with F2P/P2P columns and conditional colors."""
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
            total_full = sum(1 for r in model_results if r.get("resolution") == "FULL")
            color = "green" if total_avg >= 80 else "orange" if total_avg >= 40 else "red"
            summary_rows += (
                f"<tr><td>{model}</td>"
                + "".join(f"<td>{s}</td>" for s in scores)
                + f'<td style="color:{color};font-weight:bold">{total_avg:.0f}</td>'
                + f'<td>{total_full}/{len(model_results)} ✅</td></tr>'
            )

        # Build detail rows
        detail_rows = ""
        for r in results:
            res = r.get("resolution", "NO")
            cat = r.get("failure_category", "")
            emoji = self._resolution_emoji(res)
            score = r["total_score"]

            if res == "FULL":
                color = "green"
            elif res == "PARTIAL":
                color = "orange"
            elif res == "REGRESSION":
                color = "darkred"
            else:
                color = "red"

            f2p = f"{r.get('f2p_passed', 0)}/{r.get('f2p_total', 0)}"
            p2p = f"{r.get('p2p_passed', 0)}/{r.get('p2p_total', 0)}"
            fail_display = cat if cat else "—"
            time_display = f"{r.get('exec_time', 0):.1f}s" if r.get('exec_time') else "—"
            resp_display = f"{r.get('response_time', 0):.1f}s"

            detail_rows += f"""
            <tr>
                <td>{r['model']}</td>
                <td>{task_labels.get(r['task'], r['task'])}</td>
                <td>{emoji} {r['case']}</td>
                <td style="color:{color};font-weight:bold">{res}</td>
                <td style="color:{color};font-weight:bold">{score}</td>
                <td>{f2p}</td>
                <td>{p2p}</td>
                <td>{fail_display}</td>
                <td>{resp_display}</td>
                <td>{time_display}</td>
            </tr>"""

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
code {{ background: #1e1e2e; padding: 0.2rem 0.4rem; border-radius: 4px; font-size: 0.9em; }}
pre {{ background: #1e1e2e; padding: 1rem; border-radius: 8px; overflow-x: auto; margin: 0.5rem 0; }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; font-weight: 600; }}
.badge-full {{ background: #065f46; color: #6ee7b7; }}
.badge-partial {{ background: #78350f; color: #fcd34d; }}
.badge-no {{ background: #7f1d1d; color: #fca5a5; }}
.badge-regression {{ background: #450a0a; color: #f87171; border: 1px solid #ef4444; }}
.footer {{ color: #555; font-size: 0.85rem; margin-top: 2rem; text-align: center; }}
</style>
</head>
<body>
<h1>🧪 Swe-Bench-Mini Report v2</h1>
<p>{datetime.now().strftime('%Y-%m-%d %H:%M')} — {len(results)} tasks — F2P/P2P evaluation</p>

<h2>📊 Summary</h2>
<table>
<thead><tr><th>Model</th>
{"".join(f'<th>{task_labels.get(t, t)}</th>' for t in tasks)}
<th><strong>Total</strong></th>
<th><strong>Resolved</strong></th>
</tr></thead>
<tbody>{summary_rows}</tbody>
</table>

<h2>📋 Details</h2>
<table>
<thead><tr>
<th>Model</th><th>Category</th><th>Case</th><th>Resolution</th><th>Score</th>
<th>F2P</th><th>P2P</th><th>Failure</th><th>Response</th><th>Exec</th>
</tr></thead>
<tbody>{detail_rows}</tbody>
</table>

<div class="footer">
Generated by swe-bench-mini v2 — Resolution: ✅ FULL | ⚠️ PARTIAL | ❌ NO | 🔴 REGRESSION
</div>
</body>
</html>"""

        html_path = RESULTS_DIR / f"report_{timestamp}.html"
        with open(html_path, "w") as f:
            f.write(html)
        return html_path
