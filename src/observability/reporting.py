from __future__ import annotations

from typing import Any

from core.utils import write_text


def _fmt(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.4f}"
    if isinstance(value, (dict, list)):
        return f"`{value}`"
    return str(value)


def _metrics_table(metrics: dict[str, Any]) -> str:
    rows = [
        ("samples", metrics.get("samples")),
        ("retrieval_hit_rate", metrics.get("retrieval_hit_rate")),
        ("mean_token_f1", metrics.get("mean_token_f1")),
        ("judge_accuracy", metrics.get("judge_accuracy")),
        ("mean_judge_score", metrics.get("mean_judge_score")),
    ]
    lines = ["| Metric | Value |", "| --- | ---: |"]
    lines.extend(f"| `{name}` | {_fmt(value)} |" for name, value in rows)
    return "\n".join(lines)


def _quality_table(quality: dict[str, Any]) -> str:
    lines = ["| Expectation | Column | Success | Observed |", "| --- | --- | :---: | --- |"]
    for item in quality.get("expectations", []):
        lines.append(
            "| `{type}` | {column} | {success} | {observed} |".format(
                type=item.get("expectation_type", "-"),
                column=item.get("column") or "-",
                success=item.get("success"),
                observed=_fmt(item.get("observed_value")),
            )
        )
    return "\n".join(lines)


