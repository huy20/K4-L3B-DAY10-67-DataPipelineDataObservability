# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Phan Đại Cương |
| MSSV               | 2A202602510 |
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
| RAG & Vector Index | `src/retrieval/index.py`, `src/retrieval/embeddings.py`, `src/retrieval/qa.py` | Clean dataframe, `Settings` | `data/chroma/`, `data/embeddings/papers_embeddings*.json`, 3 collection | Hoàn thành |
| Data Observability | `src/observability/quality.py` | Clean dataframe, `Settings` | `data/quality/*` | Hoàn thành |
| Benchmark Evaluation | `src/evaluation/testset.py` | Clean dataframe | `data/eval/test_set.json` | Hoàn thành |
| Baseline pipeline | `src/pipelines/phase1.py` | Raw records, `Settings` | `data/results/baseline_metrics.json` | Hoàn thành |
| Corruption suite | `src/ingestion/corruption.py` | Clean dataframe | `data/results/corruption_log.json` | Hoàn thành |
| Idempotent Repair & comparison | `src/pipelines/corruption_flow.py` | Raw records, baseline artifacts | `data/results/repaired_metrics.json`, `data/reports/corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Cấu hình collection name theo state | `retrieval/index.py` | 3 collection tách biệt cho so sánh công bằng |
| Xử lý tài liệu trùng id | `corruption.py`, `index.py` | `record_id` duy nhất, không lỗi Chroma |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Nạp vector baseline | `LocalEmbeddingIndex.build` | Collection `papers-baseline` 24 docs | `data/embeddings/papers_embeddings.json` |
| Nạp vector corrupted/repaired | `build` với `embeddings_output_path` | `papers-corrupted` (22), `papers-repaired` (24) | `data/chroma/` |
| Truy vấn ngữ cảnh | `index.search`, `qa.answer_question` | Baseline hit 1.0 | `data/results/baseline_metrics.json` |
| End-to-end + repair | `src/pipelines/*` | 3 trạng thái, repaired về baseline | 2 script entrypoint |

Output cụ thể: 3 manifest `data/embeddings/papers_embeddings{,_corrupted,_repaired}.json` ghi rõ `collection_name`, `persist_path`, `embedding_model` và danh sách documents để tái nạp index.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Index toàn bộ tài liệu sạch vào ChromaDB bằng `all-MiniLM-L6-v2`, tách biệt 3 trạng thái để so sánh, và đảm bảo truy vấn trả về đúng ngữ cảnh kể cả khi có tài liệu trùng.

### Cách triển khai

- **Embedding:** `SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")`, chuẩn hóa vector (`normalize_embeddings=True`) → cosine tương đương dot-product.
- **Collection:** Chroma `PersistentClient` tại `data/chroma`, mỗi trạng thái một collection (`papers-baseline/corrupted/repaired`), cấu hình `hnsw.space = cosine`; build thì xóa collection cũ trước để tránh dữ liệu thừa.
- **Document/ID:** `record_id = "{paper_id}::{index}"` đảm bảo duy nhất kể cả khi corruption nhân bản dòng; metadata lưu `paper_id, title, published, authors_joined, categories_joined, summary, abs_url, pdf_url`.
- **Search:** trả `score = 1 − distance`, kèm dedupe khi agent khớp exact title.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Clean dataframe (`text_for_embedding` + metadata), `Settings.embedding_model`, `top_k=4` |
| Output                         | Chroma collection + manifest JSON cho từng trạng thái |
| Module phụ thuộc             | `core/config.py`, `core/utils.py`, `sentence-transformers`, `chromadb` |
| Module sử dụng output        | `evaluation/metrics.py`, `pipelines/*`, `retrieval/qa.py` |
| Điều kiện lỗi cần xử lý | Tài liệu trùng id, collection cũ tồn tại, model phải tải/cache |

### Cách xác minh

```bash
python script/run_phase1.py
python -c "from core.config import load_settings; from retrieval.index import LocalEmbeddingIndex; s=load_settings(); idx=LocalEmbeddingIndex.load(s); print(idx.collection_name, idx.collection.count())"
```

- **Kết quả mong đợi:** `papers-baseline 24`.
- **Kết quả thực tế:** đúng; corrupted 22, repaired 24.
- **Artifact/log:** `data/chroma/`, `data/embeddings/`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** có nhiều cách lưu index cho 3 trạng thái và cách đặt ID tài liệu.
- **Các phương án đã cân nhắc:** (A) dùng một collection rồi xóa/nạp lại mỗi lần; (B) dùng 3 collection độc lập, ID ghép `paper_id::index`.
- **Phương án đã chọn:** (B).
- **Lý do:** giữ nguyên trạng thái baseline để đối chiếu (A làm mất baseline khi eval corrupted), và ID ghép tránh lỗi khi corruption nhân bản `paper_id`.
- **Bằng chứng:** 3 manifest tồn tại đồng thời; corrupted eval chạy thành công với 22 docs có dòng trùng id.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `chromadb.errors.IDAlreadyExistsError` khi nạp dữ liệu corrupted có `duplicate_rows`.
- **Nguyên nhân gốc:** kịch bản duplicate nhân bản dòng nên `paper_id` bị lặp; nếu dùng `paper_id` làm ID vector thì Chroma từ chối.
- **Cách xử lý:** dùng `record_id = f"{paper_id}::{index}"` (index theo thứ tự enumerate) làm ID, vẫn đảm bảo duy nhất và giữ `paper_id` trong metadata để tra cứu.
- **Cách xác minh sau khi sửa:** `papers-corrupted` nạp đủ 22 docs, `evaluate_pipeline` chạy không lỗi.
- **Điều học được:** ID trong vector store phải là duy nhất ở tầng kỹ thuật, tách khỏi định danh nghiệp vụ.

## 7. Hiểu biết về luồng end-to-end

1. **Crossref → vector index:** API/snapshot → parse → clean → MiniLM + Chroma `papers-baseline`.
2. **Evaluation set:** 10 câu/4 nhóm; hit nếu id truy hồi nằm trong `ground_truth_doc_ids`; token-F1 so `ground_truth`.
3. **Quality vs freshness:** quality kiểm tra cấu trúc/đầy đủ/hợp lệ; freshness kiểm tra chiều thời gian.
4. **Cùng test set:** cô lập biến duy nhất là chất lượng dữ liệu.
5. **Repair thành công:** fingerprint trùng baseline + GX/freshness pass + metrics về baseline.

## 8. Phân tích kết quả

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét |
| ---------------------- | -------: | --------: | -------: | -------- |
| `retrieval_hit_rate` |     1.0 |      0.5 |     1.0 | 5 gold doc bị xoá khỏi index |
| `mean_token_f1`      |     1.0 |   0.4456 |     1.0 | Summary hỏng |
| `judge_accuracy`     |     1.0 |      0.4 |     1.0 | Cùng xu hướng |
| `mean_judge_score`   |       5 |      2.6 |       5 | Giảm hơn 2 bậc |
| Quality checks         |    True |     False |     True | Fail unique + length |
| Freshness status       |    True |     False |     True | 6/22 stale (27.3%) |

1. **Corruption → tín hiệu → metric:** index mất 5 tài liệu (drop latest) và nội dung bị hỏng (blank/noise) → hit 1.0→0.5, F1 1.0→0.4456.
2. **Repair → phục hồi → metric:** build lại `papers-repaired` từ dữ liệu tái dựng raw → metric về baseline.

Corruption ảnh hưởng rõ nhất tới retrieval: **drop_latest_records** vì làm biến mất vector của đúng các gold document; **duplicate_rows** không phá retrieval (nhờ `record_id`) nhưng bị Quality Gate bắt.

## 9. Điều học được và hướng cải thiện

1. **Pipeline:** tách collection theo trạng thái giúp so sánh mà không mất dữ liệu baseline.
2. **Observability:** vector store cần ID duy nhất tách khỏi ID nghiệp vụ.
3. **RAG:** thiếu tài liệu trong index là nguyên nhân trực tiếp làm retrieval sụt.

**Nếu có thêm thời gian:** thêm metadata filter (theo `published`) khi truy vấn và đo recall@k ngoài top-4.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phan Đại Cương
**Ngày xác nhận:** 2026-09-26
