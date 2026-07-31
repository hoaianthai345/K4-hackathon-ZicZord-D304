# Submission checklist · ZicZord

Đối chiếu theo `02-guide.md §5.2` và `04-rubric.md`. Cập nhật 31/07/2026.

## Deliverable repo

| Yêu cầu | Trạng thái | Bằng chứng |
|---|---|---|
| README có thành viên + phân công cụ thể | ✅ | `README.md` bảng 5 thành viên và deliverable |
| `spec.md` | ✅ | Map R1–R7, impact, 4 lớp rủi ro, flow, eval |
| `demo-slides.pdf` đúng 6 trang | ✅ | `demo-slides.pdf` + `demo-slides.html` |
| `codebase/` chạy được | ✅ | Docker Compose; backend health và frontend build |
| `eval/` có ≥20 case, bar khóa, baseline + full run | ✅ | 24 case; baseline 8/24; submission 24/24; bar 80% |
| `validation/` có evidence A | ✅ | 24 response ẩn danh + 5 transcript interview |
| User-test prototype ≥5 người | ⚠️ 3/5 | `validation/user-test-log.md`; cần thêm 2 phiên |
| `reflection/` mỗi thành viên một file | ⚠️ 4/5 | Đã có Tuyến, An, Trình, Khang; thiếu Phúc |
| Backup demo screenshot/video | ✅ ảnh | `demo/production-landing.png` + `demo/production-t004-brief.png`; video 60–90 giây vẫn nên quay |

## Bằng chứng và rubric

| Rubric | Trạng thái | Ghi chú |
|---|---|---|
| R1 · Bằng chứng + impact | ✅ | 17/24 mất ≥10 phút/tuần; 20/24 chắc chắn/có thể dùng; có cách đếm và log |
| R2 · Lát cắt + thiết kế | ✅ | Một user/job/decision/outcome; alternatives + HAX/PAIR cụ thể |
| R3 · Chỗ khó + kịch bản | ✅ | 4 lớp, ≥8 tình huống, happy/clarify/fail/correction/out-of-scope |
| R4 · Kiểm thử | ✅ | 24 case, 4 risk type, frozen bar, baseline và submission đầy đủ |
| R5 · Prototype | ✅ | Web + backend + T004 pitch flow + citation + task connector |
| R6 · Validation | ⚠️ | Có 3 feedback thật và change log; thiếu 2 user-test để tối đa điểm |
| R7 · Repo + phân công | ✅ | Deliverable gắn tên từng thành viên |

## Trước khi lên pitch

1. Mở https://kute-discord-copilot.vercel.app/ và kiểm tra frontend tải được.
2. Kiểm tra backend tunnel còn sống; nếu tunnel đổi URL, cập nhật Vercel env rồi
   deploy lại.
3. Trong `/chat`, chạy `Nạp context & tạo brief`; mở ít nhất một citation.
4. Nói rõ Google Tasks đang là `pitch-mock` nếu chưa cấu hình OAuth; không gọi
   đó là task thật.
5. Demo một happy path và một hard case: `deadline?` hoặc yêu cầu đọc team T009.
6. Mỗi thành viên phải nói ít nhất một phần và giải thích được deliverable có tên.

## Việc không thể tự điền thay thành viên/người dùng

- Hai người ngoài nhóm cần tự chạy prototype và để lại feedback quan sát được.
- Nguyễn Văn Phúc cần tự viết reflection:
  vai trò, AI hỗ trợ gì, một case fail thật và nếu làm lại sẽ đổi gì.
- OAuth Google Tasks cần owner tài khoản Google cấp quyền; nếu không có, giữ
  pitch-mock và trình bày trung thực.
