# Mining report — Learning Memory

> Trạng thái: Evidence B draft
> Nguồn: `data/vlearn-pack/chatlog/chat_history_anonymized_for_hackathon.csv`
> Phạm vi thời gian trong pack: 22–29/07/2026
> Script kiểm lại: `python3 evidence/analyze_chatlog.py`

## 1. Câu hỏi mining

1. Học viên có lịch sử nhiều lượt/nhiều conversation đủ để một memory layer tạo giá trị không?
2. Job “tóm tắt/ôn lại/biết phần cần nhớ” có xuất hiện trực tiếp không?
3. Tutor hiện tại có lưu signal về learning state và chủ động kiểm tra hiểu không?
4. Recap hiện tại có grounding/citation ở mức nào?

## 2. Phương pháp

1. Đọc dictionary và 30–50 cặp hỏi–đáp trước khi định nghĩa rule.
2. Một turn là một `turn_id`, gồm đúng một student message và một tutor message.
3. “Returning user” là `user_id` có từ hai `turn_id` khác nhau.
4. “Multi-conversation user” là `user_id` có từ hai `conversation_id` khác nhau.
5. “Recap request” là student message khớp regex không phân biệt hoa/thường:

```text
\b(tóm tắt|tóm gọn|ôn lại|ôn tập|nội dung chính|
quan trọng nhất|cần nhớ|keyword cần nhớ)\b
```

6. Recap “không citation” khi tutor message cùng turn có `citations` bằng rỗng hoặc `[]`.
7. “Explicit self-check” dùng rule hẹp:

```text
\b(quiz|tự kiểm tra|đánh giá.{0,50}(học xong|hiểu|nắm))\b
```

8. Check hiểu, misconception và follow-up dùng trực tiếp ba field:
   `asked_check_question`, `misconceptions`, `follow_ups`.
9. Không dùng `total_cost_usd` vì data dictionary xác nhận tracking đang broken.

Giới hạn: keyword rule có thể bỏ sót cách diễn đạt khác; các số là lower-bound cho recap. Mining chứng minh hành vi/pain tồn tại, không tự chứng minh số phút tiết kiệm hoặc mức sẵn sàng dùng.

## 3. Kết quả

| Metric | Kết quả |
|---|---:|
| Tổng số dòng | 2.522 |
| Cặp hỏi–đáp | 1.261 |
| Học viên ẩn danh | 369 |
| Conversation | 585 |
| User có ≥2 turn | 230/369 (62,3%) |
| User có ≥2 conversation | 130/369 (35,2%) |
| Conversation có ≥2 turn | 276/585 (47,2%) |
| Số turn/user | median 2; mean 3,42; max 60 |
| Recap request | 129 turn từ 94 user (25,5% user) |
| Recap không citation | 84/129 (65,1%) |
| Explicit self-check request theo rule hẹp | 4 turn từ 3 user |
| Tutor hỏi kiểm tra hiểu | 3/1.261 (0,24%) |
| `misconceptions` khác rỗng | 0/1.261 |
| `follow_ups` khác rỗng | 0/1.261 |

## 4. Ví dụ nguyên văn ngắn

Chỉ giữ trích dẫn tối thiểu cần cho hackathon, kèm mã turn thay vì copy data dài.

| Turn | Quote học viên | Signal |
|---|---|---|
| `T0303` | “bạn có nhớ câu hỏi mà tôi trả lời không” | Nhu cầu continuity/memory trực tiếp |
| `T0113` | “Làm sao để tôi có thể đánh giá là mình đã học xong bài này?” | Muốn biết learning state |
| `T0849` | “TẠO QUIZ ĐỂ TÔI HIỂU RÕ VÀ ÔN LẠI…” | Muốn self-check/ôn tập |
| `T0985` | “tóm tắt lại hôm nay đã học những gì…” | Muốn recap sau buổi |
| `T0913` | “Tôi là sinh viên năm nhất… chưa có nền tảng về AI.” | User phải tự lặp context trình độ |
| `T0597` | “trả lời cho một sinh viên SE chưa hiểu gì về AI” | User phải tự khai lại level |
| `T0173` | “Gạch các tiêu đề ra… để tôi xem mình nên học những cái gì” | Muốn biết phạm vi cần ôn |
| `T0530` | “cho tôi cách ghi nhớ nhanh bài này” | Muốn chuyển nội dung thành memory học tập |

Đáng chú ý ở `T0303`, tutor trả lời rằng không có dữ liệu về câu hỏi trước đó trong lượt hội thoại. Đây là ví dụ trực tiếp về context bị đứt, không phải suy đoán từ metadata.

## 5. Kết luận có thể dùng

- Pack có đủ longitudinal signal ở mức prototype: 62,3% user có từ hai turn và 35,2% đi qua nhiều conversation.
- Nhu cầu recap xuất hiện ở ít nhất 25,5% user theo rule hẹp.
- Tutor hiện gần như không tạo learning-state signal có cấu trúc: 0 misconception, 0 follow-up và chỉ 0,24% lượt có check question.
- Vì 65,1% recap request không có citation, một recap cá nhân hóa phải giữ provenance thay vì chỉ sinh thêm text.

## 6. Điều chưa được phép kết luận

- Không được gọi mọi câu hỏi là một “lỗ hổng kiến thức”.
- Không được nói user “đã hiểu” chỉ vì không hỏi lại.
- Không được nói tính năng tiết kiệm X phút nếu chưa khảo sát.
- Không được nói 94 user chắc chắn muốn Learning Memory; họ chỉ thể hiện job recap.
- Không được dùng code/quote để suy ngược danh tính người học.

## 7. Bước xác minh tiếp

Khảo sát ≥20 người về lần ôn gần nhất:

1. Sau buổi học gần nhất, bạn làm gì để biết phần nào mình còn chưa chắc?
2. Bạn phải mở lại những nguồn nào và mất khoảng bao lâu?
3. Lần gần nhất tutor trả lời, nó có dùng những gì bạn đã hỏi trước đó không?
4. Nếu hệ thống đề xuất “phần có thể cần ôn”, điều gì khiến bạn tin hoặc không tin?
5. Bạn có đồng ý thử prototype 10 phút trước demo không?

Ghi toàn bộ từng câu trả lời và tên/vai; không chỉ ghi số tổng hợp.
