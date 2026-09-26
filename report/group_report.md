# Group Report — Day 10: Data Pipeline & Data Observability

> Báo cáo chung của nhóm 5 thành viên cho bài lab Data Pipeline & Data Observability.

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K4              |
| Tên nhóm         | 67     |
| Repository         | https://github.com/huy20/K4-L3B-DAY10-67-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26               |

### Thành viên và phân công

> **Mô hình làm việc:** mỗi thành viên **độc lập triển khai trọn vẹn pipeline** trên nhánh riêng; Trưởng nhóm đánh giá, chọn bản tốt nhất và hợp nhất vào `main`. Vì vậy mọi thành viên đều sở hữu đầy đủ các module.

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Phùng Quang Minh Huy | 2A202602610 | Trưởng nhóm — Full-pipeline + Đánh giá & Hợp nhất | Toàn bộ pipeline; chịu trách nhiệm chọn & merge bản tốt nhất vào `main` |
| 2 | Lưu Nguyên Khôi | 2A202602547 | Full-pipeline implementer | Toàn bộ pipeline (ingestion, cleaning, index, evaluation, observability, corruption/repair, reporting) |
| 3 | Chu Thùy Dương | 2A202602660 | Full-pipeline implementer | Toàn bộ pipeline (ingestion, cleaning, index, evaluation, observability, corruption/repair, reporting) |
| 4 | Nguyễn Minh Hiếu | 2A202602669 | Full-pipeline implementer | Toàn bộ pipeline (ingestion, cleaning, index, evaluation, observability, corruption/repair, reporting) |
| 5 | Phan Đại Cương | 2A202602510 | Full-pipeline implementer | Toàn bộ pipeline (ingestion, cleaning, index, evaluation, observability, corruption/repair, reporting) |

### Quy trình đánh giá & hợp nhất

- Mỗi thành viên chạy đủ 6 checkpoint trên bản của mình và nộp commit riêng.
- Trưởng nhóm đối chiếu theo thứ tự ưu tiên: (1) pipeline chạy end-to-end không lỗi, (2) GX `success=True` + freshness đúng ngữ nghĩa, (3) bộ artifact/metrics đầy đủ và khớp report, (4) idempotency của repair (`repair_log.json`).
- Bản hợp nhất được chọn là bản đáp ứng đủ cả 4 tiêu chí và có số liệu baseline ổn định nhất; các thành viên khác vẫn giữ commit của mình để đối chiếu.

## 2. Tóm tắt kết quả

Nhóm tổ chức theo mô hình **5 bản triển khai độc lập**: mỗi thành viên tự hoàn thành trọn vẹn luồng dữ liệu end-to-end cho hệ thống RAG, sau đó Trưởng nhóm đánh giá và hợp nhất bản tốt nhất vào `main`. Luồng dữ liệu gồm: thu thập 24 metadata bài báo từ Crossref (kèm fallback snapshot offline), làm sạch và mô hình hóa pre-embed, nạp vector vào ChromaDB, sinh bộ test set 10 câu hỏi, và dựng Data Quality Gate theo Great Expectations 1.x kèm Freshness SLA. Baseline pipeline chạy ổn định với `retrieval_hit_rate = 1.0` và `mean_token_f1 = 1.0` trên 24 tài liệu sạch. Nhóm sau đó tiêm 6 kịch bản corruption có kiểm soát (seed cố định): chất lượng sụt rõ rệt — `retrieval_hit_rate` còn 0.5, `mean_token_f1` còn 0.4456, GX gate chuyển `success=False` và freshness vi phạm (6/22 dòng stale, 27.3% > 25%). Corruption ảnh hưởng nặng nhất là **drop latest records**, vì 5 tài liệu mới nhất bị xóa đúng là gold document của các câu hỏi `summary`/`authors`. Cơ chế Idempotent Repair tái dựng dữ liệu sạch từ raw snapshot đưa mọi chỉ số về lại baseline (recovery 100%), với bằng chứng fingerprint `baseline == repaired` trong `repair_log.json`. Blocker chính còn lại là phụ thuộc LLM judge bên ngoài (API key hết quota trả về 429), đã được xử lý bằng cờ `RUN_LLM_JUDGE` để evaluation chạy tất định.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API
    -> raw response/raw records
    -> cleaning và data modeling
    -> embedding + ChromaDB index
    -> evaluation baseline
    -> quality/freshness reports
    -> corruption
    -> re-index và re-evaluate
    -> repair từ dữ liệu nguồn
    -> comparison report
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref REST API / snapshot | Fetch, retry/backoff 429/503, parse `PaperRecord` | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Tất cả thành viên |
| Cleaning          | 24 raw records | Chuẩn hóa text, khử trùng lặp, `age_days`, `text_for_embedding` | `data/clean/papers_clean.{csv,json}` | Tất cả thành viên |
| Embedding/index   | Clean dataframe | `all-MiniLM-L6-v2` + ChromaDB cosine | `data/chroma/`, collections `papers-*` | Tất cả thành viên |
| Evaluation        | Clean dataframe | Test set 10 câu, Hit Rate + token-F1 | `data/eval/test_set.json`, `data/results/*_metrics.json` | Tất cả thành viên |
| Observability     | Clean dataframe | GX 1.x suite + Freshness SLA | `data/quality/*`, `data/quality/gx/*` | Tất cả thành viên |
| Corruption/repair | Clean dataframe + raw | 6 lỗi có seed, tái dựng từ raw | `corruption_log.json`, `repair_log.json` | Tất cả thành viên |
| Orchestration     | Tất cả artifacts | Điều phối, kiểm tra nhất quán, idempotency | `phase1_report.md`, `corruption_report.md` | Phùng Quang Minh Huy (hợp nhất) |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | `gemini` (judge tắt mặc định, dùng heuristic tất định) |
| `LLM_MODEL`                | `gemini-2.5-flash` |
| Embedding model              | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | `24` |
| Retrieval`top_k`           | `4` |
| Freshness threshold          | `180` ngày (ngưỡng stale ratio 25%) |
| Random seed, nếu có        | `42` |

