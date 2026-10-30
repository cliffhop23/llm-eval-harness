"""Deterministic output checks."""

from __future__ import annotations

import json
import re

from .models import CheckResult, CheckSpec


def _json_valid(text: str) -> bool:
    try:
        json.loads(text)
        return True
    except json.JSONDecodeError:
        return False


def run_check(spec: CheckSpec, response: str) -> CheckResult:
    kind = spec.type
    value = spec.value
    text = response.strip()
    if kind == "contains":
        passed = (value or "") in response
        return CheckResult(kind, passed, "" if passed else f"missing {value!r}")
    if kind == "not_contains":
        passed = (value or "") not in response
        return CheckResult(kind, passed, "" if passed else f"unexpected {value!r}")
    if kind == "exact":
        passed = text == (value or "").strip()
        return CheckResult(kind, passed, "" if passed else f"expected {value!r}")
    if kind == "regex":
        passed = re.search(value or "", response) is not None
        return CheckResult(kind, passed, "" if passed else f"no match for {value!r}")
    if kind == "json":
        passed = _json_valid(text)
        return CheckResult(kind, passed, "" if passed else "invalid JSON")
    if kind == "max_words":
        limit = int(value or "0")
        words = len(text.split())
        passed = words <= limit
        return CheckResult(kind, passed, "" if passed else f"{words} words > {limit}")
    return CheckResult(kind, False, f"unknown check type: {kind}")
