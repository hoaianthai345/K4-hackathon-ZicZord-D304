# Discord dataset pipeline

Pipeline này **không sửa hoặc xóa file Excel gốc**. Mỗi lần chạy sẽ đọc các
workbook ở thư mục input và tạo ba dataset JSONL mới trong thư mục output:

- `messages_clean.jsonl`: toàn bộ message, text gốc, text chuẩn hóa, text đã
  redact cho model, cờ noise và metadata attachment/reaction.
- `issue_episodes.jsonl`: một record cho mỗi cuộc trao đổi quanh question/problem
  anchor.
- `painpoint_summary.jsonl`: các episode được gom bằng vector similarity từ
  `canonical_problem + product_area + entities`.

`summary.json` lưu thống kê kiểm tra nhanh. Output bị Git ignore vì vẫn chứa nội
dung Discord gốc; chỉ report aggregate không định danh mới nên được commit.

## Chạy

```bash
cd codebase
python3 -m pip install -r data_pipeline/requirements.txt
python3 -m data_pipeline.process_discord_exports \
  --input "/absolute/path/to/Dataset" \
  --output data/processed
```

Thêm `--llm-labels` để dùng OpenRouter đặt tên pain-point cluster. Chỉ
`content_model` đã redact email/số điện thoại được gửi ra ngoài. Nếu không bật,
pipeline dùng nhãn deterministic để vẫn chạy offline.

## Nguyên tắc

- `content_original` và URL gốc luôn được giữ trong output local.
- `content_clean` dùng Unicode NFC, trim và collapse whitespace.
- `content_search` là bản casefold chỉ dùng deduplicate/search.
- `content_model` redact email và số điện thoại, là field duy nhất dành cho
  embedding/LLM.
- Dot/greeting chỉ bị loại khỏi context cuối; acknowledgement vẫn được giữ làm
  tín hiệu resolution.
- Same-author duplicate gần nhau được đánh dấu/ghép episode, không xóa row.
- Report từ tác giả khác vẫn là episode riêng và có thể cùng
  `painpoint_cluster_id`.

Giới hạn của export hiện tại: Discord ID đã bị Excel lưu dạng số nên có thể mất
precision, đồng thời thiếu `message_id`, reply/thread và role. Lần crawl kế tiếp
cần lưu các ID dưới dạng string.
