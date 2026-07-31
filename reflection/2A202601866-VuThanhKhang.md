# Reflection — 2A202601866 · Vũ Thanh Khang

## 1. Vai trò & phần mình làm cụ thể

- **Lane:** Backend+Data / Memory+Eval — vai trò chính của tôi là `Scraw dữ liệu Discord + eval`.
- **Deliverable có tên mình:**
    - `data_pipeline/process_discord_exports.py` — pipeline làm sạch và chuẩn hoá Discord export.
    - `data/vlearn-pack/chatlog/chat_history_anonymized_for_hackathon.csv` — dataset Discord chat đã anonymize.
    - `eval/golden_set.csv` — golden set dùng để đánh giá chất lượng đề xuất task/decision.
    - `eval/run_eval.py` — script chạy đánh giá trên golden set.
- **Công việc tự tay làm (không chỉ copy AI):**
    - Thu thập và phân tích raw export Discord, xác định format message, thread, mention, embed, và attachment.
    - Xây dựng quy trình tiền xử lý: đọc raw data, chuẩn hoá timestamp, chuẩn hoá user references, tạo output phẳng phù hợp cho eval.
    - Thiết kế và thực hiện bước anonymize PII: thay thế mentions Discord, user IDs, tên người dùng, email, URL chứa thông tin người dùng.
    - Tách thread/conversation thành các bản ghi phù hợp để golden set có thể đánh giá đúng ngữ cảnh hội thoại.
    - Chọn mẫu và gán label cho golden set, đảm bảo representation của task/decision/deadline/noise.
    - Kiểm tra chất lượng kết quả bằng sanity-check schema, row count, và verify không còn ID/người dùng thật.
- **Chỗ mình chắc chắn giải thích được:**
    - Vì sao vai trò này là `Scraw dữ liệu Discord + eval`, tức cả collect data và chuẩn bị dữ liệu cho đánh giá.
    - Vì sao cần giữ `thread_id`, `timestamp`, `author_role` và `message_text` để bảo toàn context khi đánh giá đề xuất task/decision.
    - Vì sao golden set phải được rút ra riêng và annotate, không thể dùng raw Discord export thô.

## 2. AI hỗ trợ mình thế nào

- **Tool:** ChatGPT và các script tự viết.
- **Prompt điển hình:**
    - "Làm sao anonymize Discord mention `<@1234>` và tất cả user ID trong messages?"
    - "Cách tách thread conversation từ Discord export JSON/CSV để tạo dataset cho eval?"
- **AI làm tốt:**
    - Đề xuất cấu trúc pipeline: load data, normalize timestamp, anonymize, output CSV.
    - Gợi ý regex nhanh cho mentions Discord và URL chứa ID.
    - Hướng cách phân tích trường data phức tạp như embed, attachment metadata.
- **AI sinh sai, mình sửa:**
    - AI đề xuất xóa toàn bộ metadata để đơn giản hoá, nhưng tôi giữ lại những trường cần thiết cho context và đánh giá.
    - AI gợi ý filter author dựa trên label không rõ; tôi phân tích raw export để dùng `user_id` và role chính xác.
    - AI bỏ qua một số edge-case Discord format, tôi bổ sung test và điều chỉnh logic để xử lý đúng.
- **Phần mình làm thêm:**
    - Test regex anonymize với dữ liệu thật để tránh leak hoặc làm mất context.
    - Bổ sung step sanity-check: verify schema, verify no raw IDs, verify số lượng dòng hợp lý.
    - Định nghĩa rõ ràng schema output cho eval và ghi chú các field giữ lại/loại bỏ.

## 3. Một bài học từ case fail của nhóm

**Case fail cụ thể:**

- Lần đầu nhóm xử lý dữ liệu, chúng tôi chỉ anonymize các trường text hiển nhiên.
- Kết quả là vẫn còn user ID ẩn trong URL/embed Discord và trong mention system dạng `<@1234>`.
- Một số record bị anonymize quá mức, khiến context hội thoại mất, làm gold set kém thực tế.

**Bài học:**

- Anonymize phải đi sâu cross-field, kiểm tra tất cả trường và metadata, không chỉ `message_text`.
- Dữ liệu phải được đánh giá end-to-end: raw export → preprocessing → golden set → eval.
- Phân biệt rõ phần dữ liệu `cần giữ cho task` (context, thread, timestamp, role) và phần `cần loại bỏ` (PII, raw IDs, tên riêng).
- Golden set cần được xây dựng song song với pipeline, không để bước này trở thành gấp rút cuối cùng.

## 4. Nếu làm lại từ đầu, mình sẽ làm khác

- Viết test suite cho bước preprocessing ngay từ đầu, bao gồm anonymize mentions, URLs, embeds, attachments và sanity-check schema.
- Xây dựng pipeline dạng CLI có input/output rõ ràng để dễ reproduce trên export Discord mới.
- Soạn `data/README.md` mô tả schema data, quy ước anonymize và cách chạy pipeline.
- Lưu metadata hoặc checksum cho từng phiên bản output để dễ track thay đổi.
- Hợp tác sớm hơn với team eval để xác định golden set và criteria đánh giá ngay từ giai đoạn đầu.

## 5. Kết quả tôi đã đóng góp

- `data_pipeline/process_discord_exports.py`: pipeline rõ ràng cho Discord raw → processed dataset.
- `data/vlearn-pack/chatlog/chat_history_anonymized_for_hackathon.csv`: file chatlog đã được anonymize và chuẩn hóa.
- `eval/golden_set.csv`: golden set sample có label để đánh giá chất lượng đề xuất task/decision.
- `eval/run_eval.py`: script chạy đánh giá.
- Một hướng tiếp cận data và eval rõ ràng, phù hợp với vai trò `Scraw dữ liệu Discord + eval`.

## 6. Hành động tiếp theo (gợi ý)

- Viết `data/README.md` mô tả schema CSV, trường giữ lại và trường anonymized.
- Thêm unit test và sanity-check cho step anonymize.
- Thiết lập checklist pre-release data: verify PII, verify schema, verify no raw IDs, verify row count.
- Nếu có thời gian, bổ sung script so sánh diff giữa các phiên bản data để phát hiện thay đổi bất ngờ.
