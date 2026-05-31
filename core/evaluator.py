"""
Evaluator — Extracts code from model responses, executes tests, computes score.
"""

import ast
import tempfile
import subprocess
import sys
import time
import os
import re


CODE_BLOCK_RE = re.compile(
    r"```(?:python)?\s*\n(.*?)```", re.DOTALL
)


class Evaluator:
    """Evaluates model code output and computes a composite score (0-100)."""

    # Score weights
    W_SYNTAX = 20
    W_TESTS = 50
    W_TIME = 15
    W_QUALITY = 15

    # Quality checks
    HAS_DOCSTRING_RE = re.compile(r'""".*?"""', re.DOTALL)
    HAS_TYPE_HINTS_RE = re.compile(r":\s*\w+")
    HAS_DEF_RE = re.compile(r"def\s+\w+\s*\(")

    def evaluate(self, task, response_text):
        """Full evaluation pipeline: extract → syntax → tests → quality → score."""
        code = self._extract_code(response_text)
        if not code:
            return {
                "code": "",
                "syntax_ok": False,
                "tests_passed": 0,
                "tests_total": 0,
                "exec_time": 0,
                "has_docstring": False,
                "has_type_hints": False,
                "syntax_score": 0,
                "tests_score": 0,
                "time_score": 0,
                "quality_score": 0,
                "total_score": 0,
                "error": "No code block found in response",
            }

        # 1) Syntax check (20 pts)
        syntax_ok, syntax_error = self._check_syntax(code)
        syntax_score = self.W_SYNTAX if syntax_ok else 0

        # 2) Test execution (50 pts)
        test_code = task.get("test_code", "")
        tests_passed = 0
        tests_total = 0
        exec_time = 0
        tests_score = 0
        runtime_error = None

        if syntax_ok and test_code:
            tests_passed, tests_total, exec_time, runtime_error = self._run_tests(
                code, test_code, task.get("timeout", 5)
            )
            tests_score = (
                int(self.W_TESTS * tests_passed / tests_total)
                if tests_total > 0
                else 0
            )
        elif syntax_ok and not test_code:
            tests_score = self.W_TESTS  # auto-pass if no tests

        # 3) Time score (15 pts)
        if syntax_ok:
            threshold = task.get("timeout", 5)
            if exec_time <= threshold:
                time_score = self.W_TIME
            elif exec_time <= threshold * 2:
                time_score = int(self.W_TIME * (1 - (exec_time - threshold) / threshold))
            else:
                time_score = 0
        else:
            time_score = 0

        # 4) Quality score (15 pts)
        quality_score = self._quality_score(code) if syntax_ok else 0

        total_score = syntax_score + tests_score + time_score + quality_score

        return {
            "code": code,
            "syntax_ok": syntax_ok,
            "syntax_error": syntax_error,
            "tests_passed": tests_passed,
            "tests_total": tests_total,
            "exec_time": round(exec_time, 3),
            "runtime_error": runtime_error,
            "has_docstring": bool(self.HAS_DOCSTRING_RE.search(code)),
            "has_type_hints": bool(self.HAS_TYPE_HINTS_RE.search(code)),
            "syntax_score": syntax_score,
            "tests_score": tests_score,
            "time_score": time_score,
            "quality_score": quality_score,
            "total_score": total_score,
            "error": None,
        }

    def _extract_code(self, text):
        """Extract Python code from ```python ... ``` blocks."""
        blocks = CODE_BLOCK_RE.findall(text)
        if not blocks:
            # Try extracting any code-like block
            return None
        return "\n".join(b.strip() for b in blocks)

    def _check_syntax(self, code):
        """Check if code has valid Python syntax."""
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            return False, str(e)

    def _run_tests(self, code, test_code, timeout):
        """Write code + tests to temp file and execute with subprocess."""
        full_code = code + "\n\n" + test_code

        # Count test lines (each assert is a test)
        test_lines = [l.strip() for l in test_code.split("\n") if l.strip().startswith("assert")]
        total = len(test_lines) if test_lines else 1

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, dir=os.path.expanduser("~")
        ) as f:
            f.write(full_code)
            tmp_path = f.name

        t0 = time.time()
        try:
            result = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            exec_time = time.time() - t0

            if result.returncode == 0:
                passed = total
            else:
                # Count how many asserts passed vs failed
                stderr = result.stderr
                passed = 0
                for line in test_lines:
                    if line not in stderr:
                        passed += 1

            os.unlink(tmp_path)
            return passed, total, exec_time, None if result.returncode == 0 else result.stderr

        except subprocess.TimeoutExpired:
            os.unlink(tmp_path)
            return 0, total, timeout, "timeout"
        except Exception as e:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
            return 0, total, time.time() - t0, str(e)

    def _quality_score(self, code):
        """Assess code quality: docstrings, type hints, function definitions."""
        score = 0
        checks = 0

        # Has at least one function/class
        if self.HAS_DEF_RE.search(code):
            score += 5
        checks += 5

        # Has docstring
        if self.HAS_DOCSTRING_RE.search(code):
            score += 5
        checks += 5

        # Has type hints
        if self.HAS_TYPE_HINTS_RE.search(code):
            score += 3
        checks += 3

        # Not too many lines per function (simplicity heuristic)
        lines = code.split("\n")
        score += 2 if len(lines) < 100 else 0
        checks += 2

        return int(self.W_QUALITY * score / checks) if checks > 0 else 0
