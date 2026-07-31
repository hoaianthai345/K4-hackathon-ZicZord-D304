# Survey log — Chuẩn A

**Ngày thu:** 31/07/2026 · **n = 24 người ngoài nhóm**

**Dữ liệu kiểm chứng:** [survey-responses-anonymized.csv](survey-responses-anonymized.csv)

**Bổ sung định tính:** 5 transcript phỏng vấn tại [interview-transcripts.md](interview-transcripts.md)

Repo public chỉ lưu ID `F01–F24`; tên, mã học viên và timestamp trong bản xuất
Google Form gốc được giữ ngoài repo để không công khai PII.

## Câu hỏi đã dùng

1. Bạn thường trao đổi công việc nhóm trên nền tảng nào?
2. Team bạn đang quản lý công việc bằng công cụ nào?
3. Bạn mất khoảng bao nhiêu thời gian mỗi tuần để tổng hợp hoặc tìm lại thông tin trong các cuộc trò chuyện?
4. Theo bạn, khó khăn lớn nhất khi làm việc nhóm qua chat là gì?
5. Nếu có một AI tự đọc cuộc trò chuyện, đề xuất Task – Owner – Deadline và bạn chỉ cần bấm Xác nhận để lưu sang Trello/Jira, bạn có muốn sử dụng không?
6. Bạn mong AI hỗ trợ tính năng nào nhất?
7. Điều gì khiến bạn lo ngại khi dùng AI này?

## Cách đếm và kết quả

**Con số pain chính: 17/24 = 70,8%.** Lọc cột `time_per_week`, đếm các
response khác `Dưới 10 phút`: 10 người chọn 10–30 phút, 5 người chọn 30–60
phút và 2 người chọn trên 1 giờ. Như vậy hơn 50% người được hỏi mất ít nhất 10
phút mỗi tuần chỉ để tổng hợp hoặc tìm lại thông tin trong chat.

**Ý định sử dụng: 20/24 = 83,3%.** Đếm 6 `Chắc chắn có` + 14 `Có thể`; không
gộp 2 `Chưa chắc`, 1 `Có thể không` và 1 `Chắc chắn không`.

| Chỉ số | Kết quả | Cách kiểm chứng |
|---|---:|---|
| Dùng Discord để trao đổi | 13/24 (54,2%) | Đếm `platform=Discord` |
| Dùng Zalo để trao đổi | 11/24 (45,8%) | Đếm `platform=Zalo` |
| Dùng Sheets/Jira/Notion/Trello | 22/24 (91,7%) | Đếm `task_tool` không phải `Chưa dùng/Không dùng` |
| Trả lời pain bằng văn bản | 16/24 (66,7%) | Đếm `pain_verbatim` không rỗng |
| Lo AI nhận diện sai | 14/24 (58,3%) | Đếm `concern=AI nhận diện sai` |
| Muốn tóm tắt cuộc họp | 17/24 (70,8%) | Tách `desired_features` theo dấu `;` |
| Muốn nhắc deadline | 16/24 (66,7%) | Tách `desired_features` theo dấu `;` |
| Muốn tự động tạo task | 13/24 (54,2%) | Tách `desired_features` theo dấu `;` |

## Ví dụ nguyên văn

- F01: “Đoạn chat cần thiết sẽ bị trôi khi mọi người thảo luận nhóm, muốn xem lại thì mấy thời gian.”
- F04: “Tin nhắn quan trọng bị trôi.”
- F10: “Miss tin nhắn.”
- F18: “Miss nhiều tin nhắn.”
- F21: “Hay bị miss tin nhắn.”
- F22: “Mình nghĩ là sẽ mất thời gian để tìm lại thông tin khi cần do tin nhắn bị trôi, đôi khi miss thông tin mới nhất và làm việc dựa trên thông tin cũ.”

## Đối chiếu với 5 phỏng vấn

- 5/5 người phỏng vấn đang dùng nền tảng/tool khác cho việc nhóm; 3/5 nói sẽ dùng thử giải pháp.
- Tuấn muốn sửa trực tiếp sang task tool; Lợi nói sẽ quay lại Discord.
- Mentor cảnh báo false positive làm người dùng phải dọn task sai. Vì vậy sản
  phẩm chỉ **propose**, luôn cần người dùng xác nhận trước khi write.

## Giới hạn bằng chứng

Form được phát trong cùng cộng đồng K4 và câu hỏi ý định sử dụng có mô tả giải
pháp, nên dùng kết quả 20/24 để chứng minh **willingness**, không dùng nó thay
cho quan sát hành vi. Con số 17/24 từ thời gian tìm lại thông tin và transcript
1-1 là bằng chứng pain chính.
