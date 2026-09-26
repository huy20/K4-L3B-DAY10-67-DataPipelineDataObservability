# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên nhóm:** `67`
- **Mã Nhóm / Lớp:** `K4`
- **Tên Repository Nộp Bài:** `https://github.com/huy20/K4-L3B-DAY10-67-DataPipelineDataObservability`

> **Mô hình làm việc:** Cả 5 thành viên **độc lập triển khai trọn vẹn pipeline** (Ingestion → Cleaning → Index → Evaluation → Observability → Corruption/Repair). Sau đó Trưởng nhóm đánh giá, chọn bản tốt nhất và hợp nhất vào nhánh `main`.

---

## # Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Phùng Quang Minh Huy | 2A202602610 | [email] | Trưởng nhóm — Full-pipeline + Đánh giá & Hợp nhất bản tốt nhất vào `main` | `report/individual_report.md` |
| 2 | Lưu Nguyên Khôi | 2A202602547 | [email] | Full-pipeline (Ingestion → Cleaning → Index → Evaluation → Observability → Corruption/Repair) | `report/2A202602547_LuuNguyenKhoi.md` |
| 3 | Chu Thùy Dương | 2A202602660 | [email] | Full-pipeline (Ingestion → Cleaning → Index → Evaluation → Observability → Corruption/Repair) | `report/2A202602660_ChuThuyDuong.md` |
| 4 | Nguyễn Minh Hiếu | 2A202602669 | [email] | Full-pipeline (Ingestion → Cleaning → Index → Evaluation → Observability → Corruption/Repair) | `report/2A202602669_NguyenMinhHieu.md` |
| 5 | Phan Đại Cương | 2A202602510 | [email] | Full-pipeline (Ingestion → Cleaning → Index → Evaluation → Observability → Corruption/Repair) | `report/2A202602510_PhanDaiCuong.md` |

---

## # Phạm vi công việc chung (mỗi thành viên thực hiện đầy đủ)

| Khối | Module | Artifact bàn giao |
|---|---|---|
| Ingestion & Data Lineage | `src/ingestion/crossref.py` | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` (24 bài) |
| Cleaning & Corruption | `src/ingestion/cleaning.py`, `src/ingestion/corruption.py` | `data/clean/papers_clean*.{csv,json}`, `data/results/corruption_log.json` |
| RAG & Vector Index | `src/retrieval/` (`index.py`, `embeddings.py`, `qa.py`) | `data/chroma/`, `data/embeddings/`, collections `papers-baseline` / `papers-corrupted` / `papers-repaired` |
| Observability | `src/observability/quality.py`, `src/observability/reporting.py` | `data/quality/*`, `data/quality/gx/*` |
| Evaluation | `src/evaluation/testset.py`, `src/evaluation/metrics.py` | `data/eval/test_set.json`, `data/results/*_metrics.json` |
| Pipeline / Orchestration | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `src/core/` | `data/reports/phase1_report.md`, `data/reports/corruption_report.md`, `data/results/repair_log.json` |

**Bản hợp nhất trên `main`** là phiên bản do Trưởng nhóm Phùng Quang Minh Huy đánh giá là đầy đủ và ổn định nhất; mọi thành viên đều có commit trên nhánh `main`.

---

## # Cá nhân

### ## Phùng Quang Minh Huy — 2A202602610
- **Vai trò:** Trưởng nhóm — Full-pipeline + Đánh giá & Hợp nhất.
- **Công việc chi tiết đã hoàn thành:** Triển khai trọn vẹn pipeline; điều phối & hợp nhất bản tốt nhất vào `main`; kiểm tra tính nhất quán artifact 3 trạng thái và idempotency.
- **Đóng góp chính:** Quyết định kiến trúc orchestrator tự chứa (`run_corruption_flow.py`) và cơ chế Idempotent Repair tái dựng từ raw.

### ## Lưu Nguyên Khôi — 2A202602547
- **Vai trò:** Full-pipeline implementer.
- **Công việc chi tiết đã hoàn thành:** Xây dựng đầy đủ ingest → clean → index → eval → observability → corruption/repair; chú trọng chuẩn hóa `text_for_embedding` 5 phần và xử lý ngày thiếu.
- **Đóng góp chính:** Quy tắc làm sạch dữ liệu và xử lý `published` thiếu theo hướng "unknown, không tính stale".

### ## Chu Thùy Dương — 2A202602660
- **Vai trò:** Full-pipeline implementer.
- **Công việc chi tiết đã hoàn thành:** Xây dựng đầy đủ pipeline; chú trọng Quality Gate Great Expectations 1.x và Freshness SLA.
- **Đóng góp chính:** Chuyển đổi sang cú pháp GX 1.x (ephemeral context + ExpectationSuite) thay cho cú pháp cũ.

### ## Nguyễn Minh Hiếu — 2A202602669
- **Vai trò:** Full-pipeline implementer.
- **Công việc chi tiết đã hoàn thành:** Xây dựng đầy đủ pipeline; chú trọng bộ test set 4 nhóm và đo lường retrieval/answer quality.
- **Đóng góp chính:** Thiết kế câu hỏi neo theo exact title và fallback category `Uncategorized`.

### ## Phan Đại Cương — 2A202602510
- **Vai trò:** Full-pipeline implementer.
- **Công việc chi tiết đã hoàn thành:** Xây dựng đầy đủ pipeline; chú trọng vector index ChromaDB và embedding MiniLM.
- **Đóng góp chính:** Cấu hình 3 collection cosine độc lập và `record_id` duy nhất cho mỗi tài liệu.
