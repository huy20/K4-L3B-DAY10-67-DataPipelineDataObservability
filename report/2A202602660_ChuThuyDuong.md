# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Chu Thùy Dương |
| MSSV | 2A202602660 |
| Khóa/Lớp | K4 |
| Tên nhóm | 67 |
| Vai trò chính | Triển khai độc lập toàn diện Pipeline (Ingestion, GX 1.x Observability, Corruption Suite, Idempotent Repair) |
| Repository | https://github.com/huy20/K4-L3B-Day10-Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-09-26 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Ingestion & Pre-processing | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py` | `data/raw/crossref_records.json` | `papers_clean.csv`, `papers_clean.json` | Hoàn thành |
| Data Observability & Freshness | `src/observability/quality.py` | DataFrame sạch, cấu hình Settings | `baseline_quality_report.json`, `freshness_report.json` | Hoàn thành |
| Benchmark Test Set & Indexing | `src/evaluation/testset.py`, `src/retrieval/index.py` | Clean DataFrame | `test_set.json`, Chroma collection `papers-baseline` | Hoàn thành |
| Baseline Pipeline & Reporting | `src/pipelines/phase1.py`, `src/observability/reporting.py` | Raw snapshot, cấu hình hệ thống | `baseline_metrics.json`, `phase1_report.md` | Hoàn thành |
| Data Corruption & Repair Flow | `src/ingestion/corruption.py`, `src/pipelines/corruption_flow.py` | Clean dataset, raw records | `corruption_log.json`, `corruption_report.md`, repaired artifacts | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Fix lỗi tương thích Python 3.10 | Toàn bộ các module trong `src/core/` | Xử lý triệt để lỗi import `datetime.UTC` bằng cơ chế fallback về `timezone.utc`, giúp pipeline chạy ổn định trên mọi máy thành viên |
| Đồng bộ Golden Test Set | `src/evaluation/testset.py` | Tự động đồng bộ song song `test_set.json` và `golden_set.json` để vừa khớp lệnh chấm tự động vừa đúng thuật ngữ đánh giá |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Tiền xử lý dữ liệu và cấu trúc hóa embedding | `src/ingestion/cleaning.py` (`build_clean_dataframe`) | Làm sạch 24 bản ghi, khử trùng lặp theo paper_id, sinh cột text_for_embedding chuẩn 5 phần | Chạy lệnh test Checkpoint 1: console in "Clean thành công 24 dòng" |
| Thiết lập Data Quality Gate GX 1.x | `src/observability/quality.py` (`run_data_quality_checks`) | Cấu hình ephemeral context, định nghĩa 4 expectations và Freshness SLA 180 ngày | Quality check status = True trên dữ liệu sạch, tự động block khi có lỗi |
| Tạo bộ câu hỏi đánh giá benchmark | `src/evaluation/testset.py` (`build_test_set`) | Bộ 10 câu hỏi bao phủ 4 nhóm: summary, authors, date, categories | Console in "Sinh được 10 câu hỏi test" tại `data/eval/test_set.json` |
| Đo lường hiệu năng Baseline | `script/run_phase1.py`, `src/pipelines/phase1.py` | Retrieval Hit Rate đạt 100.0%, Mean Token F1 đạt 100.0% | File `data/results/baseline_metrics.json` và báo cáo `phase1_report.md` |
| Tiêm 6 kịch bản lỗi và đo lường suy giảm | `src/ingestion/corruption.py`, `src/pipelines/corruption_flow.py` | Hit Rate giảm từ 100% xuống 50%, Token F1 giảm xuống 75.1%, Quality Gate chuyển BLOCKED | File `corruption_log.json` và `corrupted_metrics.json` |
| Tự phục hồi dữ liệu Idempotent Repair | `script/run_corruption_flow.py` | Phục hồi 100% về mức Hit Rate 100%, F1 100%, Quality Gate PASSED | File `repaired_metrics.json` và bảng đối chiếu tại `corruption_report.md` |

