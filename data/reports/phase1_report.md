# Phase 1 Report — Baseline Data Pipeline

- Generated at: `2026-09-26T03:26:49.101091+00:00`
- Source: `Crossref REST API`
- Query: `agentic retrieval augmented generation large language model`
- Filter: `from-pub-date:2026-03-30,has-abstract:true`
- Raw records: `24`
- Clean rows: `24`
- Vector collection: `papers-baseline` (`24` docs)
- Overall quality/freshness status: **PASS**

## 1. Raw & Clean Lineage

- Raw API response: `data\raw\crossref_response.json`
- Raw records: `data\raw\crossref_records.json`

## 2. Baseline Metrics

| Metric | Value |
| --- | ---: |
| `samples` | 10 |
| `retrieval_hit_rate` | 1.0000 |
| `mean_token_f1` | 1.0000 |
| `judge_accuracy` | 1.0000 |
| `mean_judge_score` | 5 |

- Ragas: `{'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'}`

## 3. Data Quality (Great Expectations 1.x)

- Overall `success`: **True**
- Rows checked: `24`

| Expectation | Column | Success | Observed |
| --- | --- | :---: | --- |
| `expect_table_row_count_to_be_between` | - | True | 24 |
| `expect_column_values_to_not_be_null` | paper_id | True | N/A |
| `expect_column_values_to_be_unique` | paper_id | True | N/A |
| `expect_column_values_to_not_be_null` | title | True | N/A |
| `expect_column_value_lengths_to_be_between` | summary | True | N/A |

## 4. Freshness SLA

| Field | Value |
| --- | --- |
| `latest_published` | 2026-09-15 |
| `oldest_published` | 2026-04-01 |
| `stale_rows` | 0 |
| `unknown_published_rows` | 2 |
| `total_rows` | 24 |
| `stale_ratio` | 0.0000 |
| `freshness_threshold_days` | 180 |
| `is_fresh` | True |

- SLA rule: `is_fresh = False` when the ratio of rows with `age_days > 180` exceeds 25%.
