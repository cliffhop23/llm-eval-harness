from __future__ import annotations

from llm_eval.compare import compare_runs


def _run(passed: bool, judge: float) -> dict:
    return {
        "dataset": "d.jsonl",
        "summary": {
            "checks_pass_rate": 1.0 if passed else 0.5,
            "judge_mean": judge,
            "latency_p95_ms": 10.0,
        },
        "cases": [{"id": "case-1", "passed": passed, "judge_score": judge}],
    }


def test_regression_detected() -> None:
    diff = compare_runs(_run(True, 5.0), _run(False, 4.0))
    assert diff["regressions"]
    assert diff["regressions"][0]["id"] == "case-1"
    assert diff["pass_rate_delta"] < 0


def test_improvement_detected() -> None:
    diff = compare_runs(_run(False, 3.0), _run(True, 4.5))
    assert diff["improvements"]
    assert not diff["regressions"]
