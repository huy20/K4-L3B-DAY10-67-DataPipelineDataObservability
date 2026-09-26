# Báo Cáo Pha 1: Baseline Data Pipeline & Data Observability

> **Hệ thống:** Agentic RAG Data Pipeline với Data Observability (Great Expectations 1.x)  
> **Bộ dữ liệu chuẩn:** Crossref REST API / Metadata Snapshot  
> **Trạng thái Quality Gate:** PASSED  

---

## 1. Tóm Tắt Nguồn Dữ Liệu (Data Ingestion)
- **Nguồn API:** `Crossref REST API`
- **Query:** `agentic retrieval augmented generation large language model`
- **Filter:** `from-pub-date:2026-03-30,has-abstract:true`
- **Tổng số bản ghi thu thập:** `24`
- **Số bản ghi sau tiền xử lý:** `24`

---

## 2. Tiền Xử Lý & Chuẩn Hóa Schema (Data Cleaning)
- Loại bỏ các thẻ định dạng JATS XML (`<jats:p>`, v.v.) và khoảng trắng thừa.
- Khử trùng lặp theo `paper_id` và loại bỏ bản ghi thiếu trường cốt lõi.
- Tính toán độ tuổi bài báo `age_days = (run_date - published).days`.
- Tạo cấu trúc chuẩn 5 phần `text_for_embedding`:
  - `Title`: Tiêu đề bài báo đã làm sạch.
  - `Authors`: Danh sách tác giả chuẩn hóa nối bằng dấu phẩy.
  - `Published`: Ngày xuất bản chuẩn ISO YYYY-MM-DD.
  - `Categories`: Các danh mục phân loại nghiên cứu.
  - `Summary`: Tóm tắt nội dung học thuật.

---

## 3. Data Observability Gate (Great Expectations 1.x & Freshness SLA)

| Hạng mục kiểm định | Tiêu chí | Kết quả | Trạng thái |
| :--- | :--- | :---: | :---: |
| **Row Count** | `ExpectTableRowCountToBeBetween(1, 1000)` | `24` dòng | PASSED |
| **Null Values** | `ExpectColumnValuesToNotBeNull(paper_id, title)` | 0 nulls | PASSED |
| **Unique IDs** | `ExpectColumnValuesToBeUnique(paper_id)` | 100% unique | PASSED |
| **Summary Length** | `ExpectColumnValueLengthsToBeBetween(10, 5000)` | 193 - 296 ký tự | PASSED |
| **Freshness SLA** | Tỷ lệ `age_days > 180` không quá 25% | `1/24 (4.2%)` | PASSED |

**Kết luận Quality Gate:** Hệ thống xác nhận dữ liệu sạch đạt chuẩn để đưa vào Vector Store Serving Layer.

---

## 4. Vector Database & Indexing
- **Vector Database:** ChromaDB (Local Persistent)
- **Collection Name:** `papers-baseline`
- **Embedding Model:** `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions)
- **Khoảng cách tương đồng:** Cosine Similarity (HNSW Index)
- **Tổng số documents đã index:** `24`

---

## 5. Đánh Giá Hiệu Năng Nền (Baseline Evaluation Benchmarks)

| Chỉ số đánh giá | Giá trị Baseline | Diễn giải kỹ thuật |
| :--- | :---: | :--- |
| **Số câu hỏi benchmark (Samples)** | `10` | Phủ qua 4 nhóm: `summary`, `authors`, `date`, `categories` |
| **Retrieval Hit Rate** | **`100.0%`** | Tỷ lệ context truy xuất chứa đúng tài liệu chân lý |
| **Mean Token F1** | **`100.0%`** | Độ trùng khớp token giữa câu trả lời và ground truth |
| **LLM Judge Accuracy** | **`100.0%`** | Tỷ lệ câu trả lời được LLM Judge chấm đạt |
| **Mean Judge Score (1-5)** | **`5.00 / 5.0`** | Điểm trung bình chất lượng câu trả lời |

---

## 6. Sẵn Sàng Cho Pha Thử Nghiệm Tiêm Lỗi (Next Steps)
Bộ dữ liệu sạch đã được bảo vệ bởi Data Observability Gate và thiết lập các mốc hiệu năng nền vững chắc. Hệ thống sẵn sàng cho thử thách tại Checkpoint 4 (Synthetic Data Corruption Suite).
