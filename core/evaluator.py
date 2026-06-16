"""
Evaluator v2 — F2P/P2P evaluation pipeline.

Inspired by SWE-bench (Princeton NLP):
- fail_to_pass (F2P): tests that should pass on fixed code (bug resolution)
- pass_to_pass (P2P): tests that should still pass (no regression)
- Resolution status: FULL / PARTIAL / NO / REGRESSION
- Failure categories with precedence order
"""

import ast
import json
import os
import subprocess
import sys
import tempfile
import time
import re
from pathlib import Path

from core.thinking import strip_think_tags, THINK_TAG_RE


CODE_BLOCK_RE = re.compile(
    r"```(?:python)?\s*\n(.*?)```", re.DOTALL
)

_EVAL_TMP_DIR = Path(__file__).parent.parent / ".eval_tmp"


class Evaluator:
    """Evaluates model code output using F2P/P2P methodology."""

    def evaluate(self, task, response_text):
        """Full F2P/P2P evaluation pipeline.

        Returns:
            dict with keys: code, syntax_ok, syntax_error,
            f2p_passed, f2p_total, p2p_passed, p2p_total,
            f2p_ratio, p2p_ratio, total_score,
            resolution, failure_category, exec_time, error
        """
        result = {
            "code": "",
            "syntax_ok": False,
            "syntax_error": None,
            "f2p_passed": 0,
            "f2p_total": 0,
            "p2p_passed": 0,
            "p2p_total": 0,
            "f2p_ratio": 0.0,
            "p2p_ratio": 0.0,
            "total_score": 0,
            "resolution": "NO",
            "failure_category": None,
            "exec_time": 0.0,
            "error": None,
            "hints_used": bool(task.get("hints")),
        }

        # 1) Extract code
        code = self._extract_code(response_text)
        if not code:
            result["failure_category"] = "no_code"
            result["error"] = "No code block found in response"
            return result
        result["code"] = code

        # 2) Syntax check
        syntax_ok, syntax_error = self._check_syntax(code)
        result["syntax_ok"] = syntax_ok
        result["syntax_error"] = syntax_error
        if not syntax_ok:
            result["failure_category"] = "syntax"
            result["error"] = syntax_error
            return result

        # 3) Detect evaluation mode
        f2p_asserts = task.get("fail_to_pass", [])
        p2p_asserts = task.get("pass_to_pass", [])
        mode = task.get("evaluation_mode")
        if mode is None:
            mode = "generation" if f2p_asserts == p2p_asserts else "bug_fixing"
        is_generation_mode = mode == "generation"
        f2p_p2p_identical = f2p_asserts == p2p_asserts
        timeout = task.get("timeout", 5)

        # 4) Run F2P tests
        f2p_passed, f2p_total, f2p_time, f2p_error = self._run_test_list(
            f2p_asserts, code, timeout
        )
        result["f2p_passed"] = f2p_passed
        result["f2p_total"] = f2p_total
        result["exec_time"] = round(f2p_time, 3)

        if f2p_error and f2p_error != "timeout":
            result["runtime_error"] = f2p_error

        if f2p_total > 0:
            result["f2p_ratio"] = round(f2p_passed / f2p_total, 4)
        else:
            result["f2p_ratio"] = 1.0

        # 5) Run P2P tests
        p2p_passed = 0
        p2p_total = 0
        p2p_error = None
        if is_generation_mode and f2p_p2p_identical:
            result["p2p_passed"] = f2p_passed
            result["p2p_total"] = f2p_total
            result["p2p_ratio"] = result["f2p_ratio"]
        elif is_generation_mode and p2p_asserts:
            p2p_passed, p2p_total, p2p_time, p2p_error = self._run_test_list(
                p2p_asserts, code, timeout
            )
            result["p2p_passed"] = p2p_passed
            result["p2p_total"] = p2p_total
            result["exec_time"] = round(max(result["exec_time"], p2p_time), 3)
            if p2p_total > 0:
                result["p2p_ratio"] = round(p2p_passed / p2p_total, 4)
            else:
                result["p2p_ratio"] = 1.0
        elif not is_generation_mode and p2p_asserts:
            p2p_passed, p2p_total, p2p_time, p2p_error = self._run_test_list(
                p2p_asserts, code, timeout
            )
            result["p2p_passed"] = p2p_passed
            result["p2p_total"] = p2p_total
            result["exec_time"] = round(
                max(result["exec_time"], p2p_time), 3
            )
            if p2p_total > 0:
                result["p2p_ratio"] = round(p2p_passed / p2p_total, 4)
            else:
                result["p2p_ratio"] = 1.0
        else:
            result["p2p_passed"] = 0
            result["p2p_total"] = 0
            result["p2p_ratio"] = 1.0

        # 6) Check for timeout
        if f2p_error == "timeout" or p2p_error == "timeout":
            result["failure_category"] = "timeout"
            result["error"] = "Execution timed out"
            return result

        # 7) Check for runtime error (non-AssertionError)
        runtime_err = f2p_error or p2p_error
        if runtime_err:
            result["failure_category"] = "runtime"
            result["error"] = runtime_err
            return result

        # 8) Classify failure (precedence order)
        f2p_all_pass = result["f2p_passed"] == result["f2p_total"]
        p2p_all_pass = result["p2p_passed"] == result["p2p_total"]

        if is_generation_mode:
            if f2p_all_pass and p2p_all_pass:
                result["resolution"] = "FULL"
                result["total_score"] = 100
            else:
                result["resolution"] = "NO"
                result["failure_category"] = "unresolved"
                if f2p_p2p_identical:
                    result["total_score"] = int(result["f2p_ratio"] * 60)
                else:
                    result["total_score"] = int(
                        result["f2p_ratio"] * 60 + result["p2p_ratio"] * 40
                    )
                result["error"] = "Code does not pass all tests"
        else:
            # Bug fixing mode: full F2P/P2P logic
            if not p2p_all_pass:
                # Regression has higher precedence than unresolved
                result["failure_category"] = "regression"
                result["resolution"] = "REGRESSION"
                result["total_score"] = int(
                    result["f2p_ratio"] * 60 + result["p2p_ratio"] * 40
                )
                result["error"] = "Created regression(s) — existing tests broke"
            elif not f2p_all_pass:
                if result["f2p_passed"] > 0:
                    result["resolution"] = "PARTIAL"
                    result["failure_category"] = "unresolved"
                else:
                    result["resolution"] = "NO"
                    result["failure_category"] = "unresolved"
                result["total_score"] = int(
                    result["f2p_ratio"] * 60 + result["p2p_ratio"] * 40
                )
                result["error"] = "Bug not fully resolved"
            else:
                result["resolution"] = "FULL"
                result["total_score"] = 100

        return result

    def _extract_code(self, text):
        """Extract Python code from ```python ... ``` blocks."""
        if not text:
            return None
        had_think = bool(THINK_TAG_RE.search(text))
        text = strip_think_tags(text)
        blocks = CODE_BLOCK_RE.findall(text)
        if not blocks:
            blocks = re.findall(r"```\s*\n(.*?)```", text, re.DOTALL)
        if not blocks:
            return None
        if len(blocks) > 1 and had_think:
            return blocks[-1].strip()
        return "\n".join(b.strip() for b in blocks)

    def _check_syntax(self, code):
        """Check if code has valid Python syntax."""
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            return False, str(e)

    def _run_test_list(self, asserts, code, timeout):
        """Run a list of assert statements with individual try/except wrapping.

        Each assert is wrapped so ALL execute even if some fail.
        Results are returned via JSON on stdout.

        Returns:
            (passed_count, total_count, exec_time, error_string_or_None)
        """
        if not asserts:
            return 0, 0, 0, None

        total = len(asserts)

        # Build wrapper: code + try/except for each assert
        wrapper_lines = [code, ""]
        wrapper_lines.append("_results = {}")
        for i, assert_code in enumerate(asserts):
            wrapper_lines.append(f"""
try:
    {assert_code}
    _results[{i}] = 'PASS'
except AssertionError:
    _results[{i}] = 'FAIL'
except Exception as e:
    _results[{i}] = 'ERR:' + str(e)
""")
        wrapper_lines.append("")
        wrapper_lines.append("import json")
        wrapper_lines.append("print('__RESULTS__')")
        wrapper_lines.append("print(json.dumps(_results))")
        full_code = "\n".join(wrapper_lines)

        # Write to temp file
        tmp_path = None
        try:
            _EVAL_TMP_DIR.mkdir(exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False,
                dir=str(_EVAL_TMP_DIR),
            ) as f:
                f.write(full_code)
                tmp_path = f.name

            t0 = time.time()
            result = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            exec_time = time.time() - t0

            # Parse JSON results from stdout
            results = {}
            capture = False
            for line in result.stdout.splitlines():
                if line.strip() == "__RESULTS__":
                    capture = True
                    continue
                if capture:
                    try:
                        results = json.loads(line)
                    except (json.JSONDecodeError, ValueError):
                        pass
                    break

            if not results:
                # Fallback: parse stderr for errors
                stderr = result.stderr.strip()
                if stderr:
                    return 0, total, exec_time, stderr[:500]
                return 0, total, exec_time, "Could not parse test results"

            passed = 0
            runtime_error = None
            for i in range(total):
                status = results.get(str(i), "FAIL")
                if status == "PASS":
                    passed += 1
                elif status.startswith("ERR:"):
                    if runtime_error is None:
                        runtime_error = status[4:]  # Remove 'ERR:' prefix

            os.unlink(tmp_path)
            return passed, total, exec_time, runtime_error

        except subprocess.TimeoutExpired:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            return 0, total, timeout, "timeout"
        except Exception as e:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
            return 0, total, time.time() - t0 if "t0" in locals() else 0, str(e)

    def compute_score(self, f2p_ratio, p2p_ratio):
        """Compute composite score from F2P and P2P ratios."""
        return int(f2p_ratio * 60 + p2p_ratio * 40)

    @staticmethod
    def get_resolution_status(f2p_ratio, p2p_ratio, is_generation=False):
        """Determine resolution status from ratios."""
        if is_generation:
            return "FULL" if f2p_ratio >= 1.0 else "NO"

        if f2p_ratio >= 1.0 and p2p_ratio >= 1.0:
            return "FULL"
        if p2p_ratio >= 1.0:
            return "PARTIAL" if f2p_ratio > 0 else "NO"
        return "REGRESSION"
