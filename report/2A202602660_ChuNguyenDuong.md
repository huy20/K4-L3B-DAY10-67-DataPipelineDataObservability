# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Chu Nguyên Dương |
| MSSV               | 2A202602660 |
| Khóa/Lớp         | K4 |
| Tên nhóm         | 67     |
| Vai trò chính    | Full-pipeline implementer |
| Repository         | https://github.com/huy20/K4-L3B-DAY10-67-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

> Nhóm làm theo mô hình mỗi thành viên triển khai trọn vẹn pipeline; tôi sở hữu toàn bộ các module dưới đây ở bản của mình.

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ----------- |
| Ingestion & Data Lineage | `src/ingestion/crossref.py` | Crossref API / snapshot | `data/raw/*.json` (24 bài) | Hoàn thành |
| Cleaning & pre-embed | `src/ingestion/cleaning.py` | Raw records, `run_date` | `data/clean/papers_clean.{csv,json}` | Hoàn thành |
| Data Observability (GX 1.x + Freshness) | `src/observability/quality.py::run_data_quality_checks`, `build_freshness_report` | Clean dataframe, `Settings` | `data/quality/*_quality_report.json`, `data/quality/gx/*_suite.json`, freshness reports | Hoàn thành |
| Benchmark Evaluation | `src/evaluation/testset.py` | Clean dataframe | `data/eval/test_set.json` (10 câu) | Hoàn thành |
| Baseline pipeline | `src/pipelines/phase1.py` | Raw records, `Settings` | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` | Hoàn thành |
| Corruption suite | `src/ingestion/corruption.py` | Clean dataframe | `data/results/corruption_log.json` | Hoàn thành |
| Idempotent Repair & comparison | `src/pipelines/corruption_flow.py`, `src/observability/reporting.py` | Raw records, baseline artifacts | `data/results/repaired_metrics.json`, `data/reports/corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Chuẩn hóa báo cáo quality/freshness | `src/observability/reporting.py` | Bảng GX + freshness trong `phase1_report.md` |
| Đối chiếu ngưỡng freshness | Toàn nhóm | Thống nhất `age_days > 180`, stale ratio 25% |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Thiết lập GX 1.x suite | `src/observability/quality.py` | 4 expectation thiết yếu, baseline `success=True` | `data/quality/baseline_quality_report.json` |
| Freshness SLA | `quality.py::build_freshness_report` | `is_fresh` theo tỷ lệ stale | `data/quality/freshness_report.json` |
| Quality trên dữ liệu bẩn | `quality.py` + corruption | Corrupted `success=False` (unique + length) | `data/quality/corrupted_quality_report.json` |
| End-to-end + repair | `src/pipelines/*` | 3 trạng thái, repaired quality pass | 2 script entrypoint |

Output cụ thể: `data/quality/corrupted_quality_report.json` chỉ rõ 2 expectation fail (`expect_column_values_to_be_unique`, `expect_column_value_lengths_to_be_between`) — bằng chứng Data Quality Gate chặn được dữ liệu bẩn.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Dựng một chốt kiểm dịch chất lượng tự động theo đúng chuẩn **Great Expectations 1.x** (không dùng cú pháp cũ gây crash) và bổ sung Freshness SLA để phát hiện cả lỗi cấu trúc lẫn lỗi "quá cũ".

### Cách triển khai

- **Ephemeral context:** `gx.get_context(mode="ephemeral")` → `data_sources.add_pandas("papers_source")` → `add_dataframe_asset("papers_asset")` → `add_batch_definition_whole_dataframe("papers_batch")` → `get_batch(batch_parameters={"dataframe": df})`.
- **Suite:** `gx.ExpectationSuite` + `add_expectation` cho 4 loại thiết yếu: row count, not-null, unique `paper_id`, độ dài `summary`; lưu JSON bằng `suite.to_json_dict()` để làm bằng chứng.
- **Validation:** `batch.validate(suite)` trả về `success` và `results`; tôi trích `observed_value` của từng expectation để ghi report.
- **Freshness:** đếm tỷ lệ `age_days > 180`; `is_fresh=False` khi vượt 25%; tách riêng `unknown_published_rows`.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Clean dataframe (24 cột dẫn xuất), `Settings.freshness_threshold_days = 180` |
| Output                         | `data/quality/<state>_quality_report.json`, `data/quality/gx/<state>_suite.json`, `_freshness_report.json` |
| Module phụ thuộc             | `core/config.py`, `core/utils.py` |
| Module sử dụng output        | `observability/reporting.py`, `pipelines/*` |
| Điều kiện lỗi cần xử lý | Cú pháp GX cũ, `age_days` NA, dataframe rỗng |