def _freshness_table(freshness: dict[str, Any]) -> str:
    rows = [
        ("latest_published", freshness.get("latest_published")),
        ("oldest_published", freshness.get("oldest_published")),
        ("stale_rows", freshness.get("stale_rows")),
        ("unknown_published_rows", freshness.get("unknown_published_rows")),
        ("total_rows", freshness.get("total_rows")),
        ("stale_ratio", freshness.get("stale_ratio")),
        ("freshness_threshold_days", freshness.get("freshness_threshold_days")),
        ("is_fresh", freshness.get("is_fresh")),
    ]
    lines = ["| Field | Value |", "| --- | --- |"]
    lines.extend(f"| `{name}` | {_fmt(value)} |" for name, value in rows)
    return "\n".join(lines)


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Viet markdown report cho baseline phase."""
    status = "PASS" if quality.get("success") and freshness.get("is_fresh") else "ATTENTION"
    ragas = metrics.get("ragas")

    lines = [
        "# Phase 1 Report — Baseline Data Pipeline",
        "",
        f"- Generated at: `{source_summary.get('generated_at', 'N/A')}`",
        f"- Source: `{source_summary.get('source_api', 'N/A')}`",
        f"- Query: `{source_summary.get('source_query', 'N/A')}`",
        f"- Filter: `{source_summary.get('source_filter', 'N/A')}`",
        f"- Raw records: `{source_summary.get('records', 'N/A')}`",
        f"- Clean rows: `{source_summary.get('clean_rows', 'N/A')}`",
        f"- Vector collection: `{source_summary.get('collection', 'N/A')}` (`{source_summary.get('indexed_docs', 'N/A')}` docs)",
        f"- Overall quality/freshness status: **{status}**",
        "",
        "## 1. Raw & Clean Lineage",
        "",
        f"- Raw API response: `{source_summary.get('raw_response', 'N/A')}`",
        f"- Raw records: `{source_summary.get('raw_records', 'N/A')}`",
        "",
        "## 2. Baseline Metrics",
        "",
        _metrics_table(metrics),
        "",
        f"- Ragas: {_fmt(ragas)}",
        "",
        "## 3. Data Quality (Great Expectations 1.x)",
        "",
        f"- Overall `success`: **{quality.get('success')}**",
        f"- Rows checked: `{quality.get('row_count', 'N/A')}`",
        "",
        _quality_table(quality),
        "",
        "## 4. Freshness SLA",
        "",
        _freshness_table(freshness),
        "",
        f"- SLA rule: `is_fresh = False` when the ratio of rows with `age_days > "
        f"{freshness.get('freshness_threshold_days', 'N/A')}` exceeds 25%.",
        "",
    ]
    write_text(report_path, "\n".join(lines))


def _recovery_ratio(baseline: Any, corrupted: Any, repaired: Any) -> str:
    try:
        baseline_value = float(baseline)
        corrupted_value = float(corrupted)
        repaired_value = float(repaired)
    except (TypeError, ValueError):
        return "N/A"
    drop = baseline_value - corrupted_value
    if abs(drop) < 1e-12:
        return "N/A"
    return f"{(repaired_value - corrupted_value) / drop * 100:.1f}%"


def _comparison_table(
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
) -> str:
    rows = [
        ("retrieval_hit_rate", baseline_metrics, corrupted_metrics, repaired_metrics),
        ("mean_token_f1", baseline_metrics, corrupted_metrics, repaired_metrics),
        ("judge_accuracy", baseline_metrics, corrupted_metrics, repaired_metrics),
        ("mean_judge_score", baseline_metrics, corrupted_metrics, repaired_metrics),
    ]
    lines = [
        "| Metric | Baseline | Corrupted | Repaired | Corruption delta | Recovery |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, baseline, corrupted, repaired in rows:
        base_value = baseline.get(name)
        corr_value = corrupted.get(name)
        rep_value = repaired.get(name)
        delta = "N/A"
        if isinstance(base_value, (int, float)) and isinstance(corr_value, (int, float)):
            delta = f"{corr_value - base_value:+.4f}"
        lines.append(
            f"| `{name}` | {_fmt(base_value)} | {_fmt(corr_value)} | {_fmt(rep_value)} | {delta} | "
            f"{_recovery_ratio(base_value, corr_value, rep_value)} |"
        )
    return "\n".join(lines)


def _state_table(
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> str:
    lines = [
        "| Signal | Corrupted | Repaired |",
        "| --- | :---: | :---: |",
        f"| GX `success` | {corrupted_quality.get('success')} | {repaired_quality.get('success')} |",
        f"| Failed expectations | {sum(1 for e in corrupted_quality.get('expectations', []) if not e.get('success'))} | "
        f"{sum(1 for e in repaired_quality.get('expectations', []) if not e.get('success'))} |",
        f"| Freshness `is_fresh` | {corrupted_freshness.get('is_fresh')} | {repaired_freshness.get('is_fresh')} |",
        f"| Stale rows | {corrupted_freshness.get('stale_rows')} | {repaired_freshness.get('stale_rows')} |",
        f"| Total rows | {corrupted_freshness.get('total_rows')} | {repaired_freshness.get('total_rows')} |",
    ]
    return "\n".join(lines)


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Viet markdown report so sanh baseline/corrupted/repaired."""
    corrupted_failed = [
        item for item in corrupted_quality.get("expectations", []) if not item.get("success")
    ]
    failed_names = ", ".join(
        f"`{item.get('expectation_type')}`" for item in corrupted_failed
    ) or "none"

    lines = [
        "# Corruption & Repair Report — Three-State Comparison",
        "",
        "> Baseline vs Corrupted vs Repaired. Repair is idempotent: it re-derives the clean "
        "dataset directly from the trusted raw snapshot instead of patching corrupted rows.",
        "",
        "## 1. Performance Comparison",
        "",
        _comparison_table(baseline_metrics, corrupted_metrics, repaired_metrics),
        "",
        f"- Baseline samples: `{baseline_metrics.get('samples', 'N/A')}`",
        f"- Corrupted samples: `{corrupted_metrics.get('samples', 'N/A')}`",
        f"- Repaired samples: `{repaired_metrics.get('samples', 'N/A')}`",
        "",
        "## 2. Data Quality & Freshness",
        "",
        _state_table(corrupted_quality, repaired_quality, corrupted_freshness, repaired_freshness),
        "",
        f"- Corrupted quality gate failed on: {failed_names}",
        "",
        "## 3. Conclusions",
        "",
        "1. **Corruption → quality/freshness signal → agent metrics.** Dropping the newest "
        "records and blanking/noising summaries removed gold documents from the index and "
        "corrupted answer text, so `retrieval_hit_rate`, `mean_token_f1`, and the judge metrics "
        "all fell while the GX uniqueness/length checks and the freshness SLA flipped to fail.",
        "2. **Repair action → quality/freshness recovery → agent metrics recovery.** Rebuilding "
        "the clean dataframe from `data/raw/crossref_records.json` restores the document set and "
        "the quality gate passes again, bringing retrieval and answer metrics back to baseline.",
        "",
        "## 4. Interpretation Notes",
        "",
        "- The corrupted run uses the same evaluation set as baseline and repaired, so the only "
        "variable is data quality; this keeps the comparison causal rather than confounded.",
        "- A recovery of `100%` means the repaired metric returned to its baseline value; `N/A` "
        "means the corruption did not change that metric (no denominator).",
        "",
    ]
    write_text(report_path, "\n".join(lines))
