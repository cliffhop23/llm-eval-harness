"""Core data structures for evaluation runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CheckSpec:
    type: str
    value: str | None = None


@dataclass(frozen=True)
class Case:
    id: str
    prompt: str
    checks: tuple[CheckSpec, ...] = ()
    rubric: str | None = None
    mock_response: str | None = None
    mock_judge: dict[str, Any] | None = None


@dataclass(frozen=True)
class Completion:
    text: str
    latency_ms: float
    tokens: int


@dataclass
class CheckResult:
    type: str
    passed: bool
    detail: str = ""


@dataclass
class CaseResult:
    id: str
    response: str
    checks: list[CheckResult] = field(default_factory=list)
    judge_score: float | None = None
    judge_reason: str = ""
    latency_ms: float = 0.0
    tokens: int = 0

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)


@dataclass
class Summary:
    cases: int
    checks_passed: int
    checks_total: int
    checks_pass_rate: float
    cases_pass_rate: float
    judge_mean: float | None
    latency_p50_ms: float
    latency_p95_ms: float
    tokens: int


@dataclass
class RunResult:
    provider: str
    model: str
    dataset: str
    started_at: str
    cases: list[CaseResult]
    summary: Summary

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "dataset": self.dataset,
            "started_at": self.started_at,
            "summary": self.summary.__dict__,
            "cases": [
                {
                    "id": case.id,
                    "response": case.response,
                    "passed": case.passed,
                    "checks": [check.__dict__ for check in case.checks],
                    "judge_score": case.judge_score,
                    "judge_reason": case.judge_reason,
                    "latency_ms": case.latency_ms,
                    "tokens": case.tokens,
                }
                for case in self.cases
            ],
        }