### Cách xác minh

```bash
python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); print(run_data_quality_checks(df, s, 'test')['success'])"
```

- **Kết quả mong đợi:** `True`.
- **Kết quả thực tế:** `True`; trên dữ liệu corrupted trả `False` với 2 expectation fail.
- **Artifact/log:** `data/quality/`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Great Expectations đã đổi API ở 1.x; tài liệu/nhiều ví dụ cũ dùng `create_expectation_suite` / datasource kiểu cũ dễ gây crash.
- **Các phương án đã cân nhắc:** (A) ghim Great Expectations phiên bản 0.x để dùng cú pháp cũ; (B) dùng đúng cú pháp 1.x với ephemeral context và `ExpectationSuite`.
- **Phương án đã chọn:** (B).
- **Lý do:** đúng yêu cầu rubric (không dùng cú pháp cũ), không phải hạ cấp dependency, và API 1.x ổn định hơn cho pandas dataframe.
- **Bằng chứng:** `run_data_quality_checks` chạy không lỗi và `baseline_quality_report.json` có `success=true` cùng 5 expectation.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** lỗi khi khởi tạo datasource/suite theo cú pháp GX 0.x (`create_expectation_suite` deprecated, `get_validator` yêu cầu `BatchRequest`).
- **Nguyên nhân gốc:** phiên bản `great-expectations>=1.16` đã bỏ API cũ, thay bằng data source/asset/batch definition mới.
- **Cách xử lý:** chuyển sang chuỗi `add_pandas → add_dataframe_asset → add_batch_definition_whole_dataframe → get_batch`, dùng `ExpectationSuite.add_expectation` và `batch.validate(suite)`.
- **Cách xác minh sau khi sửa:** `run_data_quality_checks` trả `success=True` trên baseline và `False` trên corrupted.
- **Điều học được:** phải bám phiên bản thư viện khi viết observability; lưu suite JSON để tái lập kiểm định.

## 7. Hiểu biết về luồng end-to-end

1. **Crossref → vector index:** API/snapshot → parse → clean → MiniLM + Chroma `papers-baseline`.
2. **Evaluation set:** 10 câu/4 nhóm; hit nếu id truy hồi nằm trong `ground_truth_doc_ids`; token-F1 so `ground_truth`.
3. **Quality vs freshness:** quality kiểm tra cấu trúc/đầy đủ/hợp lệ; freshness kiểm tra chiều thời gian — hai lớp bổ sung.
4. **Cùng test set:** cô lập biến duy nhất là chất lượng dữ liệu.
5. **Repair thành công:** GX `success=True`, freshness True, fingerprint trùng baseline, metrics về baseline.

## 8. Phân tích kết quả

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét |
| ---------------------- | -------: | --------: | -------: | -------- |
| `retrieval_hit_rate` |     1.0 |      0.5 |     1.0 | Mất 5 gold doc |
| `mean_token_f1`      |     1.0 |   0.4456 |     1.0 | Summary hỏng |
| `judge_accuracy`     |     1.0 |      0.4 |     1.0 | Cùng xu hướng |
| `mean_judge_score`   |       5 |      2.6 |       5 | Giảm hơn 2 bậc |
| Quality checks         |    True |     False |     True | Fail unique + length |
| Freshness status       |    True |     False |     True | 6/22 stale (27.3%) |

1. **Corruption → tín hiệu → metric:** duplicate + blank summary → GX fail; stale date → freshness fail; đồng thời hit 1.0→0.5, F1 1.0→0.4456.
2. **Repair → phục hồi → metric:** tái dựng từ raw → GX/freshness pass, metric về baseline.

Quality Gate là tín hiệu phát hiện sớm: **duplicate_rows** kích hoạt unique check và **blank_summary** kích hoạt length check, trong khi **stale_date** chỉ hiện qua freshness — chứng minh cần cả hai lớp. Khác kỳ vọng: freshness vượt ngưỡng khá sát (27.3%).

## 9. Điều học được và hướng cải thiện

1. **Pipeline:** observability nên lưu lại suite/report để tái lập và kiểm toán.
2. **Observability:** GX 1.x cần đúng API mới; quality và freshness bù trừ cho nhau.
3. **RAG:** quality fail là cảnh báo sớm trước khi metric agent sụt.

**Nếu có thêm thời gian:** thêm expectation về category/`published` và dashboard trực quan hoá quality theo thời gian (bonus B1).

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Chu Nguyên Dương
**Ngày xác nhận:** 2026-09-26
