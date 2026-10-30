from __future__ import annotations

import pytest

from llm_eval.checks import run_check
from llm_eval.models import CheckSpec


@pytest.mark.parametrize(
    ("spec", "response", "passed"),
    [
        (CheckSpec("contains", "A123"), "order A123 is late", True),
        (CheckSpec("contains", "A999"), "order A123 is late", False),
        (CheckSpec("not_contains", "lifetime"), "30 days", True),
        (CheckSpec("not_contains", "30 days"), "30 days", False),
        (CheckSpec("exact", "201"), "201", True),
        (CheckSpec("exact", "201"), "201 Created", False),
        (CheckSpec("regex", r"^\d{3}$"), "201", True),
        (CheckSpec("regex", r"^\d{3}$"), "abc", False),
        (CheckSpec("json"), '{"a": 1}', True),
        (CheckSpec("json"), "not json", False),
        (CheckSpec("max_words", "3"), "one two three", True),
        (CheckSpec("max_words", "2"), "one two three", False),
        (CheckSpec("unknown"), "x", False),
    ],
)
def test_checks(spec: CheckSpec, response: str, passed: bool) -> None:
    assert run_check(spec, response).passed is passed
