# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Minh Hiếu |
| MSSV               | 2A202602669 |
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
| Data Observability | `src/observability/quality.py` | Clean dataframe, `Settings` | `data/quality/*` | Hoàn thành |
| Benchmark Evaluation | `src/evaluation/testset.py::build_test_set` | Clean dataframe | `data/eval/test_set.json` (10 câu, 4 nhóm) | Hoàn thành |
| Baseline pipeline | `src/pipelines/phase1.py` | Raw records, `Settings` | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` | Hoàn thành |
| Corruption suite | `src/ingestion/corruption.py` | Clean dataframe | `data/results/corruption_log.json` | Hoàn thành |
| Idempotent Repair & comparison | `src/pipelines/corruption_flow.py`, `src/observability/reporting.py` | Raw records, baseline artifacts | `data/results/repaired_metrics.json`, `data/reports/corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Thiết kế ground-truth cho 4 nhóm câu hỏi | `src/evaluation/metrics.py` | Hit Rate + token-F1 đo được |
| Xử lý category rỗng | `src/ingestion/cleaning.py` | Fallback `Uncategorized` nhất quán ground-truth/answer |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Sinh test set 4 nhóm | `src/evaluation/testset.py` | 10 câu: summary 3, authors 3, date 2, categories 2 | `data/eval/test_set.json` |
| Neo câu hỏi theo exact title | `testset.py`, `retrieval/qa.py` | Retrieval hit chính xác, baseline 1.0 | `data/results/baseline_metrics.json` |
| Fallback category | `cleaning.py` | `categories_joined = Uncategorized` | `test_set.json` q-009/q-010 |
| End-to-end + repair | `src/pipelines/*` | 3 trạng thái, repaired về baseline | 2 script entrypoint |

Output cụ thể: `data/eval/test_set.json` gồm 10 câu hỏi có `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids`; baseline `retrieval_hit_rate = 1.0`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Xây một bộ benchmark ổn định, tất định, phủ đủ 4 nhóm nghiệp vụ, để đo cả retrieval lẫn chất lượng câu trả lời và tái sử dụng được cho cả 3 trạng thái.

### Cách triển khai

- **Chọn tài liệu:** dùng con trỏ xoay vòng trên dataframe đã sort để chọn tài liệu tất định, tránh trùng giữa các nhóm; nhóm `date` chỉ chọn tài liệu có `published` hợp lệ.
- **Sinh câu hỏi:** mỗi câu nhúng nguyên văn `title` trong dấu nháy đơn; agent có regex bắt title để exact lookup, nên câu `date`/`categories` vẫn truy hồi đúng bất chấp embedding.
- **Ground-truth:** lấy trực tiếp từ cột đã clean (`authors_joined`, `published`, `categories_joined`, first sentence của `summary`) nên ground-truth luôn khớp với những gì agent trích xuất.
- **Lưu file:** `write_json` ghi `data/eval/test_set.json`.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Clean dataframe (24 dòng) |
| Output                         | JSON list 10 item: `id, question_type, question, ground_truth, ground_truth_doc_ids` |
| Module phụ thuộc             | `core/utils.py`, `ingestion/cleaning.py` |
| Module sử dụng output        | `evaluation/metrics.py`, `pipelines/*`, `retrieval/qa.py` |
| Điều kiện lỗi cần xử lý | `categories` rỗng, `published` thiếu, < 10 tài liệu |

### Cách xác minh

```bash
python -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); print(len(build_test_set(df, s.paths.eval_testset)))"
```

