from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings


from pathlib import Path
from typing import Any

import great_expectations as gx
import pandas as pd

from core.config import Settings
from core.utils import write_json


def build_freshness_report(
    df: pd.DataFrame,
    settings: Settings,
    report_path: Path | str | None = None,
) -> dict[str, Any]:
    """Tong hop freshness report va danh gia Freshness SLA.

    1. Tim latest va oldest published date.
    2. Dem so dong stale (age_days > freshness_threshold_days).
    3. Tao payload:
       - latest_published
       - oldest_published
       - stale_rows
       - total_rows
       - is_fresh
    4. Ghi JSON report.
    """
    target_path = Path(report_path) if report_path else settings.paths.freshness_report
    total_rows = len(df)
    threshold = settings.freshness_threshold_days

    if "age_days" in df.columns:
        stale_mask = df["age_days"] > threshold
        stale_rows = int(stale_mask.sum())
    else:
        stale_rows = 0

    stale_ratio = (stale_rows / total_rows) if total_rows > 0 else 0.0
    # Freshness SLA: canh bao is_fresh = False neu ty le stale > 25%
    is_fresh = bool(stale_ratio <= 0.25)

    published_series = (
        df["published"].dropna().astype(str)
        if "published" in df.columns and not df.empty
        else pd.Series(dtype=str)
    )
    latest_published = str(published_series.max()) if not published_series.empty else ""
    oldest_published = str(published_series.min()) if not published_series.empty else ""

    payload: dict[str, Any] = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": round(stale_ratio, 4),
        "freshness_threshold_days": threshold,
        "is_fresh": is_fresh,
    }

    write_json(target_path, payload)
    return payload


def run_data_quality_checks(
    df: pd.DataFrame,
    settings: Settings,
    report_name: str,
) -> dict[str, Any]:
    """Tao bo data quality checks theo chuan Great Expectations 1.x.

    1. Cấu hình ephemeral context Great Expectations 1.x.
    2. Định nghĩa 4 Expectations thiết yếu:
       - Row count between 20 and 30
       - Not null cho paper_id, title, summary
       - Unique cho paper_id
       - Length range cho title (>=8) va summary (>=20)
    3. Tinh toan Freshness SLA bang age_days.
    4. Ghi ket qua chi tiet vao data/quality/.
    """
    # 1. Ephemeral context GX 1.x
    context = gx.get_context(mode="ephemeral")
    source_name = f"papers_source_{report_name}"
    asset_name = f"papers_asset_{report_name}"
    batch_name = f"papers_batch_{report_name}"
    suite_name = f"papers_suite_{report_name}"

    data_source = context.data_sources.add_pandas(name=source_name)
    data_asset = data_source.add_dataframe_asset(name=asset_name)
    batch_def = data_asset.add_batch_definition_whole_dataframe(batch_name)
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    # 2. Xay dung Expectation Suite voi 4 nhom expectation thiet yeu
    suite = gx.ExpectationSuite(name=suite_name)
    # (1) ExpectTableRowCountToBeBetween
    suite.add_expectation(
        gx.expectations.ExpectTableRowCountToBeBetween(min_value=20, max_value=30)
    )
    # (2) ExpectColumnValuesToNotBeNull
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToNotBeNull(column="paper_id")
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToNotBeNull(column="title")
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToNotBeNull(column="summary")
    )
    # (3) ExpectColumnValuesToBeUnique
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id")
    )
    # (4) ExpectColumnValueLengthsToBeBetween
    suite.add_expectation(
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="title", min_value=8)
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=20)
    )

    # 3. Validate batch
    validation_results = batch.validate(suite)
    gx_success = bool(validation_results.success)

    # 4. Kiem tra Freshness SLA
    if report_name == "baseline":
        freshness_path = settings.paths.freshness_report
    else:
        freshness_path = settings.paths.quality_dir / f"{report_name}_freshness_report.json"
    freshness = build_freshness_report(df, settings, report_path=freshness_path)
    is_fresh = bool(freshness.get("is_fresh", True))

    overall_success = bool(gx_success and is_fresh)

    # 5. Tong hop ket qua expectation
    expectation_summaries: list[dict[str, Any]] = []
    for r in validation_results.results:
        exp_type = getattr(r.expectation_config, "type", "unknown")
        kwargs = dict(getattr(r.expectation_config, "kwargs", {}) or {})
        result_dict = dict(getattr(r, "result", {}) or {})
        expectation_summaries.append(
            {
                "expectation_type": exp_type,
                "column": kwargs.get("column"),
                "kwargs": kwargs,
                "success": bool(r.success),
                "result": {
                    "observed_value": result_dict.get("observed_value"),
                    "element_count": result_dict.get("element_count"),
                    "unexpected_count": result_dict.get("unexpected_count"),
                },
            }
        )

    successful_count = sum(1 for item in expectation_summaries if item["success"])
    total_count = len(expectation_summaries)

    statistics = {
        "evaluated_expectations": total_count,
        "successful_expectations": successful_count,
        "unsuccessful_expectations": total_count - successful_count,
        "success_percent": round(100.0 * successful_count / total_count, 2) if total_count else 0.0,
    }

    report_payload: dict[str, Any] = {
        "report_name": report_name,
        "success": overall_success,
        "gx_success": gx_success,
        "is_fresh": is_fresh,
        "total_rows": len(df),
        "statistics": statistics,
        "freshness": freshness,
        "expectations": expectation_summaries,
    }

    # 6. Ghi report ra output path tuong ung
    if report_name == "baseline":
        out_path = settings.paths.baseline_quality_report
    elif report_name == "corrupted":
        out_path = settings.paths.corrupted_quality_report
    else:
        out_path = settings.paths.quality_dir / f"{report_name}_quality_report.json"

    write_json(out_path, report_payload)
    return report_payload

