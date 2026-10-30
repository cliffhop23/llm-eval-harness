"""Model providers: a deterministic mock and an OpenAI-compatible HTTP client."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Protocol

import httpx

from .models import Case, Completion


class Provider(Protocol):
    """Anything that can turn a prompt into a completion."""

    name: str

    async def complete(
        self, prompt: str, model: str, *, case_id: str | None = None
    ) -> Completion: ...


class MockProvider:
    """Deterministic provider used by tests, demos, and CI (no API key needed)."""

    name = "mock"

    def __init__(self, responses: dict[str, str] | None = None) -> None:
        self.responses = responses or {}

    @classmethod
    def from_cases(cls, cases: list[Case]) -> MockProvider:
        responses: dict[str, str] = {}
        for case in cases:
            responses[case.id] = case.mock_response or f"mock response for {case.id}"
            if case.mock_judge is not None:
                responses[f"{case.id}:judge"] = json.dumps(case.mock_judge)
        return cls(responses)

    async def complete(
        self, prompt: str, model: str, *, case_id: str | None = None
    ) -> Completion:
        started = time.monotonic()
        await asyncio.sleep(0.005)
        text = self.responses.get(case_id or "", f"mock response: {prompt[:40]}")
        return Completion(
            text=text,
            latency_ms=(time.monotonic() - started) * 1000,
            tokens=max(1, len(text) // 4),
        )


class OpenAICompatProvider:
    """Provider for OpenAI-compatible `/chat/completions` endpoints
    (OpenAI, DeepSeek, Ollama, vLLM).
    """

    name = "openai"

    def __init__(self, base_url: str, api_key: str = "", timeout: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    async def complete(
        self, prompt: str, model: str, *, case_id: str | None = None
    ) -> Completion:
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
        started = time.monotonic()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.base_url}/chat/completions"
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        latency_ms = (time.monotonic() - started) * 1000
        text = data["choices"][0]["message"].get("content") or ""
        usage = data.get("usage") or {}
        return Completion(
            text=text,
            latency_ms=latency_ms,
            tokens=int(usage.get("total_tokens") or 0),
        )
