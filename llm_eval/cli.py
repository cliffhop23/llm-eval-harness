"""Command-line interface: run evaluations, compare runs, scaffold datasets."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .compare import compare_runs, load_run
from .datasets import load_cases
from .providers import MockProvider, OpenAICompatProvider, Provider
from .report import write_reports
from .runner import run_dataset

app = typer.Typer(add_completion=False, help="Evaluate LLM outputs and gate regressions.")


def _console() -> Console:
    return Console()

SAMPLE_DATASET = """\
{"id":"late-order","prompt":"Customer says: 'Hi, my order #A123 is late.' Write one concise, empathetic sentence that mentions the order and offers a tracking link.","checks":[{"type":"contains","value":"A123"},{"type":"contains","value":"track"},{"type":"max_words","value":"40"}],"rubric":"Empathetic tone, mentions the order number, offers a next step, concise.","mock_response":"Sorry about the delay with order A123 — here is your tracking link: https://example.com/track/A123","mock_judge":{"score":5,"reason":"Empathetic, specific, and offers tracking."}}
{"id":"refund-policy","prompt":"Answer in one sentence: what is the refund window for physical products?","checks":[{"type":"contains","value":"30 days"},{"type":"max_words","value":"30"},{"type":"not_contains","value":"lifetime"}],"rubric":"Correct, concise, no invented policy details.","mock_response":"Physical products can be returned within 30 days of delivery for a refund.","mock_judge":{"score":5,"reason":"Direct, correct, concise."}}
"""


def _build_provider(kind: str, base_url: str, api_key_env: str, cases) -> Provider:
    if kind == "mock":
        return MockProvider.from_cases(cases)
    if kind in {"openai", "compat"}:
        api_key = os.getenv(api_key_env, "")
        return OpenAICompatProvider(base_url=base_url, api_key=api_key)
    raise typer.BadParameter("provider must be 'mock' or 'openai'")


def _summary_table(result, min_pass_rate: float, min_judge: float) -> Table:
    summary = result.summary
    judge = f"{summary.judge_mean:.2f} / 5" if summary.judge_mean is not None else "n/a"
    table = Table(title="Evaluation summary", show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    table.add_row("Cases", str(summary.cases))
    table.add_row("Check pass rate", f"{summary.checks_pass_rate:.1%}")
    table.add_row("Cases fully passing", f"{summary.cases_pass_rate:.1%}")
    table.add_row("Mean judge score", judge)
    table.add_row(
        "Latency p50 / p95",
        f"{summary.latency_p50_ms:.0f} / {summary.latency_p95_ms:.0f} ms",
    )
    table.add_row("Tokens", str(summary.tokens))
    table.add_row("Gate (pass rate)", f">= {min_pass_rate:.0%}")
    if min_judge:
        table.add_row("Gate (judge)", f">= {min_judge:.2f}")
    return table


@app.command()
def run(
    dataset: Path = typer.Option(..., "--dataset", "-d", exists=True, help="JSONL dataset"),
    provider: str = typer.Option("mock", help="mock or openai (OpenAI-compatible)"),
    model: str = typer.Option("mock-1", help="Model name passed to the provider"),
    base_url: str = typer.Option("https://api.openai.com/v1", help="OpenAI-compatible base URL"),
    api_key_env: str = typer.Option("OPENAI_API_KEY", help="Env var holding the API key"),
    out: Path = typer.Option(Path("reports/run.json"), help="JSON report path"),
    html: Path | None = typer.Option(None, help="Optional HTML report path"),
    markdown: Path | None = typer.Option(None, help="Optional Markdown report path"),
    min_pass_rate: float = typer.Option(0.0, help="Fail if check pass rate is below this"),
    min_judge: float = typer.Option(0.0, help="Fail if mean judge score is below this"),
    concurrency: int = typer.Option(4, min=1, max=32, help="Concurrent requests"),
) -> None:
    """Run a dataset against a provider and write reports."""
    cases = load_cases(dataset)
    evaluator = _build_provider(provider, base_url, api_key_env, cases)
    result = asyncio.run(run_dataset(cases, evaluator, model, dataset.name, concurrency))
    paths = write_reports(result, out, html_path=html, markdown_path=markdown)
    _console().print(_summary_table(result, min_pass_rate, min_judge))
    _console().print("Reports: " + ", ".join(str(path) for path in paths))

    failures: list[str] = []
    if result.summary.checks_pass_rate < min_pass_rate:
        failures.append(
            f"check pass rate {result.summary.checks_pass_rate:.1%} < {min_pass_rate:.0%}"
        )
    if (
        min_judge
        and result.summary.judge_mean is not None
        and result.summary.judge_mean < min_judge
    ):
        failures.append(f"judge mean {result.summary.judge_mean:.2f} < {min_judge:.2f}")
    if failures:
        _console().print("[red]Gate failed:[/red] " + "; ".join(failures))
        raise typer.Exit(code=1)
    _console().print("[green]Gate passed[/green]")


@app.command()
def compare(
    baseline: Path = typer.Argument(..., exists=True),
    current: Path = typer.Argument(..., exists=True),
) -> None:
    """Compare two JSON runs and report deltas and regressions."""
    diff = compare_runs(load_run(baseline), load_run(current))
    table = Table(title="Run comparison")
    table.add_column("Metric", style="cyan")
    table.add_column("Delta", justify="right")
    for key, label in (
        ("pass_rate_delta", "Check pass rate"),
        ("judge_delta", "Mean judge score"),
        ("latency_p95_delta_ms", "Latency p95 (ms)"),
    ):
        value = diff[key]
        table.add_row(label, "n/a" if value is None else f"{value:+.3f}")
    _console().print(table)
    if diff["regressions"]:
        _console().print("[red]Regressions:[/red]")
        for item in diff["regressions"]:
            _console().print(f"  - {item['id']}: {item['type']}")
    else:
        _console().print("[green]No regressions[/green]")
    if diff["improvements"]:
        _console().print("Improvements: " + ", ".join(item["id"] for item in diff["improvements"]))
    if diff["new_cases"]:
        _console().print("New cases: " + ", ".join(diff["new_cases"]))


@app.command()
def init(
    directory: Path = typer.Option(Path("datasets"), help="Directory for the sample dataset"),
    force: bool = typer.Option(False, help="Overwrite an existing sample dataset"),
) -> None:
    """Write a sample dataset that works with the mock provider."""
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / "support_qa.jsonl"
    if target.exists() and not force:
        _console().print(f"[yellow]Already exists:[/yellow] {target} (use --force to overwrite)")
        raise typer.Exit(code=1)
    target.write_text(SAMPLE_DATASET, encoding="utf-8")
    _console().print(f"Wrote {target}")


if __name__ == "__main__":
    app()
