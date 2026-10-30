from __future__ import annotations

import asyncio
from pathlib import Path

from llm_eval.datasets import load_cases
from llm_eval.providers import MockProvider
from llm_eval.runner import run_dataset

DATASET = Path(__file__).resolve().parents[1] / "datasets" / "support_qa.jsonl"


def test_mock_run_passes_and_scores() -> None:
    cases = load_cases(DATASET)
    provider = MockProvider.from_cases(cases)
    result = asyncio.run(run_dataset(cases, provider, "mock-1", DATASET.name))
    assert result.summary.cases == len(cases)
    assert result.summary.checks_pass_rate == 1.0
    assert result.summary.cases_pass_rate == 1.0
    assert result.summary.judge_mean is not None
    assert result.summary.judge_mean >= 4.0
    assert result.summary.tokens > 0
    assert all(case.passed for case in result.cases)