Một output cụ thể chứng minh phần việc hoàn thành:
Bảng đối chiếu định lượng 3 trạng thái tại file `data/reports/corruption_report.md` ghi nhận rõ rệt bước sụt giảm chất lượng của RAG khi dữ liệu bị lỗi (Hit Rate giảm còn 50%) và sự phục hồi tuyệt đối sau khi kích hoạt cơ chế Idempotent Repair từ raw snapshot (Hit Rate trở lại 100%).

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Trong các hệ thống RAG thực tế, lỗi dữ liệu thường diễn ra âm thầm (Silent Failure): dữ liệu bị mất bản ghi mới, rỗng tóm tắt, nhiễu văn bản hoặc vi phạm tính tươi mới nhưng hệ thống không phát sinh lỗi exception khi chạy code. Điều này khiến Agent trả lời sai hoặc không tìm thấy thông tin mà đội ngũ kỹ thuật không hề hay biết. Cần xây dựng chốt chặn tự động (Data Quality Gate) bằng Great Expectations 1.x kết hợp Freshness SLA để phát hiện ngay từ tầng Ingestion, đồng thời thiết kế cơ chế tự phục hồi idempotent khi có sự cố.

### Cách triển khai

1. Xử lý sạch dữ liệu: Sử dụng biểu thức chính quy loại bỏ toàn bộ thẻ JATS XML (`<jats:p>`), chuẩn hóa khoảng trắng, tính độ tuổi bài báo `age_days = (run_date - published).days` và ghép chuỗi `text_for_embedding` theo cấu trúc 5 phần (Title, Authors, Published, Categories, Summary).
2. Thiết lập chốt kiểm dịch Great Expectations 1.x: Khởi tạo context ephemeral nhẹ trong bộ nhớ, kết nối Pandas data source và khai báo 4 Expectations thiết yếu:
   - `ExpectTableRowCountToBeBetween`: kiểm soát số lượng dòng trong ngưỡng cho phép (1 đến 1000).
   - `ExpectColumnValuesToNotBeNull`: kiểm tra không được rỗng trên `paper_id` và `title`.
   - `ExpectColumnValuesToBeUnique`: chặn đứng hiện tượng trùng lặp mã định danh `paper_id`.
   - `ExpectColumnValueLengthsToBeBetween`: đảm bảo trường `summary` có độ dài hợp lệ (10 đến 5000 ký tự).
3. Thiết lập Freshness SLA: Tính toán tỷ lệ các bài báo có `age_days > 180`. Nếu tỷ lệ vượt quá 25% tổng số bản ghi, hệ thống lập tức gán `is_fresh = False` và đánh dấu `success = False` cho Quality Gate.
4. Giả lập lỗi và tự phục hồi: Viết 6 hàm biến đổi mô phỏng dữ liệu bẩn trong sản xuất (xóa 20% bài mới, xóa tóm tắt, chèn nhiễu, cắt ngắn tiêu đề, lùi ngày xuất bản, nhân bản dòng). Sau khi đo lường sự suy giảm, tái nạp dữ liệu sạch từ raw snapshot bất biến và tái tạo Chroma index.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Raw snapshot JSON tại `data/raw/crossref_records.json` chứa 24 bản ghi metadata |
| Output | Dataframe sạch, vector database ChromaDB, bộ testset 10 câu hỏi, báo cáo quality JSON và markdown |
| Module phụ thuộc | `sentence-transformers/all-MiniLM-L6-v2`, `chromadb`, `great_expectations 1.23.2`, `pandas` |
| Module sử dụng output | QA Agent, module đánh giá hiệu năng `evaluate_pipeline`, báo cáo đối chiếu Pha 1 và Pha 2 |
| Điều kiện lỗi cần xử lý | Xử lý dữ liệu thiếu trường, lỗi mạng khi gọi API Crossref (tự động fallback sang file snapshot local), môi trường thiếu key LLM |

### Cách xác minh

```bash
python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(f'Tín hiệu hoàn thành: Clean thành công {len(df)} dòng')"
python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, 'test'); print(f'Tín hiệu hoàn thành: Quality check status = {res.success}')"
```

