from __future__ import annotations

import hashlib

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_dataframe, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex

_METRIC_KEYS = ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score")


def _fingerprint(df: pd.DataFrame) -> str:
    payload = "\n".join(
        f"{row['paper_id']}|{row['text_for_embedding']}" for _, row in df.iterrows()
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _num(value) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _recovery(baseline, corrupted, repaired) -> str:
    try:
        drop = float(baseline) - float(corrupted)
        if abs(drop) < 1e-12:
            return "N/A"
        return f"{(float(repaired) - float(corrupted)) / drop * 100:.0f}%"
    except (TypeError, ValueError):
        return "N/A"


def _print_comparison(
    baseline_metrics: dict,
    corrupted_metrics: dict,
    repaired_metrics: dict,
    corrupted_quality: dict,
    repaired_quality: dict,
    corrupted_freshness: dict,
    repaired_freshness: dict,
    idempotent: bool,
) -> None:
    header = f"{'Metric':<22}{'Baseline':>12}{'Corrupted':>12}{'Repaired':>12}{'Recovery':>12}"
    print("\n[corruption] Three-state comparison")
    print(header)
    print("-" * len(header))
    for name in _METRIC_KEYS:
        base_value = baseline_metrics.get(name)
        corr_value = corrupted_metrics.get(name)
        rep_value = repaired_metrics.get(name)
        print(
            f"{name:<22}{_num(base_value):>12}{_num(corr_value):>12}{_num(rep_value):>12}"
            f"{_recovery(base_value, corr_value, rep_value):>12}"
        )
    print(
        f"{'quality_success':<22}{'True':>12}{str(corrupted_quality.get('success')):>12}"
        f"{str(repaired_quality.get('success')):>12}{'':>12}"
    )
    print(
        f"{'freshness_is_fresh':<22}{'True':>12}{str(corrupted_freshness.get('is_fresh')):>12}"
        f"{str(repaired_freshness.get('is_fresh')):>12}{'':>12}"
    )
    print(f"idempotent_repair: {idempotent}")


def main() -> None:
    """Corruption -> evaluate -> idempotent repair -> evaluate -> compare."""
    settings = load_settings()
    paths = settings.paths
    run_date = now_utc()

    needs_baseline = not (
        paths.clean_json.exists()
        and paths.clean_csv.exists()
        and paths.baseline_metrics.exists()
        and paths.eval_testset.exists()
    )
    if needs_baseline:
        from pipelines.phase1 import main as run_phase1

        print("[corruption] baseline artifacts missing; running phase 1 first")
        run_phase1()

    raw_records = load_raw_records(paths.raw_records_json)
    if settings.refresh_source or not raw_records:
        raw_records = fetch_source_records(settings)
    if not raw_records:
        raise RuntimeError("No raw records available to run the corruption flow.")

    # Reference clean state, re-derived from the trusted raw snapshot.
    clean_df = build_clean_dataframe(raw_records, run_date)
    write_dataframe(clean_df, paths.clean_csv, paths.clean_json)

    if settings.refresh_test_set or not paths.eval_testset.exists():
        build_test_set(clean_df, paths.eval_testset)
    test_set = read_json(paths.eval_testset)
    baseline_metrics = read_json(paths.baseline_metrics)
    print(f"[corruption] baseline rows: {len(clean_df)} | test questions: {len(test_set)}")

    # 1. Corrupt and measure the damaged state.
    corrupted_df = corrupt_clean_dataframe(clean_df, paths.corruption_log)
    write_dataframe(corrupted_df, paths.corrupted_clean_csv, paths.corrupted_clean_json)
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df, settings, embeddings_output_path=paths.corrupted_embeddings_json
    )
    corrupted_bundle = evaluate_pipeline(
        settings, corrupted_index, paths.eval_testset, paths.corrupted_metrics, paths.corrupted_answers
    )
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, paths.quality_dir / "corrupted_freshness_report.json"
    )
    print(
        f"[corruption] corrupted rows: {len(corrupted_df)} | quality: {corrupted_quality['success']}"
        f" | fresh: {corrupted_freshness['is_fresh']}"
    )

    # 2. Idempotent repair: re-derive from raw records, never patch corrupted rows in place.
    repaired_check = build_clean_dataframe(raw_records, run_date)
    repaired_df = build_clean_dataframe(raw_records, run_date)
    idempotent = bool(
        repaired_check.equals(repaired_df)
        and _fingerprint(repaired_df) == _fingerprint(clean_df)
    )
    write_dataframe(repaired_df, paths.repaired_clean_csv, paths.repaired_clean_json)
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df, settings, embeddings_output_path=paths.repaired_embeddings_json
    )
    repaired_bundle = evaluate_pipeline(
        settings, repaired_index, paths.eval_testset, paths.repaired_metrics, paths.repaired_answers
    )
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(
        repaired_df, settings, paths.quality_dir / "repaired_freshness_report.json"
    )
    print(
        f"[corruption] repaired rows: {len(repaired_df)} | quality: {repaired_quality['success']}"
        f" | fresh: {repaired_freshness['is_fresh']} | idempotent: {idempotent}"
    )

    repair_log = {
        "generated_at": now_utc().isoformat(),
        "repair_source": str(paths.raw_records_json.relative_to(paths.project_dir)),
        "idempotent": idempotent,
        "repaired_matches_baseline": _fingerprint(repaired_df) == _fingerprint(clean_df),
        "rows": {
            "baseline": int(len(clean_df)),
            "corrupted": int(len(corrupted_df)),
            "repaired": int(len(repaired_df)),
        },
        "fingerprints": {
            "baseline": _fingerprint(clean_df),
            "corrupted": _fingerprint(corrupted_df),
            "repaired": _fingerprint(repaired_df),
        },
    }
    write_json(paths.corruption_log.parent / "repair_log.json", repair_log)

    generate_corruption_report(
        paths.comparison_report,
        baseline_metrics,
        corrupted_bundle.summary,
        repaired_bundle.summary,
        corrupted_quality,
        repaired_quality,
        corrupted_freshness,
        repaired_freshness,
    )
    _print_comparison(
        baseline_metrics,
        corrupted_bundle.summary,
        repaired_bundle.summary,
        corrupted_quality,
        repaired_quality,
        corrupted_freshness,
        repaired_freshness,
        idempotent,
    )
    print(f"[corruption] report written: {paths.comparison_report}")


if __name__ == "__main__":
    main()
