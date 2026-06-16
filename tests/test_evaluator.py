"""Unit tests for core.evaluator.Evaluator."""

import unittest

from core.evaluator import Evaluator


def _gen_task(f2p, p2p=None, **kwargs):
    p2p = p2p if p2p is not None else f2p
    return {
        "id": "test",
        "fail_to_pass": f2p,
        "pass_to_pass": p2p,
        **kwargs,
    }


class TestEvaluator(unittest.TestCase):
    def setUp(self):
        self.evaluator = Evaluator()

    def test_no_code_block(self):
        result = self.evaluator.evaluate(_gen_task(["assert True"]), "no code here")
        self.assertEqual(result["failure_category"], "no_code")
        self.assertEqual(result["resolution"], "NO")

    def test_syntax_error(self):
        response = "```python\ndef foo(\n```"
        result = self.evaluator.evaluate(_gen_task(["assert True"]), response)
        self.assertEqual(result["failure_category"], "syntax")
        self.assertFalse(result["syntax_ok"])

    def test_generation_full(self):
        code = "```python\ndef add(a, b):\n    return a + b\n```"
        task = _gen_task(["assert add(1, 2) == 3", "assert add(0, 0) == 0"])
        result = self.evaluator.evaluate(task, code)
        self.assertEqual(result["resolution"], "FULL")
        self.assertEqual(result["total_score"], 100)

    def test_generation_partial(self):
        code = "```python\ndef add(a, b):\n    return a + b\n```"
        task = _gen_task(
            ["assert add(1, 2) == 3", "assert add(0, 0) == 99"],
        )
        result = self.evaluator.evaluate(task, code)
        self.assertEqual(result["resolution"], "NO")
        self.assertEqual(result["failure_category"], "unresolved")
        self.assertEqual(result["f2p_passed"], 1)
        self.assertEqual(result["f2p_total"], 2)
        self.assertEqual(result["total_score"], 30)

    def test_bug_fixing_regression(self):
        code = "```python\ndef validate(x):\n    return True\n```"
        task = _gen_task(
            ["assert validate(1) == True"],
            ["assert validate(-1) == False"],
        )
        result = self.evaluator.evaluate(task, code)
        self.assertEqual(result["resolution"], "REGRESSION")
        self.assertEqual(result["failure_category"], "regression")

    def test_bug_fixing_partial(self):
        code = "```python\ndef validate(x):\n    return x > 0\n```"
        task = _gen_task(
            ["assert validate(1) == True", "assert validate(0) == True"],
            ["assert validate(-1) == False"],
        )
        result = self.evaluator.evaluate(task, code)
        self.assertEqual(result["resolution"], "PARTIAL")
        self.assertEqual(result["failure_category"], "unresolved")

    def test_extract_multiple_blocks(self):
        text = (
            "Here is helper:\n```python\nx = 1\n```\n"
            "And main:\n```python\ndef foo():\n    return x\n```"
        )
        code = self.evaluator._extract_code(text)
        self.assertIn("x = 1", code)
        self.assertIn("def foo():", code)

    def test_timeout(self):
        code = "```python\nimport time\ntime.sleep(10)\n```"
        task = _gen_task(["assert True"], timeout=1)
        result = self.evaluator.evaluate(task, code)
        self.assertEqual(result["failure_category"], "timeout")

    def test_evaluation_mode_generation_explicit(self):
        """SQL-style task: F2P != P2P but generation mode — no REGRESSION."""
        code = "```python\ndef f():\n    return 1\n```"
        task = _gen_task(
            ["assert f() == 1"],
            ["assert f() == 99"],
            evaluation_mode="generation",
        )
        result = self.evaluator.evaluate(task, code)
        self.assertEqual(result["resolution"], "NO")
        self.assertNotEqual(result["failure_category"], "regression")
        self.assertEqual(result["failure_category"], "unresolved")

    def test_thinking_tags_uses_last_code_block(self):
        o, c = "<" + "think>", "</" + "think>"
        text = (
            f"Let me think...\n{o}\nDraft\n```python\nx = 0\n```\n{c}\n"
            "Final:\n```python\ndef foo():\n    return 1\n```"
        )
        code = self.evaluator._extract_code(text)
        self.assertIn("def foo():", code)
        self.assertNotIn("x = 0", code)

    def test_runtime_error(self):
        code = "```python\ndef boom():\n    raise ValueError('fail')\n```"
        task = _gen_task(["assert boom() == 1"])
        result = self.evaluator.evaluate(task, code)
        self.assertEqual(result["failure_category"], "runtime")


if __name__ == "__main__":
    unittest.main()