Không dán nội dung API key hoặc file `.env` vào báo cáo.

### Lệnh cài đặt

```bash
python -m pip install -e .
```

### Lệnh chạy

Baseline:

```bash
python script/run_phase1.py
```

Corruption flow:

```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái                                    | Thời điểm chạy gần nhất | Bằng chứng                         |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công | 2026-09-26 | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow   | Thành công | 2026-09-26 | `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`, `data/reports/corruption_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref REST API (`https://api.crossref.org/works`) |
| Query/filter                | `agentic retrieval augmented generation large language model`; `from-pub-date:2026-03-30,has-abstract:true` |
| Thời điểm lấy dữ liệu | 2026-09-26 |
| Số record nhận được    | 24 |
| Cơ chế retry/backoff      | Retry 3 lần, backoff `2^n` giây cho `429/503`, fallback snapshot khi thất bại |

### Raw và clean schema

| Trường        | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa   | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| `paper_id`    | string        | Có | DOI định danh tài liệu | Loại dòng nếu rỗng; khử trùng lặp |
| `title`       | string        | Có | Tiêu đề bài báo | Loại dòng nếu rỗng; strip tag/whitespace |
| `summary`     | string        | Có | Abstract đã làm sạch | Loại dòng nếu < 20 ký tự |
| `authors`     | list[string]  | Không | Danh sách tác giả | Ghép thành `authors_joined` |
| `categories`  | list[string]  | Không | Chủ đề Crossref `subject` | Fallback `Uncategorized` khi rỗng |
| `published`   | date string   | Không | Ngày xuất bản | `age_days` để trống (unknown); 2/24 record thiếu |
| `age_days`    | int64         | Không | Số ngày kể từ `published` đến run date | Nullable khi thiếu ngày |

### Quy tắc cleaning

| Quy tắc                                 | Quality dimension liên quan | Số record bị tác động | Cách xác minh      |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| Loại tag JATS/XML và chuẩn hóa whitespace | Validity/Consistency | 24 | `data/clean/papers_clean.json` |
| Khử trùng lặp theo `paper_id` | Uniqueness | 0 (không có trùng ở raw) | `baseline_quality_report.json` (unique pass) |
| Loại dòng thiếu `paper_id`/`title`/`summary` hoặc summary < 20 ký tự | Completeness | 0 | Số dòng clean = 24 |
| Fallback category rỗng thành `Uncategorized` | Completeness | 24 | Cột `categories_joined` |
| Đánh dấu `published` thiếu là unknown (không tính stale) | Timeliness | 2 | `freshness_report.json` (`unknown_published_rows = 2`) |

Giải thích cách nhóm tạo `text_for_embedding`, document ID và `age_days`:

