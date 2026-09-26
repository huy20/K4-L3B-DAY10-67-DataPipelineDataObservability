from __future__ import annotations

from core.config import load_settings
from core.utils import now_utc, read_json, write_dataframe
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Baseline pipeline end-to-end: ingest -> clean -> index -> evaluate -> report."""
    settings = load_settings()
    paths = settings.paths

    records = load_raw_records(paths.raw_records_json)
    if settings.refresh_source or not records:
        records = fetch_source_records(settings)
    print(f"[phase1] raw records: {len(records)}")

    run_date = now_utc()
    df = build_clean_dataframe(records, run_date)
    if df.empty:
        raise RuntimeError("Cleaned dataframe is empty; cannot build the baseline index.")
    write_dataframe(df, paths.clean_csv, paths.clean_json)
    print(f"[phase1] clean rows: {len(df)} -> {paths.clean_csv}")

    index = LocalEmbeddingIndex.build(df, settings)
    print(f"[phase1] chroma collection: {index.collection_name} ({index.collection.count()} docs)")

    if settings.refresh_test_set or not paths.eval_testset.exists():
        test_set = build_test_set(df, paths.eval_testset)
    else:
        test_set = read_json(paths.eval_testset)
    print(f"[phase1] evaluation questions: {len(test_set)}")

    bundle = evaluate_pipeline(
        settings,
        index,
        paths.eval_testset,
        paths.baseline_metrics,
        paths.baseline_answers,
    )
    metrics = bundle.summary

    quality = run_data_quality_checks(df, settings, "baseline")
    freshness = build_freshness_report(df, settings, paths.freshness_report)

    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "records": len(records),
        "clean_rows": len(df),
        "raw_response": str(paths.raw_api_response.relative_to(paths.project_dir)),
        "raw_records": str(paths.raw_records_json.relative_to(paths.project_dir)),
        "generated_at": run_date.isoformat(),
        "collection": index.collection_name,
        "indexed_docs": index.collection.count(),
    }
    generate_phase1_report(paths.baseline_report, source_summary, metrics, quality, freshness)

    print("[phase1] baseline metrics:")
    for key in ("samples", "retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"):
        print(f"  {key}: {metrics.get(key)}")
    print(f"[phase1] quality success: {quality['success']} | freshness is_fresh: {freshness['is_fresh']}")
    print(f"[phase1] report written: {paths.baseline_report}")


if __name__ == "__main__":
    main()
