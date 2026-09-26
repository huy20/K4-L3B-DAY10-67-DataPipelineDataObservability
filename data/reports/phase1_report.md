# Báo Cáo Pha 1: Baseline Data Pipeline & Observability

> **Ngày sinh báo cáo:** 2026-09-26 03:41:18 UTC  
> **Nguồn dữ liệu:** Crossref REST API  
> **Mô hình Embedding:** sentence-transformers/all-MiniLM-L6-v2  
> **LLM Provider:** gemini (gemini-3.6-flash)

---

## 1. Tổng Quan Thu Thập & Làm Sạch Dữ Liệu
- **Số bản ghi thô (Raw Records):** 24
- **Số bản ghi sạch (Clean Records):** 24
- **Phạm vi ngày xuất bản:** 2026-03-28 đến 2026-07-22
- **Artifacts:**
  - Raw response: `D:\VINAI\K4-L3B-Day10-Data-Pipeline-Data-Observability\data\raw\crossref_response.json`
  - Raw records: `D:\VINAI\K4-L3B-Day10-Data-Pipeline-Data-Observability\data\raw\crossref_records.json`
  - Clean CSV: `D:\VINAI\K4-L3B-Day10-Data-Pipeline-Data-Observability\data\clean\papers_clean.csv`
  - Clean JSON: `D:\VINAI\K4-L3B-Day10-Data-Pipeline-Data-Observability\data\clean\papers_clean.json`

---

## 2. Kiểm Định Chất Lượng Dữ Liệu (Data Observability - GX 1.x)
- **Trạng thái Quality Gate:** `PASSED`
- **Số Expectations kiểm định:** 7 (Đạt: 7/7)
- **Expectations thiết yếu:**
  - `ExpectTableRowCountToBeBetween`: Đạt yêu cầu số lượng bản ghi [20, 30]
  - `ExpectColumnValuesToNotBeNull`: Đầy đủ `paper_id`, `title`, `summary`
  - `ExpectColumnValuesToBeUnique`: Đảm bảo `paper_id` duy nhất 100%
  - `ExpectColumnValueLengthsToBeBetween`: Đạt chuẩn độ dài `title` (>=8) và `summary` (>=20)

---

## 3. Báo Cáo Độ Tươi (Freshness SLA)
- **Trạng thái Freshness:** `FRESH` (is_fresh = True)
- **Ngưỡng SLA:** 180 ngày
- **Số bản ghi quá hạn (> 180 ngày):** 1 / 24
- **Tỷ lệ vi phạm:** 4.17% (Giới hạn cho phép: <= 25.0%)
- **Bản ghi mới nhất:** 2026-07-22 | **Bản ghi cũ nhất:** 2026-03-28

---

## 4. Kết Quả Đánh Giá Baseline RAG Pipeline
Đánh giá trên bộ benchmark 10 câu hỏi đa dạng (Summary, Authors, Date, Categories):

| Chỉ số đánh giá | Giá trị Baseline | Tiêu chuẩn đạt |
|---|:---:|:---:|
| **Retrieval Hit Rate** | **100.0%** | >= 80.0% |
| **Mean Token F1** | **100.0%** | >= 60.0% |
| **Judge Accuracy** | **100.0%** | >= 70.0% |
| **Mean Judge Score** | **5.00 / 5.0** | >= 3.5 |

---

## 5. Kết Luận Pha 1
Pipeline dữ liệu sạch hoạt động ổn định, vượt qua toàn bộ các cổng kiểm định chất lượng Great Expectations 1.x và đạt chuẩn Freshness SLA. Hệ thống sẵn sàng bước vào Pha 2 (Stress-testing & Corruption).
