from __future__ import annotations

from core.config import load_settings
from core.utils import now_utc, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Xay dung baseline pipeline end-to-end cho Pha 1."""
    settings = load_settings()
    print("=== [PHASE 1] Khoi dong Baseline Pipeline End-to-End ===")

    # 1. Fetch / Load source raw records
    print("1. Dang nap raw records tu Crossref...")
    raw_records = fetch_source_records(settings)
    print(f"   -> Da tai {len(raw_records)} ban ghi tho.")

    # 2. Clean data
    print("2. Dang thuc thi Data Cleaning & Schema Normalization...")
    clean_df = build_clean_dataframe(raw_records, now_utc())
    print(f"   -> Da lam sach va chuan hoa {len(clean_df)} ban ghi.")

    # 3. Save clean artifacts
    print("3. Luu tru clean artifacts...")
    write_csv(clean_df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, clean_df.to_dict(orient="records"))
    print(f"   -> Da luu clean CSV va JSON tai {settings.paths.clean_csv.parent}")

    # 4. Build Chroma vector index
    print(f"4. Xay dung ChromaDB collection '{settings.baseline_collection_name}'...")
    index = LocalEmbeddingIndex.build(clean_df, settings, settings.paths.embeddings_json)
    print(f"   -> Da index {len(index.documents)} documents vao ChromaDB.")

    # 5. Build or load evaluation test set
    print("5. Xay dung Evaluation Benchmark Test Set...")
    test_set = build_test_set(clean_df, settings.paths.eval_testset)
    print(f"   -> Da tao {len(test_set)} cau hoi benchmark tai {settings.paths.eval_testset}")

    # 6. Evaluate baseline pipeline
    print("6. Thuc thi Baseline Evaluation Benchmark...")
    eval_bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    hit_rate = eval_bundle.summary.get("retrieval_hit_rate", 0.0) * 100
    token_f1 = eval_bundle.summary.get("mean_token_f1", 0.0) * 100
    print(f"   -> Retrieval Hit Rate: {hit_rate:.1f}%")
    print(f"   -> Mean Token F1: {token_f1:.1f}%")

    # 7. Run data quality checks & freshness report
    print("7. Kiem dinh chat luong qua Great Expectations 1.x & Freshness SLA...")
    quality_report = run_data_quality_checks(clean_df, settings, "baseline")
    freshness_report = build_freshness_report(clean_df, settings, settings.paths.freshness_report)
    print(
        f"   -> Quality Gate Status: {quality_report['success']} "
        f"(GX: {quality_report['gx_success']}, Freshness: {freshness_report['is_fresh']})"
    )

    # 8. Generate Phase 1 markdown report
    print("8. Xuat bao cao tong ket Pha 1...")
    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "raw_count": len(raw_records),
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=eval_bundle.summary,
        quality=quality_report,
        freshness=freshness_report,
    )
    print(f"   -> Da xuat bao cao tai {settings.paths.baseline_report}")
    print("=== [PHASE 1] Hoan thanh Baseline Pipeline End-to-End thanh cong! ===")