- **Kết quả mong đợi:** `10`.
- **Kết quả thực tế:** `10`; baseline `retrieval_hit_rate=1.0`.
- **Artifact/log:** `data/eval/test_set.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** câu hỏi về `date`/`categories` khó truy hồi bằng semantic search thuần vì giá trị ngắn, ít ngữ nghĩa.
- **Các phương án đã cân nhắc:** (A) chỉ dựa vào semantic search; (B) nhúng nguyên văn title vào câu hỏi để tận dụng exact-title lookup của agent; (C) tự viết retriever riêng.
- **Phương án đã chọn:** (B).
- **Lý do:** tận dụng cơ chế có sẵn, cho kết quả tất định và giải thích được, đồng thời vẫn đo được semantic retrieval khi câu hỏi không khớp title.
- **Bằng chứng:** cả 10 câu đạt `retrieval_hit=true` ở baseline (`baseline_metrics.json`).

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** toàn bộ record có `"categories": []`; câu hỏi `categories` cho ground-truth rỗng khiến `_token_f1` luôn bằng 0 và test vô nghĩa.
- **Nguyên nhân gốc:** Crossref snapshot không trả trường `subject`, nên `categories_joined` rỗng ở mọi tài liệu.
- **Cách xử lý:** chuẩn hóa category rỗng thành sentinel `Uncategorized` ở cleaning; ground-truth và câu trả lời của agent cùng dùng sentinel này nên nhất quán.
- **Cách xác minh sau khi sửa:** q-009/q-010 có `ground_truth="Uncategorized"`, agent trả `Uncategorized`, token-F1 = 1.0.
- **Điều học được:** trường thiếu phải được biểu diễn tường minh trong cả ground-truth lẫn agent, nếu không benchmark sẽ mất tính phân biệt.

## 7. Hiểu biết về luồng end-to-end

1. **Crossref → vector index:** API/snapshot → parse → clean → MiniLM + Chroma `papers-baseline`.
2. **Evaluation set:** 10 câu/4 nhóm; hit nếu id truy hồi nằm trong `ground_truth_doc_ids`; token-F1 so `ground_truth`.
3. **Quality vs freshness:** quality kiểm tra cấu trúc/đầy đủ/hợp lệ; freshness kiểm tra chiều thời gian.
4. **Cùng test set:** cô lập biến duy nhất là chất lượng dữ liệu.
5. **Repair thành công:** fingerprint trùng baseline + GX/freshness pass + metrics về baseline.

## 8. Phân tích kết quả

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét |
| ---------------------- | -------: | --------: | -------: | -------- |
| `retrieval_hit_rate` |     1.0 |      0.5 |     1.0 | Drop latest xoá đúng gold doc |
| `mean_token_f1`      |     1.0 |   0.4456 |     1.0 | Summary hỏng |
| `judge_accuracy`     |     1.0 |      0.4 |     1.0 | Cùng xu hướng |
| `mean_judge_score`   |       5 |      2.6 |       5 | Giảm hơn 2 bậc |
| Quality checks         |    True |     False |     True | Fail unique + length |
| Freshness status       |    True |     False |     True | 6/22 stale (27.3%) |

1. **Corruption → tín hiệu → metric:** drop latest (mất gold doc của câu summary/authors) + blank/noise summary → hit 1.0→0.5, F1 1.0→0.4456.
2. **Repair → phục hồi → metric:** tái dựng từ raw → metric về baseline (recovery 100%).

Corruption ảnh hưởng nhất tới benchmark: **drop_latest_records** vì trùng đúng các `ground_truth_doc_ids`; **blank_summary/inject_noise** phá token-F1. Khác kỳ vọng: câu `categories` vẫn đạt nhờ sentinel `Uncategorized`.

## 9. Điều học được và hướng cải thiện

1. **Pipeline:** test set tất định giúp so sánh 3 trạng thái công bằng.
2. **Observability:** ground-truth phải được sinh từ cùng nguồn với agent để tránh lệch.
3. **RAG:** câu hỏi ngắn (date/category) cần cơ chế truy hồi chính xác, không chỉ semantic.

**Nếu có thêm thời gian:** mở rộng test set lên 20–30 câu và thêm nhóm câu hỏi "so sánh nhiều tài liệu".

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Minh Hiếu
**Ngày xác nhận:** 2026-09-26
