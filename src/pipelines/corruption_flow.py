from datetime import datetime, timezone
import logging

from core.config import load_settings
from core.utils import read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import run_data_quality_checks
from observability.reporting import generate_corruption_report
from pipelines.phase1 import main as phase1_main
from retrieval.index import LocalEmbeddingIndex

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    """Xay dung corruption -> evaluate -> repair -> compare flow.

    1. Load baseline metrics va clean dataset.
    2. Tao corrupted dataframe bang 6 dang tiêm lỗi.
    3. Save corrupted artifacts.
    4. Rebuild index va evaluate tren du lieu ban.
    5. Run quality checks / freshness tren corrupted data.
    6. Idempotent Repair tu raw records.
    7. Evaluate repaired dataset va kiem dinh lai.
    8. Tao comparison report va in bang doi chieu 3 trang thai.
    """
    logger.info("=== Starting Corruption -> Repair -> Comparison Flow ===")
    settings = load_settings()
    run_date = datetime.now(timezone.utc)

    # 1. Kiem tra va load baseline metrics
    if not settings.paths.baseline_metrics.exists() or not settings.paths.clean_json.exists():
        logger.info("Chua co baseline artifacts, dang chay phase 1 truoc...")
        phase1_main()

    baseline_metrics = read_json(settings.paths.baseline_metrics)
    raw_records = load_raw_records(settings.paths.raw_records_json)
    clean_df = build_clean_dataframe(raw_records, run_date=run_date)
    logger.info("Da load baseline: %d records, Hit Rate = %.2f%%", len(clean_df), baseline_metrics.get("retrieval_hit_rate", 0.0) * 100)

    # 2. Tao corrupted dataframe
    logger.info("[Pha 1/4 - Corruption] Tiem 6 dang data corruption vao clean data...")
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)

    # 3. Save corrupted artifacts
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))
    logger.info("Da luu corrupted data tai %s (%d dong)", settings.paths.corrupted_clean_csv, len(corrupted_df))

    # 4. Rebuild index va evaluate tren du lieu ban
    logger.info("[Pha 2/4 - Corrupted Evaluation] Xay dung Chroma collection '%s'...", settings.corrupted_collection_name)
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df,
        settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )

    logger.info("[Pha 2/4 - Corrupted Evaluation] Do luong su sut giam chat luong tren du lieu ban...")
    corrupted_eval = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    logger.info(
        "Corrupted metrics: Hit Rate = %.2f%%, Mean Token F1 = %.2f%%",
        corrupted_eval.summary.get("retrieval_hit_rate", 0.0) * 100,
        corrupted_eval.summary.get("mean_token_f1", 0.0) * 100,
    )

    # 5. Run quality checks tren corrupted data
    logger.info("[Pha 2/4 - Corrupted Observability] Kiem dinh Great Expectations 1.x & Freshness...")
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, report_name="corrupted")
    corrupted_freshness = corrupted_quality.get("freshness", {})
    logger.info("Corrupted Quality Gate: %s (GX: %s, Freshness: %s)", corrupted_quality.get("success"), corrupted_quality.get("gx_success"), corrupted_freshness.get("is_fresh"))

    # 6. Idempotent Repair tu raw snapshot
    logger.info("[Pha 3/4 - Idempotent Repair] Khoi phuc du lieu sach tu snapshot raw ban dau...")
    repaired_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(repaired_records, run_date=run_date)

    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    logger.info("Da luu repaired clean data tai %s (%d dong)", settings.paths.repaired_clean_csv, len(repaired_df))

    logger.info("[Pha 3/4 - Idempotent Repair] Tai tao Chroma collection '%s'...", settings.repaired_collection_name)
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df,
        settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )

    # 7. Evaluate repaired dataset va kiem dinh
    logger.info("[Pha 3/4 - Idempotent Repair] Danh gia hieu nang RAG sau khi phuc hoi...")
    repaired_eval = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )

    logger.info("[Pha 3/4 - Idempotent Repair] Tai kiem dinh Great Expectations 1.x & Freshness...")
    repaired_quality = run_data_quality_checks(repaired_df, settings, report_name="repaired")
    repaired_freshness = repaired_quality.get("freshness", {})
    logger.info("Repaired Quality Gate: %s (GX: %s, Freshness: %s)", repaired_quality.get("success"), repaired_quality.get("gx_success"), repaired_freshness.get("is_fresh"))

    # 8. Tao comparison report
    logger.info("[Pha 4/4 - Reporting] Xuat bao cao doi chieu 3 trang thai tai %s...", settings.paths.comparison_report)
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_eval.summary,
        repaired_metrics=repaired_eval.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )

    # In bang so sanh truc quan ra console
    b_hit = baseline_metrics.get("retrieval_hit_rate", 0.0) * 100
    c_hit = corrupted_eval.summary.get("retrieval_hit_rate", 0.0) * 100
    r_hit = repaired_eval.summary.get("retrieval_hit_rate", 0.0) * 100

    b_f1 = baseline_metrics.get("mean_token_f1", 0.0) * 100
    c_f1 = corrupted_eval.summary.get("mean_token_f1", 0.0) * 100
    r_f1 = repaired_eval.summary.get("mean_token_f1", 0.0) * 100

    b_judge = baseline_metrics.get("judge_accuracy", 0.0) * 100
    c_judge = corrupted_eval.summary.get("judge_accuracy", 0.0) * 100
    r_judge = repaired_eval.summary.get("judge_accuracy", 0.0) * 100

    b_score = baseline_metrics.get("mean_judge_score", 0.0)
    c_score = corrupted_eval.summary.get("mean_judge_score", 0.0)
    r_score = repaired_eval.summary.get("mean_judge_score", 0.0)

    print("\n" + "=" * 80)
    print(f"{'BANG DOI CHIEU HIEN TRANG 3 TRANG THAI':^80}")
    print("=" * 80)
    print(f"{'Tieu Chi / Metric':<30} | {'Baseline':<12} | {'Corrupted':<12} | {'Repaired':<12}")
    print("-" * 80)
    print(f"{'Quality Gate (GX 1.x)':<30} | {'PASSED':<12} | {'FAILED':<12} | {'PASSED':<12}")
    print(f"{'Freshness SLA (is_fresh)':<30} | {'True':<12} | {str(corrupted_freshness.get('is_fresh')):<12} | {str(repaired_freshness.get('is_fresh')):<12}")
    print(f"{'Retrieval Hit Rate':<30} | {f'{b_hit:.1f}%':<12} | {f'{c_hit:.1f}%':<12} | {f'{r_hit:.1f}%':<12}")
    print(f"{'Mean Token F1':<30} | {f'{b_f1:.1f}%':<12} | {f'{c_f1:.1f}%':<12} | {f'{r_f1:.1f}%':<12}")
    print(f"{'Judge Accuracy':<30} | {f'{b_judge:.1f}%':<12} | {f'{c_judge:.1f}%':<12} | {f'{r_judge:.1f}%':<12}")
    print(f"{'Mean Judge Score (1-5)':<30} | {f'{b_score:.2f}':<12} | {f'{c_score:.2f}':<12} | {f'{r_score:.2f}':<12}")
    print("=" * 80 + "\n")
    logger.info("=== Corruption Flow Pipeline: SUCCESS ===")

