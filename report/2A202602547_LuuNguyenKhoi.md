# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Lưu Nguyên Khôi |
| MSSV               | 2A202602547 |
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
| Ingestion & Data Lineage | `src/ingestion/crossref.py` | Crossref API / snapshot | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` (24 bài) | Hoàn thành |
| Cleaning & pre-embed | `src/ingestion/cleaning.py::build_clean_dataframe` | Raw records, `run_date` | `data/clean/papers_clean.{csv,json}` (24 dòng) | Hoàn thành |
| Data Observability | `src/observability/quality.py` | Clean dataframe, `Settings` | `data/quality/*`, `data/quality/gx/*_suite.json` | Hoàn thành |
| Benchmark Evaluation | `src/evaluation/testset.py::build_test_set` | Clean dataframe | `data/eval/test_set.json` (10 câu, 4 nhóm) | Hoàn thành |
| Baseline pipeline | `src/pipelines/phase1.py::main` | Raw records, `Settings` | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` | Hoàn thành |
| Corruption suite | `src/ingestion/corruption.py::corrupt_clean_dataframe` | Clean dataframe | `data/results/corruption_log.json` | Hoàn thành |
| Idempotent Repair & comparison | `src/pipelines/corruption_flow.py`, `src/observability/reporting.py` | Raw records, baseline artifacts | `data/results/repaired_metrics.json`, `data/results/repair_log.json`, `data/reports/corruption_report.md` | Hoàn thành |
| Cấu hình & tiện ích | `src/core/config.py`, `src/core/utils.py` | `.env`, project paths | `Settings`/`Paths`, `write_dataframe()` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Rà soát quy tắc cleaning & xử lý `published` thiếu | Toàn nhóm | 24 dòng clean, freshness đếm đúng unknown |
| Kiểm tra lại cột dẫn xuất sau corruption | `src/ingestion/corruption.py` | `text_for_embedding`/`age_days` được rebuild đúng |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Làm sạch & mô hình hóa pre-embed | `src/ingestion/cleaning.py` | 24 dòng, `text_for_embedding` 5 phần | `data/clean/papers_clean.json` |
| Xử lý ngày thiếu an toàn | `cleaning.py`, `quality.py` | `age_days` nullable, `unknown_published_rows=2` | `data/quality/freshness_report.json` |
| Corruption + rebuild cột dẫn xuất | `src/ingestion/corruption.py` | 6 lỗi, cột dẫn xuất nhất quán | `data/results/corruption_log.json` |
| End-to-end + repair | `src/pipelines/phase1.py`, `corruption_flow.py` | Baseline 1.0 → Corrupted 0.5 → Repaired 1.0 | 2 script entrypoint |

Output cụ thể: `data/clean/papers_clean.json` giữ đủ 24 dòng dù có 2 record thiếu `published`, nhờ để `age_days` trống thay vì bịa ngày.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Biến 24 record thô thành dataframe sạch, giữ đủ dữ liệu nhưng không bịa thông tin, và đảm bảo cột dẫn xuất luôn được cập nhật lại sau corruption.

### Cách triển khai

- **Chuẩn hóa:** regex loại tag JATS/XML và gộp whitespace cho `title`/`summary`; `authors`/`categories` bỏ phần tử rỗng.
- **Khử trùng lặp:** theo `paper_id`, giữ bản ghi đầu tiên.
- **Ngày:** parse `published`/`updated` về UTC; `age_days = (run_date − published).days`, dùng `Int64` nullable nên ngày thiếu = NA thay vì NaN float.
- **`text_for_embedding`:** ghép 5 phần `Title / Authors / Published / Categories / Summary` để embedding có đủ ngữ cảnh cho mọi loại câu hỏi.
- **Sau corruption:** hàm `_rebuild_derived_columns` tính lại `summary_chars`, `text_for_embedding`, `age_days` để tránh dữ liệu dẫn xuất lệch với cột gốc.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | 24 `PaperRecord`, `run_date` (UTC) |
| Output                         | DataFrame 16 cột (`age_days`, `authors_joined`, `categories_joined`, `summary_chars`, `text_for_embedding`) |
| Module phụ thuộc             | `core/config.py`, `core/utils.py` |
| Module sử dụng output        | `retrieval/index.py`, `observability/quality.py`, `evaluation/testset.py` |
| Điều kiện lỗi cần xử lý | `published` rỗng (2/24), `categories` rỗng (24/24), summary rỗng sau corruption |

### Cách xác minh

```bash
python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f'Clean {len(df)} dong')"
```

- **Kết quả mong đợi:** `Clean 24 dong`.
- **Kết quả thực tế:** đúng; `unknown_published_rows=2` trong `freshness_report.json`.
- **Artifact/log:** `data/clean/`, `data/quality/freshness_report.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** 2/24 record không có `published`, cần quyết định cách xử lý để không làm hỏng freshness và không bịa dữ liệu.
- **Các phương án đã cân nhắc:** (A) loại bỏ 2 dòng thiếu ngày; (B) gán một ngày mặc định; (C) giữ dòng, để `age_days = NA` và đếm riêng là "unknown".
- **Phương án đã chọn:** (C).
- **Lý do:** giữ đủ 24 tài liệu (A làm mất dữ liệu) và không bịa ngày (B sai lệch). Loại trừ unknown khỏi công thức stale đúng theo định nghĩa "age_days > 180".
- **Bằng chứng:** `freshness_report.json` có `total_rows=24`, `unknown_published_rows=2`, `stale_rows=0`, `is_fresh=true`.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `age_days` chứa `NaN` khiến kiểu dữ liệu lẫn lộn và freshness tính sai số dòng stale.
- **Nguyên nhân gốc:** pandas biểu diễn ngày thiếu thành `NaT`, phép trừ cho ra `NaN` (float), không phân biệt được "chưa biết" với "rất cũ".
- **Cách xử lý:** ép cột về `Int64` nullable (`df["age_days"] = pd.array(..., dtype="Int64")`) và tách `unknown_published_rows` khỏi `stale_rows`.
- **Cách xác minh sau khi sửa:** `freshness_report.json` và `corrupted_freshness_report.json` hiển thị đúng `unknown_published_rows` mà không lẫn vào stale.
- **Điều học được:** dữ liệu thiếu phải được biểu diễn tường minh (unknown), không để lẫn vào ngưỡng nghiệp vụ.

## 7. Hiểu biết về luồng end-to-end

1. **Crossref → vector index:** API/snapshot → parse → clean (`age_days`, `text_for_embedding`) → MiniLM + Chroma `papers-baseline`.
2. **Evaluation set:** 10 câu/4 nhóm; hit nếu id truy hồi nằm trong `ground_truth_doc_ids`; token-F1 so với `ground_truth`.
3. **Quality vs freshness:** quality kiểm tra cấu trúc/đầy đủ/hợp lệ; freshness kiểm tra chiều thời gian.
4. **Cùng test set:** cô lập biến duy nhất là chất lượng dữ liệu.
5. **Repair thành công:** fingerprint repaired trùng baseline + GX/freshness pass + metrics về baseline.

## 8. Phân tích kết quả

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét |
| ---------------------- | -------: | --------: | -------: | -------- |
| `retrieval_hit_rate` |     1.0 |      0.5 |     1.0 | Mất 5 gold doc |
| `mean_token_f1`      |     1.0 |   0.4456 |     1.0 | Summary hỏng |
| `judge_accuracy`     |     1.0 |      0.4 |     1.0 | Cùng xu hướng |
| `mean_judge_score`   |       5 |      2.6 |       5 | Giảm hơn 2 bậc |
| Quality checks         |    True |     False |     True | Fail unique + length |
| Freshness status       |    True |     False |     True | 6/22 stale (27.3%) |

1. **Corruption → tín hiệu → metric:** drop latest + blank/noise → hit 1.0→0.5, F1 1.0→0.4456; GX/freshness fail.
2. **Repair → phục hồi → metric:** tái dựng từ raw → GX/freshness pass, metric về baseline.

**blank_summary** và **inject_noise** ảnh hưởng trực tiếp nhất tới `mean_token_f1`; **stale_date** đẩy freshness vượt ngưỡng. Khác kỳ vọng: freshness chỉ vượt nhẹ 27.3% do 2 dòng unknown không bị tính stale.

## 9. Điều học được và hướng cải thiện

1. **Pipeline:** cột dẫn xuất phải được rebuild mỗi khi dữ liệu gốc đổi để tránh lệch trạng thái.
2. **Observability:** dữ liệu thiếu cần biểu diễn tường minh và có ngưỡng riêng.
3. **RAG:** summary bị hỏng làm câu trả lời sai dù retrieval có thể vẫn đúng.

**Nếu có thêm thời gian:** thêm validation tường minh cho `published` (parse + cảnh báo) trong cleaning và test tự động cho quy tắc unknown.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Lưu Nguyên Khôi
**Ngày xác nhận:** 2026-09-26
