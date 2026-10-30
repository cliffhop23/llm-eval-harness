"""JSON, Markdown, and standalone HTML reports."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

from .models import RunResult


def write_json(result: RunResult, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result.to_dict(), indent=2) + "\n", encoding="utf-8")
    return output


def to_markdown(result: RunResult) -> str:
    summary = result.summary
    judge = f"{summary.judge_mean:.2f} / 5" if summary.judge_mean is not None else "n/a"
    lines = [
        f"# Evaluation: {result.dataset}",
        "",
        f"**Provider:** `{result.provider}` · **Model:** `{result.model}` · "
        f"**Started:** {result.started_at}",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Cases | {summary.cases} |",
        f"| Check pass rate | {summary.checks_pass_rate:.1%} |",
        f"| Cases fully passing | {summary.cases_pass_rate:.1%} |",
        f"| Mean judge score | {judge} |",
        f"| Latency p50 / p95 | {summary.latency_p50_ms:.0f} / {summary.latency_p95_ms:.0f} ms |",
        f"| Tokens | {summary.tokens} |",
        "",
        "| Case | Checks | Judge | Latency |",
        "|---|---|---|---|",
    ]
    for case in result.cases:
        mark = "PASS" if case.passed else "FAIL"
        judge_value = f"{case.judge_score:.0f}" if case.judge_score is not None else "-"
        lines.append(
            f"| `{case.id}` | {mark} | {judge_value} | {case.latency_ms:.0f} ms |"
        )
    lines.append("")
    return "\n".join(lines)


def to_html(result: RunResult) -> str:
    summary = result.summary
    judge = f"{summary.judge_mean:.2f} / 5" if summary.judge_mean is not None else "n/a"
    rows = []
    for case in result.cases:
        status = "pass" if case.passed else "fail"
        failed = [check.type for check in case.checks if not check.passed]
        detail = escape(", ".join(failed)) if failed else "all checks passed"
        judge_value = f"{case.judge_score:.0f}" if case.judge_score is not None else "-"
        rows.append(
            f"<tr class='{status}'><td><code>{escape(case.id)}</code></td>"
            f"<td>{status.upper()}</td><td>{escape(detail)}</td>"
            f"<td>{judge_value}</td><td>{case.latency_ms:.0f} ms</td></tr>"
        )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Evaluation: {escape(result.dataset)}</title>
<style>
  :root {{ --pass:#3fb950; --fail:#e5534b; --muted:#8b98a5; }}
  body {{ font-family: ui-sans-serif, -apple-system, sans-serif; background:#0f1419; color:#e6edf3;
         margin:32px; }}
  h1 {{ font-size:20px; }} .sub {{ color:var(--muted); font-size:13px; margin-bottom:20px; }}
  .cards {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:20px; }}
  .card {{ background:#171e26; border:1px solid #243040; border-radius:10px; padding:12px 16px; }}
  .card .k {{ color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.08em; }}
  .card .v {{ font-size:18px; font-weight:600; }}
  table {{ border-collapse:collapse; width:100%; background:#171e26; }}
  th, td {{ text-align:left; padding:9px 12px; border-bottom:1px solid #243040; font-size:13px; }}
  th {{ color:var(--muted); font-size:11px; text-transform:uppercase; }}
  tr.pass td:nth-child(2) {{ color:var(--pass); font-weight:600; }}
  tr.fail td:nth-child(2) {{ color:var(--fail); font-weight:600; }}
</style></head><body>
<h1>Evaluation: {escape(result.dataset)}</h1>
<div class="sub">Provider <code>{escape(result.provider)}</code> · model
<code>{escape(result.model)}</code> · started {escape(result.started_at)}</div>
<div class="cards">
  <div class="card"><div class="k">Cases</div><div class="v">{summary.cases}</div></div>
  <div class="card"><div class="k">Check pass rate</div>
    <div class="v">{summary.checks_pass_rate:.1%}</div></div>
  <div class="card"><div class="k">Mean judge</div><div class="v">{judge}</div></div>
  <div class="card"><div class="k">Latency p95</div>
    <div class="v">{summary.latency_p95_ms:.0f} ms</div></div>
  <div class="card"><div class="k">Tokens</div><div class="v">{summary.tokens}</div></div>
</div>
<table><thead><tr><th>Case</th><th>Status</th><th>Failed checks</th>
<th>Judge</th><th>Latency</th></tr></thead><tbody>
{''.join(rows)}
</tbody></table></body></html>
"""


def write_reports(
    result: RunResult,
    json_path: str | Path,
    *,
    html_path: str | Path | None = None,
    markdown_path: str | Path | None = None,
) -> list[Path]:
    written = [write_json(result, json_path)]
    if html_path is not None:
        target = Path(html_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(to_html(result), encoding="utf-8")
        written.append(target)
    if markdown_path is not None:
        target = Path(markdown_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(to_markdown(result), encoding="utf-8")
        written.append(target)
    return written
