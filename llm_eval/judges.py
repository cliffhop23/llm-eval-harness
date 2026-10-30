"""LLM-as-judge rubric scoring."""

from __future__ import annotations

import json
import re

from .models import Completion
from .providers import Provider

JUDGE_PROMPT = """You are a strict evaluator of assistant responses.

Rubric:
{rubric}

Response:
{response}

Score the response from 1 to 5 against the rubric. Return ONLY a JSON object:
{{"score": <integer 1-5>, "reason": "<one short sentence>"}}"""

_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


def parse_judge(text: str) -> tuple[float | None, str]:
    match = _JSON_BLOCK.search(text)
    if match is None:
        return None, "judge did not return JSON"
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None, "judge JSON was invalid"
    try:
        score = float(data["score"])
    except (KeyError, TypeError, ValueError):
        return None, "judge JSON missing a numeric score"
    return max(1.0, min(5.0, score)), str(data.get("reason", ""))


async def judge_response(
    provider: Provider, model: str, rubric: str, response: str, case_id: str
) -> tuple[float | None, str]:
    prompt = JUDGE_PROMPT.format(rubric=rubric, response=response)
    completion: Completion = await provider.complete(
        prompt, model, case_id=f"{case_id}:judge"
    )
    return parse_judge(completion.text)