- `text_for_embedding` gồm đúng 5 phần: `Title`, `Authors`, `Published`, `Categories`, `Summary`, nối bằng ký tự xuống dòng — đảm bảo cả 4 nhóm câu hỏi đều có tín hiệu truy hồi.
- Document ID (Chroma `record_id`) là `"{paper_id}::{index}"` để vẫn duy nhất ngay cả khi có dòng trùng do corruption.
- `age_days = (run_date − published).days`; với dòng thiếu ngày xuất bản thì để trống và đếm riêng là `unknown`.

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 10 |
| Các`question_type`                    | `summary` (3), `authors` (3), `date` (2), `categories` (2) |
| Ground-truth document ID                 | Lấy trực tiếp `paper_id` của tài liệu nguồn (`ground_truth_doc_ids`) |
| Embedding model                          | `sentence-transformers/all-MiniLM-L6-v2` (384 chiều) |
| Vector store/collection                  | ChromaDB cosine: `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Retrieval`top_k`                       | 4 |
| LLM provider/model                       | `gemini` / `gemini-2.5-flash` (judge gated, mặc định heuristic) |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` |

Giải thích vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:

Test set là biến cố định duy nhất để cô lập tác động của chất lượng dữ liệu. Nếu thay đổi câu hỏi giữa các trạng thái, chênh lệch metric không thể quy cho corruption/repair mà bị nhiễu bởi độ khó của câu hỏi.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records     | `data/raw/`                          | Có | 24 bài, `crossref_response.json` + `crossref_records.json` |
| Cleaned dataset          | `data/clean/`                        | Có | 24 dòng, có `text_for_embedding` |
| Embedding manifest/index | `data/embeddings/`, `data/chroma/`   | Có | 24 docs, collection `papers-baseline` |
| Evaluation set           | `data/eval/`                         | Có | 10 câu hỏi |
| Baseline metrics         | `data/results/baseline_metrics.json` | Có | Hit Rate + token-F1 |
| Quality/freshness        | `data/quality/`                      | Có | GX `success=True`, `is_fresh=True` |
| Baseline report          | `data/reports/phase1_report.md`      | Có | Sinh tự động |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` |            1.0 | Mọi câu hỏi đều truy hồi đúng tài liệu nguồn |
| `mean_token_f1`      |            1.0 | Câu trả lời trùng khớp ground-truth |
| `judge_accuracy`     |            1.0 | Toàn bộ câu được đánh giá đúng |
| `mean_judge_score`   |              5 | Điểm judge tối đa |
| Ragas, nếu có        | N/A (skipped) | Chưa bật `RUN_RAGAS=1` |

## 8. Data quality và freshness

### Quality checks

| Check        | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline      | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| `ExpectTableRowCountToBeBetween` | Completeness | 1–10000 dòng | Pass (24) | `data/quality/baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` (`paper_id`) | Completeness | 0 null | Pass | `data/quality/baseline_quality_report.json` |
| `ExpectColumnValuesToBeUnique` (`paper_id`) | Uniqueness | 0 trùng | Pass (baseline); Fail (corrupted) | `data/quality/corrupted_quality_report.json` |
| `ExpectColumnValueLengthsToBeBetween` (`summary`) | Validity | 20–20000 ký tự | Pass (baseline); Fail (corrupted) | `data/quality/corrupted_quality_report.json` |

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | Cột `age_days` của clean dataset |
| Timestamp mới nhất       | `2026-09-15` |
| Ngưỡng freshness         | `age_days > 180`, ngưỡng stale ratio 25% |
| Trạng thái baseline      | Fresh (`is_fresh = True`) |
| Lý do                     | 0/24 dòng stale (2 dòng thiếu ngày được đếm riêng là unknown) |

## 9. Corruption scenarios và repair

| Corruption         | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair   |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| `drop_latest_records` | Xóa 20% bản ghi mới nhất | 5 | Retrieval giảm | 5 gold doc bị mất → Hit Rate 1.0→0.5 | Tái dựng từ raw |
| `blank_summary` | Đặt summary rỗng | 4 | GX length fail | Token-F1 giảm | Tái dựng từ raw |
| `inject_noise` | Chèn ký tự rác vào summary | 4 | Answer quality giảm | Câu trả lời nhiễu | Tái dựng từ raw |
| `truncate_title` | Cắt title < 8 ký tự | 3 | Exact lookup hỏng | Truy hồi bằng title kém chính xác | Tái dựng từ raw |
| `stale_date` | Lùi ngày về `2024-01-01` | 4 | Freshness fail | 6/22 stale (27.3%) | Tái dựng từ raw |
| `duplicate_rows` | Nhân bản dòng | 3 | GX unique fail | Tổng 24→22 (sau drop) + 3 nhân bản | Tái dựng từ raw |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Log ghi đủ 6 kịch bản, mỗi kịch bản có tham số (ratio, seed 42), số dòng bị ảnh hưởng và danh sách `paper_id` cụ thể.

Giải thích cách repair đảm bảo dữ liệu được phục hồi từ nguồn đáng tin cậy thay vì chỉ che kết quả lỗi:

Repair không vá các dòng bị hỏng mà tái dựng toàn bộ dataframe sạch từ raw snapshot `data/raw/crossref_records.json` bằng chính hàm cleaning của baseline. Vì vậy kết quả là tất định và idempotent: chạy hai lần cho ra dữ liệu giống nhau, và repaired fingerprint trùng baseline.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét   |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate`   |     1.0 |      0.5 |     1.0 | -0.50 | 100% | Mất gold doc do drop latest |
| `mean_token_f1`        |     1.0 |   0.4456 |     1.0 | -0.5544 | 100% | Summary bị xóa/nhiễu |
| `judge_accuracy`       |     1.0 |      0.4 |     1.0 | -0.60 | 100% | Cùng xu hướng token-F1 |
| `mean_judge_score`     |       5 |      2.6 |       5 | -2.40 | 100% | Giảm hơn 2 bậc |
| Quality checks pass/fail |  Pass (True) | Fail (False) | Pass (True) | 2 expectation fail | Phục hồi | Unique + summary length |
| Freshness status         |  Fresh (True) | Stale (False) | Fresh (True) | 6/22 stale (27.3%) | Phục hồi | Stale date |

