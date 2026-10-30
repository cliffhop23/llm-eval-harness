"""Compare two evaluation runs and surface regressions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_run(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _cases_by_id(run: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {case["id"]: case for case in run.get("cases", [])}


def compare_runs(baseline: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    base_summary = baseline.get("summary", {})
    curr_summary = current.get("summary", {})
    base_cases = _cases_by_id(baseline)
    curr_cases = _cases_by_id(current)

    regressions: list[dict[str, Any]] = []
    improvements: list[dict[str, Any]] = []
    for case_id, curr in curr_cases.items():
        base = base_cases.get(case_id)
        if base is None:
            continue
        if base.get("passed") and not curr.get("passed"):
            regressions.append({"id": case_id, "type": "check_failure"})
        base_judge = base.get("judge_score")
        curr_judge = curr.get("judge_score")
        if base_judge is not None and curr_judge is not None and base_judge - curr_judge >= 0.5:
            regressions.append(
                {"id": case_id, "type": "judge_drop", "delta": curr_judge - base_judge}
            )
        if not base.get("passed") and curr.get("passed"):
            improvements.append({"id": case_id, "type": "now_passing"})

    def delta(key: str) -> float | None:
        base_value = base_summary.get(key)
        curr_value = curr_summary.get(key)
        if base_value is None or curr_value is None:
            return None
        return float(curr_value) - float(base_value)

    return {
        "baseline": baseline.get("dataset"),
        "current": current.get("dataset"),
        "pass_rate_delta": delta("checks_pass_rate"),
        "judge_delta": delta("judge_mean"),
        "latency_p95_delta_ms": delta("latency_p95_ms"),
        "regressions": regressions,
        "improvements": improvements,
        "new_cases": sorted(set(curr_cases) - set(base_cases)),
        "removed_cases": sorted(set(base_cases) - set(curr_cases)),
    }
