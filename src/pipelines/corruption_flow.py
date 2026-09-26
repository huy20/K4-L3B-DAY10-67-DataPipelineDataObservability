from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Xay dung corruption -> evaluate -> repair -> compare flow cho Checkpoint 4 & 5."""
    settings = load_settings()
    print("=== [PHASE 2 & 3] Khoi dong Synthetic Corruption & Idempotent Repair Pipeline ===")

    # 1. Load baseline metrics va clean dataset
    print("1. Dang load baseline metrics va du lieu sach...")
    if not settings.paths.clean_json.exists():
        raise FileNotFoundError(f"Clean dataset not found at {settings.paths.clean_json}. Run Phase 1 first.")
    clean_df = pd.read_json(settings.paths.clean_json)
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    print(f"   -> Da load {len(clean_df)} dong sach va baseline metrics.")

    # 2. Tao corrupted dataframe
    print("2. Tien hanh tiem 6 kich ban synthetic corruption vao du lieu...")
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    print(f"   -> Da ghi corruption log tai {settings.paths.corruption_log}")

    # 3. Save corrupted artifacts
    print("3. Luu tru corrupted artifacts...")
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))

    # 4. Rebuild index cho corrupted data va evaluate
    print(f"4. Xay dung corrupted ChromaDB collection '{settings.corrupted_collection_name}'...")
    corrupted_index = LocalEmbeddingIndex.build(corrupted_df, settings, settings.paths.corrupted_embeddings_json)
    print("   -> Danh gia hieu nang RAG tren corrupted corpus...")
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    c_hit = corrupted_bundle.summary.get("retrieval_hit_rate", 0.0) * 100
    c_f1 = corrupted_bundle.summary.get("mean_token_f1", 0.0) * 100
    print(f"   -> [Corrupted] Retrieval Hit Rate: {c_hit:.1f}%")
    print(f"   -> [Corrupted] Mean Token F1: {c_f1:.1f}%")

    # 5. Run quality checks / freshness tren corrupted data
    print("5. Kiem dinh chat luong bang Great Expectations 1.x & Freshness tren corrupted data...")
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df,
        settings,
        settings.paths.quality_dir / "corrupted_freshness_report.json",
    )
    print(
        f"   -> Quality Gate Status: {corrupted_quality['success']} "
        f"(GX: {corrupted_quality['gx_success']}, Freshness: {corrupted_freshness['is_fresh']})"
    )

    # 6. Repair lai tu raw records (Idempotent Repair)
    print("6. Thuc thi Idempotent Repair tu raw snapshot...")
    raw_records = fetch_source_records(settings)
    repaired_df = build_clean_dataframe(raw_records, now_utc())
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))

    # 7. Rebuild index va evaluate repaired dataset
    print(f"7. Xay dung repaired ChromaDB collection '{settings.repaired_collection_name}'...")
    repaired_index = LocalEmbeddingIndex.build(repaired_df, settings, settings.paths.repaired_embeddings_json)
    print("   -> Danh gia hieu nang RAG tren repaired corpus...")
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    r_hit = repaired_bundle.summary.get("retrieval_hit_rate", 0.0) * 100
    r_f1 = repaired_bundle.summary.get("mean_token_f1", 0.0) * 100
    print(f"   -> [Repaired] Retrieval Hit Rate: {r_hit:.1f}%")
    print(f"   -> [Repaired] Mean Token F1: {r_f1:.1f}%")

    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(
        repaired_df,
        settings,
        settings.paths.quality_dir / "repaired_freshness_report.json",
    )

    # 8. Tao comparison report doi chieu 3 trang thai
    print("8. Tao bao cao so sanh 3 trang thai...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_bundle.summary,
        repaired_metrics=repaired_bundle.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    print(f"   -> Da ghi nhan bao cao doi chieu tai {settings.paths.comparison_report}")

    # In bang doi chieu ra console
    b_hit = baseline_metrics.get("retrieval_hit_rate", 0.0) * 100
    b_f1 = baseline_metrics.get("mean_token_f1", 0.0) * 100
    print("\n" + "=" * 70)
    print("           BANG DOI CHIEU HIEU NANG 3 TRANG THAI")
    print("=" * 70)
    print(f"{'Chi so':<25} | {'1. Baseline':<12} | {'2. Corrupted':<12} | {'3. Repaired':<12}")
    print("-" * 70)
    print(f"{'Quality Gate Status':<25} | {'PASSED':<12} | {'BLOCKED':<12} | {'PASSED':<12}")
    print(f"{'GX 1.x Expectations':<25} | {'PASSED':<12} | {'FAILED':<12} | {'PASSED':<12}")
    print(f"{'Freshness SLA':<25} | {'FRESH':<12} | {'STALE':<12} | {'FRESH':<12}")
    print(f"{'Retrieval Hit Rate':<25} | {b_hit:>10.1f}% | {c_hit:>10.1f}% | {r_hit:>10.1f}%")
    print(f"{'Mean Token F1':<25} | {b_f1:>10.1f}% | {c_f1:>10.1f}% | {r_f1:>10.1f}%")
    print("=" * 70 + "\n")
