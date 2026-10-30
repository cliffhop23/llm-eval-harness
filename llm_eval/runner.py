"""Execute a dataset against a provider and aggregate results."""

from __future__ import annotations

import asyncio
import statistics
from datetime import UTC, datetime

from .checks import run_check
from .judges import judge_response
from .models import (
    Case,
    CaseResult,
    RunResult,
    Summary,
)
from .providers import Provider


def summarise(cases: list[CaseResult]) -> Summary:
    checks_passed = sum(1 for case in cases for check in case.checks if check.passed)
    checks_total = sum(len(case.checks) for case in cases)
    judge_scores = [case.judge_score for case in cases if case.judge_score is not None]
    latencies = sorted(case.latency_ms for case in cases)

    def percentile(values: list[float], fraction: float) -> float:
        if not values:
            return 0.0
        index = min(len(values) - 1, int(round(fraction * (len(values) - 1))))
        return values[index]

    return Summary(
        cases=len(cases),
        checks_passed=checks_passed,
        checks_total=checks_total,
        checks_pass_rate=checks_passed / checks_total if checks_total else 0.0,
        cases_pass_rate=sum(1 for case in cases if case.passed) / len(cases) if cases else 0.0,
        judge_mean=statistics.fmean(judge_scores) if judge_scores else None,
        latency_p50_ms=percentile(latencies, 0.5),
        latency_p95_ms=percentile(latencies, 0.95),
        tokens=sum(case.tokens for case in cases),
    )


async def run_dataset(
    cases: list[Case],
    provider: Provider,
    model: str,
    dataset_name: str,
    concurrency: int = 4,
) -> RunResult:
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def evaluate(case: Case) -> CaseResult:
        async with semaphore:
            completion = await provider.complete(case.prompt, model, case_id=case.id)
            result = CaseResult(
                id=case.id,
                response=completion.text,
                checks=[run_check(spec, completion.text) for spec in case.checks],
                latency_ms=completion.latency_ms,
                tokens=completion.tokens,
            )
            if case.rubric:
                score, reason = await judge_response(
                    provider, model, case.rubric, completion.text, case.id
                )
                result.judge_score = score
                result.judge_reason = reason
            return result

    results = await asyncio.gather(*(evaluate(case) for case in cases))
    return RunResult(
        provider=provider.name,
        model=model,
        dataset=dataset_name,
        started_at=datetime.now(UTC).isoformat(timespec="seconds"),
        cases=list(results),
        summary=summarise(list(results)),
    )
