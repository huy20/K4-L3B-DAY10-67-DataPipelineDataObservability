from datetime import datetime, timezone
import logging

from core.config import load_settings
from core.utils import read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import LocalEmbeddingIndex

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    """Xay dung baseline pipeline end-to-end.

    1. Load settings.
    2. Load hoac fetch raw records.
    3. Clean data.
    4. Save clean CSV/JSON.
    5. Build Chroma index.
    6. Tao hoac load evaluation set.
    7. Evaluate pipeline.
    8. Run quality checks va freshness report.
    9. Tao markdown report.
    10. Demo agent tren sample question.
    """
    logger.info("=== Phase 1 Baseline Pipeline: START ===")

    # 1. Load settings
    settings = load_settings()
    run_date = datetime.now(timezone.utc)
    logger.info("Loaded settings for provider: %s, model: %s", settings.llm_provider, settings.model_name)

    # 2. Ingestion
    logger.info("[Step 1/8] Ingesting raw Crossref records...")
    raw_records = fetch_source_records(settings)
    logger.info("Ingested %d raw records", len(raw_records))

    # 3. Cleaning
    logger.info("[Step 2/8] Cleaning and pre-embed modeling...")
    clean_df = build_clean_dataframe(raw_records, run_date=run_date)
    logger.info("Cleaned %d records with 5-part text_for_embedding", len(clean_df))

    # 4. Save clean CSV/JSON
    logger.info("[Step 3/8] Saving clean artifacts...")
    write_csv(clean_df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, clean_df.to_dict(orient="records"))
    logger.info("Saved clean data to %s and %s", settings.paths.clean_csv, settings.paths.clean_json)

    # 5. Build Chroma Index
    logger.info("[Step 4/8] Building ChromaDB index for collection '%s'...", settings.baseline_collection_name)
    index = LocalEmbeddingIndex.build(
        clean_df,
        settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )
    logger.info("ChromaDB index built with %d documents", len(clean_df))

    # 6. Evaluation test set
    logger.info("[Step 5/8] Preparing benchmark test set...")
    if not settings.paths.eval_testset.exists() or settings.refresh_test_set:
        test_set = build_test_set(clean_df, settings.paths.eval_testset)
        logger.info("Generated %d benchmark questions", len(test_set))
    else:
        test_set = read_json(settings.paths.eval_testset)
        logger.info("Loaded %d existing benchmark questions", len(test_set))

    # 7. Evaluate
    logger.info("[Step 6/8] Evaluating baseline pipeline...")
    eval_bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    logger.info(
        "Baseline evaluation metrics: Hit Rate = %.2f%%, Mean Token F1 = %.2f%%, Judge Accuracy = %.2f%%",
        eval_bundle.summary.get("retrieval_hit_rate", 0.0) * 100,
        eval_bundle.summary.get("mean_token_f1", 0.0) * 100,
        eval_bundle.summary.get("judge_accuracy", 0.0) * 100,
    )

    # 8. Data Quality & Freshness
    logger.info("[Step 7/8] Running Great Expectations 1.x & Freshness checks...")
    quality_report = run_data_quality_checks(clean_df, settings, report_name="baseline")
    freshness_report = quality_report.get("freshness", {})
    logger.info(
        "Quality Gate status: %s (GX: %s, Freshness: %s)",
        quality_report.get("success"),
        quality_report.get("gx_success"),
        quality_report.get("is_fresh"),
    )

    # 9. Markdown Report
    logger.info("[Step 8/8] Generating phase 1 report...")
    source_summary = {
        "run_date": run_date.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "source_api": settings.source_api,
        "embedding_model": settings.embedding_model,
        "llm_provider": settings.llm_provider,
        "model_name": settings.model_name,
        "raw_count": len(raw_records),
        "clean_count": len(clean_df),
        "raw_response_path": str(settings.paths.raw_api_response),
        "raw_records_path": str(settings.paths.raw_records_json),
        "clean_csv_path": str(settings.paths.clean_csv),
        "clean_json_path": str(settings.paths.clean_json),
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=eval_bundle.summary,
        quality=quality_report,
        freshness=freshness_report,
    )
    logger.info("Saved phase 1 report to %s", settings.paths.baseline_report)

    # 10. Agent Demo
    try:
        logger.info("Running sample agent queries...")
        agent = build_agent(settings, index)
        demo_queries = [
            f"What is the summary of '{clean_df.iloc[0]['title']}'?",
            f"Who authored '{clean_df.iloc[1]['title']}'?",
        ]
        demo_answers = []
        for q in demo_queries:
            ans = run_agent_question(agent, q)
            demo_answers.append({"question": q, "answer": ans})
        write_json(settings.paths.demo_answers, demo_answers)
        logger.info("Saved demo agent answers to %s", settings.paths.demo_answers)
    except Exception as exc:
        logger.warning("Agent demo skipped: %s", exc)

    logger.info("=== Phase 1 Baseline Pipeline: SUCCESS ===")

