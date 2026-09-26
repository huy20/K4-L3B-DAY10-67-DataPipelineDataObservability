# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Phùng Quang Minh Huy |
| MSSV               | 2A202602610 |
| Khóa/Lớp         | K4 |
| Tên nhóm         | 67     |
| Vai trò chính    | Trưởng nhóm — Full-pipeline + Đánh giá & Hợp nhất |
| Repository         | https://github.com/huy20/K4-L3B-DAY10-67-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

> Nhóm làm theo mô hình mỗi thành viên triển khai trọn vẹn pipeline; tôi sở hữu toàn bộ các module dưới đây ở bản của mình, đồng thời chịu trách nhiệm đánh giá và hợp nhất bản tốt nhất vào `main`.

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ----------- |
| Ingestion & Data Lineage | `src/ingestion/crossref.py` | Crossref API / snapshot | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` (24 bài) | Hoàn thành |
| Cleaning & pre-embed | `src/ingestion/cleaning.py::build_clean_dataframe` | Raw records, `run_date` | `data/clean/papers_clean.{csv,json}` (24 dòng) | Hoàn thành |
| Data Observability | `src/observability/quality.py::run_data_quality_checks`, `build_freshness_report` | Clean dataframe, `Settings` | `data/quality/*`, `data/quality/gx/*_suite.json` | Hoàn thành |
| Benchmark Evaluation | `src/evaluation/testset.py::build_test_set` | Clean dataframe | `data/eval/test_set.json` (10 câu, 4 nhóm) | Hoàn thành |
| Baseline pipeline | `src/pipelines/phase1.py::main` | Raw records, `Settings` | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` | Hoàn thành |
| Corruption suite | `src/ingestion/corruption.py::corrupt_clean_dataframe` | Clean dataframe | `data/results/corruption_log.json`, `data/clean/papers_clean_corrupted.{csv,json}` | Hoàn thành |
| Idempotent Repair & comparison | `src/pipelines/corruption_flow.py::main`, `src/observability/reporting.py` | Raw records, baseline artifacts | `data/results/repaired_metrics.json`, `data/results/repair_log.json`, `data/reports/corruption_report.md` | Hoàn thành |
| Cấu hình & tiện ích | `src/core/config.py`, `src/core/utils.py` | `.env`, project paths | `Settings`/`Paths`, `write_dataframe()` | Hoàn thành |
| Đánh giá & hợp nhất | GitHub nhánh `main`, `report/group_report.md` | 5 bản triển khai độc lập | Bản hợp nhất chạy end-to-end, 100% thành viên có commit | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Gate LLM judge sau `RUN_LLM_JUDGE` | `src/evaluation/metrics.py` | Evaluation tất định, không treo khi key hết quota |
| Đối chiếu artifact 3 trạng thái | Toàn nhóm | Metrics trong report khớp `data/results/` |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Baseline end-to-end | `src/pipelines/phase1.py` | 24 docs, `retrieval_hit_rate=1.0` | `python script/run_phase1.py` |
| Corruption + đo suy giảm | `src/ingestion/corruption.py` | 6 lỗi, hit rate 1.0→0.5 | `data/results/corruption_log.json` |
| Idempotent Repair + báo cáo 3 trạng thái | `src/pipelines/corruption_flow.py` | Recovery 100%, `idempotent=true` | `python script/run_corruption_flow.py` |
| Chọn & hợp nhất bản tốt nhất | GitHub `main`, `report/group_report.md` | Bản hợp nhất đầy đủ artifact | `git log`, `Insights > Contributors` |

Output cụ thể: `python script/run_corruption_flow.py` in bảng 3 trạng thái (Baseline/Corrupted/Repaired) với `idempotent_repair: True`, và `data/results/repair_log.json` chứng minh `baseline == repaired`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Xây dựng trọn vẹn một pipeline dữ liệu cho RAG (ingest → clean → index → evaluate → observe) và chứng minh bằng số liệu rằng dữ liệu bẩn gây suy giảm chất lượng (Silent Failure) rồi có thể phục hồi idempotent từ nguồn gốc; sau đó điều phối việc chọn lọc giữa 5 bản triển khai độc lập.

### Cách triển khai

- **Ingestion:** gọi Crossref REST API với retry/backoff cho `429/503`, fallback đọc snapshot khi mất mạng; parse `PaperRecord` và lưu raw artifacts.
- **Cleaning:** strip tag JATS/XML + whitespace, khử trùng lặp theo `paper_id`, tính `age_days`, ghép `text_for_embedding` 5 phần (`Title/Authors/Published/Categories/Summary`).
- **Observability:** GX 1.x ephemeral context + 4 expectation thiết yếu; freshness theo tỷ lệ `age_days > 180` (ngưỡng 25%); lưu suite JSON.
- **Evaluation:** test set 10 câu qua 4 nhóm, neo theo exact title; `retrieval_hit` + token-F1 + judge tùy chọn.
- **Corruption/Repair:** 6 kịch bản có seed 42; repair **tái dựng từ raw** thay vì vá tại chỗ, chạy 2 lần để chứng minh idempotent, fingerprint SHA-256.
- **Orchestration:** `corruption_flow.py` tự chứa (auto chạy baseline nếu thiếu) để một lệnh tái lập cả 3 trạng thái.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | `data/raw/crossref_records.json`, `Settings` |
| Output                         | 3 bộ metrics/answers, 3 collection Chroma, `repair_log.json`, 2 báo cáo markdown |
| Module phụ thuộc             | `core/`, `ingestion/`, `retrieval/`, `observability/`, `evaluation/` |
| Module sử dụng output        | `report/group_report.md`, các `report/*.md` |
| Điều kiện lỗi cần xử lý | Thiếu `published` (2/24), categories rỗng (24/24), mất mạng, API key hết quota |

### Cách xác minh

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** baseline 1.0; corrupted giảm; repaired về baseline; `idempotent_repair: True`.
- **Kết quả thực tế:** đúng như mong đợi; fingerprint không đổi khi chạy lại.
- **Artifact/log:** `data/reports/`, `data/results/`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** cần chọn cách điều phối để một lệnh tái lập cả 3 trạng thái và kết quả độc lập với thứ tự chạy.
- **Các phương án đã cân nhắc:** (A) bắt buộc chạy baseline trước; (B) entrypoint tự chứa + repair tái dựng từ raw.
- **Phương án đã chọn:** (B).
- **Lý do:** giảm lỗi vận hành và đảm bảo idempotent + lineage.
- **Bằng chứng:** `data/results/repair_log.json` có `idempotent=true`, `repaired_matches_baseline=true`.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `GoogleRateLimitError ... (RESOURCE_EXHAUSTED): 429`.
- **Lệnh tái hiện:** chạy evaluation 10 câu với LLM judge bật; mỗi câu treo ~37 giây.
- **Nguyên nhân gốc:** API key Gemini hết quota nhưng client vẫn retry/backoff trước khi fallback.
- **Cách xử lý:** gate LLM judge sau `RUN_LLM_JUDGE` (mặc định tắt → heuristic token-F1 tất định).
- **Cách xác minh:** `python script/run_corruption_flow.py` chạy hết end-to-end và sinh đủ artifact.
- **Điều học được:** phụ thuộc LLM phải tùy chọn và có fallback tất định để CI/lab tái lập được.

## 7. Hiểu biết về luồng end-to-end

1. **Crossref → vector index:** API/snapshot → `PaperRecord` → cleaning (`age_days`, `text_for_embedding`) → MiniLM + Chroma `papers-baseline`.
2. **Evaluation set:** 10 câu/4 nhóm; `ground_truth_doc_ids` là `paper_id`; hit = có id truy hồi nằm trong ground-truth; token-F1 so câu trả lời.
3. **Quality vs freshness:** quality kiểm tra bất biến cấu trúc/đầy đủ/hợp lệ; freshness kiểm tra chiều thời gian — bổ sung cho nhau.
4. **Cùng test set:** cô lập biến duy nhất là chất lượng dữ liệu để kết luận mang tính nhân quả.
5. **Repair thành công:** fingerprint trùng baseline + GX `success=True` + freshness True + metrics về baseline.

## 8. Phân tích kết quả

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét |
| ---------------------- | -------: | --------: | -------: | -------- |
| `retrieval_hit_rate` |     1.0 |      0.5 |     1.0 | Mất 5 gold doc → nửa số câu miss |
| `mean_token_f1`      |     1.0 |   0.4456 |     1.0 | Summary rỗng/nhiễu |
| `judge_accuracy`     |     1.0 |      0.4 |     1.0 | Cùng xu hướng |
| `mean_judge_score`   |       5 |      2.6 |       5 | Giảm hơn 2 bậc |
| Quality checks         |    True |     False |     True | Fail unique + summary length |
| Freshness status       |    True |     False |     True | 6/22 stale (27.3%) |

1. **Corruption → tín hiệu → metric:** drop latest + blank/noise → hit 1.0→0.5, F1 1.0→0.4456; GX/freshness fail.
2. **Repair → phục hồi → metric:** tái dựng từ raw → GX/freshness pass, metric về baseline (100%).

Corruption ảnh hưởng nhất: **drop_latest_records** (xóa đúng gold doc của câu hỏi summary/authors). Khác kỳ vọng: 2/24 thiếu `published` nên freshness chỉ vượt nhẹ 27.3% > 25%.

## 9. Điều học được và hướng cải thiện

1. **Pipeline:** entrypoint tự chứa + tái dựng từ raw cho pipeline idempotent, tái lập được.
2. **Observability:** quality gate và freshness là hai lớp bổ sung; "sạch" chưa đủ, phải "mới".
3. **RAG:** lỗi dữ liệu gây Silent Failure — agent vẫn trả lời nhưng sai.

**Nếu có thêm thời gian:** thêm auto-repair trigger trên GX fail và pytest CI bảo vệ bất biến.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phùng Quang Minh Huy
**Ngày xác nhận:** 2026-09-26