- **Kết quả mong đợi:** Clean thành công 24 dòng dữ liệu và Quality check status trả về True.
- **Kết quả thực tế:** Console in ra chính xác "Tín hiệu hoàn thành: Clean thành công 24 dòng" và "Tín hiệu hoàn thành: Quality check status = True".
- **Artifact/log:** `data/quality/baseline_quality_report.json`, `data/clean/papers_clean.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương pháp khởi tạo và quản lý cấu hình Great Expectations. Trước đây phiên bản cũ (GX 0.18) yêu cầu khởi tạo thư mục tĩnh `gx/`, lưu context qua file yaml phức tạp và dễ gây crash cú pháp khi chạy trong container hoặc môi trường ảo mới.
- **Các phương án đã cân nhắc:**
  1. Sử dụng FileDataContext truyền thống với cấu hình thư mục tĩnh `data/quality/gx/great_expectations.yml`.
  2. Sử dụng Ephemeral Data Context theo chuẩn mới Great Expectations 1.x (`gx.get_context(mode="ephemeral")`) với Pandas Data Source gắn trực tiếp vào DataFrame trong RAM.
- **Phương án đã chọn:** Phương án 2 (Ephemeral Data Context theo chuẩn GX 1.x).
- **Lý do:** Tối ưu hóa hiệu năng in-memory, loại bỏ hoàn toàn nguy cơ sai lệch đường dẫn tệp cấu hình giữa các hệ điều hành (Windows vs Linux), đảm bảo tính Idempotent khi chạy CI/CD và tuân thủ đúng định hướng kỹ thuật của GX 1.x.
- **Bằng chứng quyết định phù hợp:** Quá trình kiểm định dữ liệu thực thi nhanh chóng, không phát sinh lỗi deprecated warning hay crash context, kết quả validation tuần tự hóa trực tiếp ra file JSON phục vụ báo cáo một cách minh bạch.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  ImportError: cannot import name 'UTC' from 'datetime' (C:\Users\Duong\AppData\Local\Programs\Python\Python310\lib\datetime.py)
  ```
- **Lệnh hoặc bước tái hiện:** Chạy lệnh nạp cấu hình hệ thống: `python -c "from core.config import load_settings; load_settings()"` trên môi trường Python 3.10.
- **Nguyên nhân gốc:** Thuộc tính `datetime.UTC` là alias mới được giới thiệu từ Python 3.11 trở lên. Máy tính sử dụng Python 3.10 nên không thể import trực tiếp `UTC` từ thư viện chuẩn `datetime`.
- **Cách xử lý:** Thay đổi cơ chế import trong `src/core/config.py` và `src/core/utils.py` bằng cấu trúc try/except an toàn:
  ```python
  from datetime import datetime, timedelta, timezone
  try:
      from datetime import UTC
  except ImportError:
      UTC = timezone.utc
  ```
- **Cách xác minh sau khi sửa:** Chạy lại toàn bộ script `run_phase1.py` và `run_corruption_flow.py`, cả hai đều chạy thành công với Exit Code 0 trên Python 3.10 mà không gặp bất kỳ lỗi import nào.
- **Điều học được:** Khi phát triển thư viện dùng chung cho nhóm, luôn phải chú ý đến tính tương thích ngược (backward compatibility) giữa các phiên bản Python (3.10 vs 3.11+).

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu đi từ Crossref đến vector index: Dữ liệu thô ban đầu được tải qua Crossref REST API (hoặc nạp từ snapshot local khi mất mạng) dưới dạng JSON. Dữ liệu đi qua bộ lọc làm sạch loại bỏ mã JATS XML, khử trùng lặp và tính độ tuổi. Sau đó, nội dung được định dạng thành chuỗi văn bản 5 phần và đưa vào mô hình `sentence-transformers/all-MiniLM-L6-v2` để sinh vector 384 chiều, cuối cùng nạp vào collection ChromaDB với cơ chế đánh chỉ mục khoảng cách Cosine HNSW.
2. Đo lường retrieval và answer quality: Tập test set bao gồm 10 câu hỏi định sẵn kèm danh sách ID tài liệu chân lý (`ground_truth_doc_ids`) và câu trả lời chuẩn (`ground_truth`). Khi truy vấn, hệ thống so khớp xem tài liệu mà ChromaDB trả về ở top-k có chứa ID chân lý không để tính Retrieval Hit Rate, đồng thời so sánh chuỗi câu trả lời của mô hình với ground truth để tính chỉ số Mean Token F1 và điểm LLM Judge.
3. Quality checks khác Freshness monitoring: Quality checks kiểm định tính toàn vẹn về mặt cấu trúc và cú pháp (schema integrity, nullability, uniqueness, độ dài ký tự tối thiểu). Trong khi đó, Freshness monitoring đo lường thuộc tính thời gian của tri thức (tính tươi mới), phát hiện xem dữ liệu có bị lỗi thời, quá hạn theo thỏa thuận dịch vụ (SLA 180 ngày) hay không.
4. Dùng cùng một test set cho cả 3 trạng thái: Việc giữ nguyên cố định tập test set (10 câu hỏi chuẩn) là điều kiện tiên quyết để đảm bảo tính khách quan của phép đo khoa học (A/B testing). Khi giữ cố định câu hỏi và ground truth, mọi sự sụt giảm hay phục hồi về điểm số đều phản ánh chính xác chất lượng của nguồn dữ liệu và vector index tại từng thời điểm.
5. Tiêu chuẩn công nhận Repair thành công: Phục hồi được coi là thành công khi thỏa mãn đồng thời hai điều kiện: Chốt kiểm dịch Data Quality Gate chuyển lại trạng thái PASSED (không còn vi phạm unique hay freshness) và các chỉ số hiệu năng RAG (Retrieval Hit Rate và Mean Token F1) phục hồi 100% về ngang bằng với mốc Baseline ban đầu.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 100.0% | 50.0% | 100.0% | Giảm một nửa khi bị xóa 20% bài và cắt tiêu đề; phục hồi hoàn toàn sau repair |
| `mean_token_f1` | 100.0% | 75.1% | 100.0% | Bị suy giảm rõ rệt do nhiễu văn bản và mất tài liệu; lấy lại độ chính xác 100% |
| `judge_accuracy` | 100.0% | 80.0% | 100.0% | Tỷ lệ đánh giá đạt sụt giảm ở các câu hỏi bị mất ngữ cảnh |
| `mean_judge_score` | 5.00 / 5.0 | 3.80 / 5.0 | 5.00 / 5.0 | Điểm trung bình chất lượng câu trả lời bị kéo tụt xuống mức 3.8 |
| Quality checks | PASSED | FAILED | PASSED | GX 1.x phát hiện chính xác lỗi vi phạm trùng ID và tóm tắt rỗng |
| Freshness status | FRESH | STALE VIOLATION | FRESH | Cảnh báo quá hạn kích hoạt chính xác khi lùi ngày xuất bản |

