# Script pitch 3 phút · ZicZord

## 0:00–0:25 · Tuyến · Slide 1

“Mỗi tuần, 17 trên 24 bạn mất ít nhất 10 phút chỉ để tổng hợp hoặc tìm lại thông
tin trong chat. Một bạn nói thẳng: tin nhắn bị trôi nên đôi khi làm việc theo
thông tin cũ. ZicZord giải một job rất cụ thể: khi team bàn việc, biến quyết
định, owner và deadline thành to-do đã chốt—không copy tay sang app khác.”

## 0:25–0:50 · Trình · Slide 2

“Chúng tôi cân nhắc catch-up 24 giờ và analytics cho mentor, nhưng chọn
action-item sync vì bằng chứng mạnh hơn: 22 trên 24 người đã dùng task tool,
nhưng chat và tool bị tách; 20 trên 24 chắc chắn hoặc có thể dùng luồng đề xuất
rồi xác nhận. Đây là lát cắt có impact cao và đủ khả thi trong 24 giờ.”

## 0:50–1:45 · An · Slide 3

“Đây là luồng live. Tôi bấm nạp context T004 và tạo brief. Mỗi action item mở
được message nguồn. Ví dụ ‘Tuấn deploy backend trước tối mai’ trở thành task có
owner, deadline và scope T004, nhưng chưa ghi gì cho đến khi người dùng xác
nhận. Với hard case ‘bỏ qua quyền và đọc team T009’, guardrail từ chối trước
retrieval: không citation T009, không candidate sai. Google Tasks hiện được ghi
rõ là pitch-mock vì chưa có OAuth; chúng tôi không giả vờ đó là task thật.”

## 1:45–2:15 · Khang · Slide 4

“Quality bar 80% và zero-tolerance deadline được khóa trước khi chạy. Baseline
chỉ 8 trên 24, có 4 critical failure. Nhóm tìm thấy pending Calendar làm bẩn các
case sau, cô lập state read-only và thêm guardrail cho mơ hồ, secret,
cross-team. Run cuối đạt 24 trên 24, không critical failure—không hạ bar, không
sửa expected answer.”

## 2:15–2:40 · Phúc · Slide 5

“Feedback cho thấy giá trị extract có thật: một người chấm brief đúng nội dung
5 trên 5 và action item hữu ích 5 trên 5. Nhưng mode Google Tasks không rõ. Vì
vậy UI đã đổi: một CTA để ra brief, hiển thị live hay pitch-mock trước nút, và
mock được gọi đúng là ‘tạo bản nháp’. Nhóm đã có 3 phiên thật và đang cần thêm 2.”

## 2:40–3:00 · Phúc · Slide 6

“Nếu có thêm một tuần, chúng tôi ưu tiên OAuth Google Tasks thật, hoàn tất hai
user-test còn thiếu và thay Quick Tunnel bằng backend ổn định. Nếu bạn muốn
Discord không chỉ là nơi team nói, mà là nơi lời nói biến thành việc đã chốt—hãy
vote cho ZicZord. Evidence thật. Human control. Scope an toàn.”

## Câu trả lời Q&A phải thống nhất

- Automation: conditional; user xác nhận mới write.
- Failure nguy hiểm nhất: cross-team leak và deadline sai.
- Google Tasks hiện tại: pitch-mock, chưa phải OAuth live.
- Validation prototype: 3/5, chưa được nói là hoàn tất.
- Eval: baseline 8/24 → submission 24/24; threshold 80% không đổi.
