# Corruption & Repair Report — Three-State Comparison

> Baseline vs Corrupted vs Repaired. Repair is idempotent: it re-derives the clean dataset directly from the trusted raw snapshot instead of patching corrupted rows.

## 1. Performance Comparison

| Metric | Baseline | Corrupted | Repaired | Corruption delta | Recovery |
| --- | ---: | ---: | ---: | ---: | ---: |
| `retrieval_hit_rate` | 1.0000 | 0.5000 | 1.0000 | -0.5000 | 100.0% |
| `mean_token_f1` | 1.0000 | 0.4456 | 1.0000 | -0.5544 | 100.0% |
| `judge_accuracy` | 1.0000 | 0.4000 | 1.0000 | -0.6000 | 100.0% |
| `mean_judge_score` | 5 | 2.6000 | 5 | -2.4000 | 100.0% |

- Baseline samples: `10`
- Corrupted samples: `10`
- Repaired samples: `10`

## 2. Data Quality & Freshness

| Signal | Corrupted | Repaired |
| --- | :---: | :---: |
| GX `success` | False | True |
| Failed expectations | 2 | 0 |
| Freshness `is_fresh` | False | True |
| Stale rows | 6 | 0 |
| Total rows | 22 | 24 |

- Corrupted quality gate failed on: `expect_column_values_to_be_unique`, `expect_column_value_lengths_to_be_between`

## 3. Conclusions

1. **Corruption → quality/freshness signal → agent metrics.** Dropping the newest records and blanking/noising summaries removed gold documents from the index and corrupted answer text, so `retrieval_hit_rate`, `mean_token_f1`, and the judge metrics all fell while the GX uniqueness/length checks and the freshness SLA flipped to fail.
2. **Repair action → quality/freshness recovery → agent metrics recovery.** Rebuilding the clean dataframe from `data/raw/crossref_records.json` restores the document set and the quality gate passes again, bringing retrieval and answer metrics back to baseline.

## 4. Interpretation Notes

- The corrupted run uses the same evaluation set as baseline and repaired, so the only variable is data quality; this keeps the comparison causal rather than confounded.
- A recovery of `100%` means the repaired metric returned to its baseline value; `N/A` means the corruption did not change that metric (no denominator).
