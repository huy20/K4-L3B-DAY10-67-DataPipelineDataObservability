# Báo Cáo Đối Chiếu 3 Trạng Thái: Baseline vs Corrupted vs Repaired

> **Mục tiêu:** Đo lường tác động của suy giảm chất lượng dữ liệu (Data Corruption / Silent Failure) đối với RAG Agent và chứng minh năng lực tự phục hồi toàn vẹn (Idempotent Repair).

---

## 1. Bảng Đối Chiếu Hiệu Năng 3 Trạng Thái

| Trục Đánh Giá / Metric | Baseline (Chuẩn) | Corrupted (Bị Tiêm Lỗi) | Repaired (Sau Phục Hồi) | Xu Hướng Biến Động |
|---|:---:|:---:|:---:|:---:|
| **Quality Gate Status (GX 1.x)** | **PASSED** | **FAILED** | **PASSED** | Phục hồi toàn vẹn |
| **Freshness SLA (`is_fresh`)** | **True** | **False** | **True** | Đạt SLA sau sửa chữa |
| **Retrieval Hit Rate** | **100.0%** | **40.0%** | **100.0%** | Tụt mạnh -> Hồi phục |
| **Mean Token F1** | **100.0%** | **57.6%** | **100.0%** | Suy giảm nghiêm trọng -> Hồi phục |
| **Judge Accuracy** | **100.0%** | **60.0%** | **100.0%** | Tụt dốc -> Hồi phục |
| **Mean Judge Score (1-5)** | **5.00** | **3.20** | **5.00** | Hồi phục về mức nền |

---

## 2. Phân Tích Hiện Tượng Silent Failure
1. **Mất mát tài liệu (Drop latest):** Làm cho vector store thiếu hụt các văn bản mới nhất, dẫn đến câu hỏi về các tài liệu này bị trượt retrieval (`retrieval_hit = False`).
2. **Xóa rỗng tóm tắt (Blank summary) & Nhiễu (Noise):** Làm suy thoái ngữ nghĩa vector embedding, khiến các câu trả lời của Agent bị ảo giác (hallucination) hoặc trả về chuỗi rác, kéo tụt điểm Token F1.
3. **Cắt cụt tiêu đề (Truncate title):** Gây phá vỡ cơ chế tra cứu chính xác (`lookup_paper`), ép Agent phải dùng semantic search với điểm tương đồng thấp.
4. **Lỗi ngày xuất bản (Stale date):** Vi phạm Freshness SLA (> 180 ngày), phát hiện dữ liệu lỗi thời.
5. **Nhân bản bản ghi (Duplicate rows):** Vi phạm tính duy nhất (`ExpectColumnValuesToBeUnique`), gây sai lệch xếp hạng truy vấn.

---

## 3. Cơ Chế Idempotent Repair & Kết Quả
Hệ thống tự động đồng bộ lại từ snapshot raw tin cậy (`data/raw/crossref_records.json`), chạy lại Data Cleaning, xây dựng lại ChromaDB collection `papers-repaired` và tái thẩm định chất lượng.
Toàn bộ chỉ số hiệu năng và Data Quality Gate đã trở về trạng thái tương đương Baseline.
