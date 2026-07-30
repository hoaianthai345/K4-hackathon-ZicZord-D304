# Dataset processing report — 30/07/2026

Nguồn local gồm ba Discord export Excel trong thư mục `Dataset`. Pipeline chỉ đọc
file nguồn và ghi output mới vào `codebase/data/processed`; checksum SHA-256 trước
và sau lần chạy giống nhau.

## Quy mô

| Chỉ số | Giá trị |
|---|---:|
| Message | 6.373 |
| Export/channel | 3 |
| Reporter key duy nhất | 905 |
| Question/problem episode | 1.701 |
| Pain-point cluster sau hybrid vector clustering | 1.283 |
| Attachment | 193 |
| Acknowledgement signal | 230 |
| Dot noise | 742 |
| Greeting | 137 |

Reporter key là hash ổn định, không phải Discord ID thô. Con số unique reporter có
thể sai lệch do export hiện tại đã lưu Discord ID dạng số Excel và thiếu role/reply
metadata.

## Tín hiệu pain point nổi bật

Kết quả dưới đây là output heuristic để định hướng discovery, chưa phải số liệu đã
được human review:

| Pain point | Episode | Reporter duy nhất | Unresolved/unclear |
|---|---:|---:|---:|
| Xin nghỉ học và cập nhật điểm danh | 63 | 49 | 68,3% |
| Không tìm thấy nội dung hoặc slide bài giảng | 47 | 36 | 91,5% |
| Không nhận được GitHub Organization invite | 12 | 11 | 75,0% |
| Nộp daily ở đâu | 8 | 8 | 100% |
| Cách tăng XP | 8 | 7 | 100% |

Nhiều report từ người khác nhau được giữ thành episode riêng rồi mới cùng trỏ tới
`painpoint_cluster_id`. Same-author near duplicate chỉ được đánh dấu/ghép episode,
không xóa row.

## Ba output

1. `messages_clean.jsonl`: giữ `content_original`, thêm `content_clean`,
   `content_search`, `content_model`, tám cờ noise/intent, attachment và reaction.
2. `issue_episodes.jsonl`: anchor, context theo topic/entity, answer, resolution,
   response time, source rows và confidence.
3. `painpoint_summary.jsonl`: tần suất, reporter, unresolved rate, response time,
   resolution và evidence rows.

Các output chứa nội dung Discord nên bị Git ignore. File này chỉ giữ thống kê
aggregate không định danh.

## Giới hạn cần sửa ở lần crawl sau

Ưu tiên bổ sung `message_id`, `reply_to_message_id`, `channel_id`, `thread_id`,
`author_id` dạng string, `author_roles`, `is_bot`, `edited_at` và attachment metadata.
Reply/thread là tín hiệu quan trọng nhất để giảm context lẫn giữa các topic đồng thời.