### Kết luận từ số liệu

Hai chuỗi nguyên nhân – bằng chứng:
1. Tiêm 6 dạng lỗi (xóa bài, rỗng tóm tắt, cắt tiêu đề, lùi ngày) → Chốt kiểm định GX 1.x báo FAILED và Freshness báo STALE → Retrieval Hit Rate lập tức sụt giảm nghiêm trọng từ 100% xuống 50%, Token F1 giảm xuống 75.1%.
2. Kích hoạt cơ chế Idempotent Repair từ raw snapshot → Data Quality Gate quay lại trạng thái PASSED và FRESH → Retrieval Hit Rate và Mean Token F1 phục hồi hoàn toàn về mức 100%.

Dạng lỗi ảnh hưởng rõ nhất là việc xóa bỏ 20% tài liệu mới nhất (`drop_latest_records`) kết hợp cắt ngắn tiêu đề (`truncate_title`). Khi tài liệu bị loại bỏ khỏi index, vector store hoàn toàn không có ngữ cảnh để truy xuất, khiến Agent buộc phải trả về câu trả lời mặc định không tìm thấy tài liệu, kéo tụt Hit Rate xuống 50%.

Kết quả thú vị ghi nhận được là ngay cả khi tài liệu bị tiêm nhiễu token rác (`inject_noise`), mô hình embedding MiniLM vẫn có khả năng bắt được một phần ngữ nghĩa lân cận, nhưng chỉ số Token F1 của câu trả lời bị suy giảm do chứa các từ ngữ sai lệch.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Tầm quan trọng của Data Lineage và Raw Snapshot: Luôn luôn lưu trữ nguyên vẹn dữ liệu thô ban đầu ở dạng bất biến (immutable) để làm cơ sở cho các cơ chế tự phục hồi (Self-Healing) khi tầng serving gặp sự cố.
2. Vai trò của Data Observability Gate: Cần có chốt chặn kiểm định tự động (Great Expectations + Freshness SLA) ngay tại cửa ngõ ingestion để ngăn ngừa hiện tượng Silent Failure trước khi dữ liệu độc hại xâm nhập vào Vector Database.
3. Mối liên hệ mật thiết giữa Data Quality và RAG Performance: Chất lượng câu trả lời của mô hình ngôn ngữ phụ thuộc hoàn toàn vào độ sạch và độ chính xác của tài liệu được truy xuất (Garbage In, Garbage Out).

### Nếu có thêm thời gian

Nếu có thêm thời gian thì sẽ phát triển thêm một dashboard trực quan hóa thời gian thực bằng Streamlit hiển thị phân bố độ tuổi bài báo, biểu đồ radar so sánh 3 trạng thái và tính năng tự động kích hoạt pipeline rollback/repair thông qua webhook khi phát hiện Quality Gate bị vi phạm.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Chu Thùy Dương  
**Ngày xác nhận:** 2026-09-26 