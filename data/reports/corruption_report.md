# Báo Cáo Đối Chiếu 3 Trạng Thái: Baseline vs Corrupted vs Repaired

> **Hệ thống:** Data Pipeline Resilience & Idempotent Self-Healing Analysis  
> **Mục tiêu:** Định lượng sự suy giảm hiệu năng do Silent Failure và chứng minh khả năng tự phục hồi 100% về trạng thái chuẩn.  

---

## 1. Bảng Đối Chiếu Hiệu Năng Tổng Hợp (3 Trạng Thái)

| Chỉ số cốt lõi | 1. Baseline (Sạch) | 2. Corrupted (Tiêm lỗi) | 3. Repaired (Phục hồi) | Mức độ phục hồi |
| :--- | :---: | :---: | :---: | :---: |
| **Data Quality Gate** | **PASSED** | **`BLOCKED`** | **`PASSED`** | Khôi phục chốt chặn |
| **GX 1.x Expectations** | **PASSED** | **`FAILED`** | **`PASSED`** | 100% hợp lệ schema |
| **Freshness SLA** | **FRESH** | **`STALE VIOLATION`** | **`FRESH`** | Không còn vi phạm SLA |
| **Retrieval Hit Rate** | **`100.0%`** | **`50.0%`** | **`100.0%`** | `+50.0%` |
| **Mean Token F1** | **`100.0%`** | **`75.1%`** | **`100.0%`** | `+24.9%` |
| **LLM Judge Accuracy** | **`100.0%`** | **`80.0%`** | **`100.0%`** | `+20.0%` |
| **Mean Judge Score** | **`5.00 / 5.0`** | **`3.80 / 5.0`** | **`5.00 / 5.0`** | `+1.20` |

---

## 2. Phân Tích Hiện Tượng Suy Giảm (Data Corruption Impact & Silent Failure)
Khi không có Data Observability Gate, dữ liệu bẩn sẽ xâm nhập thẳng vào Vector Index:
1. **Drop latest records (mất 20% bản ghi mới):** Làm cho RAG Agent mất context hoàn toàn về các bài báo gần đây nhất -> Hit Rate giảm mạnh.
2. **Blank summary (xóa rỗng tóm tắt):** Embedding của document bị rỗng nghĩa -> Vector khoảng cách sai lệch nghiêm trọng.
3. **Inject noise (chèn ký tự rác):** Gây nhiễu embedding space, làm giảm độ chính xác ngữ nghĩa.
4. **Truncate title (tiêu đề bị cắt < 8 ký tự):** Phá vỡ cơ chế tìm kiếm exact lookup và so khớp từ khóa.
5. **Stale date (lùi ngày xuất bản về quá khứ):** Vi phạm Freshness SLA (tỷ lệ bài quá hạn > 25%), kích hoạt còi báo động.
6. **Duplicate rows (nhân bản dữ liệu):** Làm loãng top-k retrieval results với các bản ghi trùng lặp vô nghĩa.

**Hiện tượng Silent Failure:** Hệ thống RAG vẫn trả lời trôi chảy nhưng nội dung sai lệch hoặc rơi vào trạng thái "I don't know from the indexed corpus" mà không phát sinh bất kỳ runtime exception nào.

---

## 3. Cơ Chế Tự Phục Hồi An Toàn (Idempotent Repair)
- Khôi phục trực tiếp từ nguồn Raw Snapshot bất biến (`data/raw/crossref_records.json` / `crossref_response.json`).
- Tái thực thi pipeline tiền xử lý `build_clean_dataframe` với khử trùng lặp và tính toán lại `age_days`.
- Tái tạo ChromaDB collection `papers-repaired` đảm bảo tính **Idempotent** (chạy lại n lần cho cùng kết quả nhất quán).
- Sau khi phục hồi, toàn bộ chỉ số Retrieval Hit Rate và Token F1 quay trở lại đúng mức Baseline ban đầu.