Nêu ít nhất hai kết luận có quan hệ nhân quả được hỗ trợ bởi artifacts:

1. **Drop latest + blank/noise summary → GX/freshness signal thay đổi → retrieval/answer metric sụt:** Gold document bị xóa khỏi index và nội dung trả lời bị hỏng khiến `retrieval_hit_rate` 1.0→0.5 và `mean_token_f1` 1.0→0.4456, đồng thời GX `success=False` và `is_fresh=False`.
2. **Repair tái dựng từ raw → quality/freshness phục hồi → metric phục hồi:** Sau repair, GX `success=True`, `is_fresh=True`, và các metric trở lại baseline với mức phục hồi 100%.

Không kết luận corruption “có tác động” nếu số liệu không cho thấy thay đổi. Hai record thiếu `published` được đếm là unknown (không phải stale), nên ngưỡng freshness của dữ liệu corrupted chỉ vượt nhẹ 27.3% so với 25% — đã kiểm tra bằng `data/quality/corrupted_freshness_report.json`.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Evaluation treo khoảng 37 giây cho mỗi câu hỏi judge và có thể timeout toàn bộ luồng; log trả về `GoogleRateLimitError ... (RESOURCE_EXHAUSTED): 429`.
- **Nguyên nhân:** API key Gemini đã hết quota free-tier, nhưng `ChatGoogleGenerativeAI` vẫn retry kèm backoff nên mỗi lời gọi LLM judge bị block lâu trước khi rơi vào fallback heuristic.
- **Cách xử lý:** Đưa LLM judge ra sau cờ `RUN_LLM_JUDGE` (mặc định tắt → dùng heuristic token-F1 tất định), theo đúng pattern `RUN_RAGAS` sẵn có trong `src/evaluation/metrics.py`.
- **Cách xác minh:** `python script/run_corruption_flow.py` chạy hết end-to-end và in bảng 3 trạng thái; `data/results/repaired_metrics.json` được sinh đầy đủ.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng   | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Phụ thuộc LLM judge ngoài | Evaluation có thể chậm/không ổn định khi hết quota | Giữ judge tùy chọn + thêm timeout cứng; bật `RUN_LLM_JUDGE=1` khi có key hợp lệ |
| Crossref snapshot không có `subject` | Nhóm câu hỏi `categories` chỉ có giá trị `Uncategorized` | Bổ sung nguồn category khác hoặc suy luận category từ nội dung |
| Chưa có CI tự động | Bất biến dễ vỡ khi sửa code | Thêm pytest + GitHub Actions kiểm tra 24 dòng, unique `paper_id`, 10 câu hỏi (bonus B3) |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
