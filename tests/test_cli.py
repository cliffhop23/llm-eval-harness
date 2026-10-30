from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from llm_eval.cli import app

DATASET = Path(__file__).resolve().parents[1] / "datasets" / "support_qa.jsonl"
runner = CliRunner()


def test_run_command_writes_reports(tmp_path) -> None:
    out = tmp_path / "run.json"
    html = tmp_path / "run.html"
    result = runner.invoke(
        app,
        ["run", "--dataset", str(DATASET), "--out", str(out), "--html", str(html)],
    )
    assert result.exit_code == 0, result.output
    assert out.exists() and html.exists()
    assert "Evaluation summary" in result.output


def test_gate_failure_returns_nonzero(tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "run",
            "--dataset",
            str(DATASET),
            "--out",
            str(tmp_path / "run.json"),
            "--min-pass-rate",
            "1.01",
        ],
    )
    assert result.exit_code == 1
    assert "Gate failed" in result.output


def test_init_and_compare(tmp_path) -> None:
    init = runner.invoke(app, ["init", "--directory", str(tmp_path)])
    assert init.exit_code == 0
    dataset = tmp_path / "support_qa.jsonl"
    assert dataset.exists()

    out = tmp_path / "run.json"
    run = runner.invoke(app, ["run", "--dataset", str(dataset), "--out", str(out)])
    assert run.exit_code == 0, run.output

    compare = runner.invoke(app, ["compare", str(out), str(out)])
    assert compare.exit_code == 0
    assert "No regressions" in compare.output
