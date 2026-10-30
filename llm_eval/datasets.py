"""Load JSONL evaluation datasets."""

from __future__ import annotations

import json
from pathlib import Path

from .models import Case, CheckSpec


def load_cases(path: str | Path) -> list[Case]:
    dataset_path = Path(path)
    if not dataset_path.exists():
        raise FileNotFoundError(f"dataset not found: {dataset_path}")
    cases: list[Case] = []
    with dataset_path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{dataset_path}:{line_no}: invalid JSON ({exc})") from exc
            checks = tuple(
                CheckSpec(type=item["type"], value=item.get("value"))
                for item in raw.get("checks", [])
            )
            cases.append(
                Case(
                    id=raw["id"],
                    prompt=raw["prompt"],
                    checks=checks,
                    rubric=raw.get("rubric"),
                    mock_response=raw.get("mock_response"),
                    mock_judge=raw.get("mock_judge"),
                )
            )
    if not cases:
        raise ValueError(f"{dataset_path}: dataset is empty")
    return cases
