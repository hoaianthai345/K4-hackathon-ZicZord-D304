# Reflection — 2A202601866 · Vũ Thanh Khang

## 1. Vai trò & phần mình làm cụ thể

- **Lane:** Backend+Data / Memory+Eval
- **Deliverable có tên mình:**
    - `data_pipeline/process_discord_exports.py` — script thu thập và chuẩn hoá Discord export.
    - `data/vlearn-pack/chatlog/chat_history_anonymized_for_hackathon.csv` — tập dữ liệu sau tiền xử lý.
    - `eval/golden_set.csv` và `eval/run_eval.py` — golden set và script chạy đánh giá.
- **Công việc tự tay làm (không chỉ copy AI):**
    - Viết pipeline chuyển Discord JSON → CSV, loại PII, chuẩn hoá timestamp và user id.
    - Tách thread/conversation, chuẩn hoá message text (strip, normalize whitespace, xử lý embeds).
    - Chuẩn hóa schema đầu ra dùng cho eval và lưu versioned outputs.

## 2. AI hỗ trợ mình thế nào

- **Tool:** ChatGPT (hướng dẫn regex), các script nội bộ.
- **Prompt điển hình:** "Cách anonymize user mentions trong Discord export, regex cho mentions và URLs"
- **AI làm tốt:** gợi ý regex, ví dụ parsing JSON, cấu trúc pipeline.
- **AI sai / cần hiệu chỉnh:** AI đề xuất xóa metadata toàn bộ — tôi giữ lại `timestamp`, `thread_id` vì cần cho context và đánh giá.

## 3. Một bài học từ case fail của nhóm

**Case fail:** Golden set lần đầu bị leak vì anonymize không loại bỏ user id nằm trong URLs/embed.

**Bài học rút ra:** Anonymize phải kiểm tra mọi trường (cross-field), không chỉ các trường hiển nhiên; cần test end-to-end từ raw → processed → eval input.

## 4. Nếu làm lại từ đầu, mình sẽ làm khác

- Viết unit tests cho bước anonymize (covers: mentions, URLs, embeds, attachments).
- Đóng gói preprocessing thành CLI reproducible, kèm versioned outputs và checksum.
- Viết README ngắn trong `data/` mô tả schema CSV và cách reproduce.

## Kết quả hiện có

- File dữ liệu anonymized: `data/vlearn-pack/chatlog/chat_history_anonymized_for_hackathon.csv`
- Golden set và script eval: `eval/golden_set.csv`, `eval/run_eval.py`

## Hành động tiếp theo (gợi ý)

- Thêm test anonymize và chạy CI cho pipeline.
- Tạo `data/README.md` mô tả schema và cách chạy preprocessing.
