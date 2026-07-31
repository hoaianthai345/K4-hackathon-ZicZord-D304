# Canvas CP1 · Nhóm ZicZord · Team T004 · Lớp D304

*(7 dòng theo `02-guide.md §1.5` — snapshot CP1; slice đã pivot ngày 31/07 sau survey n=24 + 5 interview, xem [spec.md §9 Changelog](spec.md) + [validation/](validation/))*

1. **Hướng:** B — Trợ lý Học viên (Discord). Loại: tính năng mới — **Discord Action-Item Copilot** (bot đọc chat team → propose task/deadline/decision → sync 1-click sang task tool).
2. **Job executor:** team học viên K4 3-5 người đang chạy project 6 tuần (ví dụ T004 · G10 mentor · LEC-D302 · LAB-D304) khi bàn công việc trong chat và cần ghi lại decision/task/deadline vào cùng chỗ với to-do list team đang dùng — mà không phải copy tay sang tool khác.
3. **Pain 1 câu:** team học viên K4 phải tách chat và task tool: 22/24 người khảo sát dùng Sheets/Jira/Notion/Trello, 17/24 mất ≥10 phút/tuần để tổng hợp hoặc tìm lại thông tin trong chat; 5 interview cho thấy team chuyển giữa Discord, Zalo, Messenger, Trello và Sheets.
4. **Bằng chứng đầu:** chuẩn A n=24 ([survey-log.md](validation/survey-log.md)): 17/24 (70,8%) mất ≥10 phút/tuần; 20/24 (83,3%) chắc chắn/có thể dùng; 5 interview có transcript nguyên văn, 3/5 sẽ dùng. Chuẩn B từ mining pack ở [evidence/mining-report.md](evidence/mining-report.md).
5. **Lát cắt MỘT CÂU:** team học viên chat trong `#🤖-gõ-commands` → bot đọc + phân loại message (task/decision/deadline/blocker/noise) trong scope allowed + đề xuất owner + đề xuất scope → user confirm bằng click hoặc trả lời email → sync sang Google Calendar/task tool + notify owner + track deadline.
6. **Automation: conditional-with-confirm** — bot chỉ **propose candidate**, KHÔNG bao giờ auto-write; user confirm mới ghi ra external tool. Lý do (trực tiếp từ Mentor interview): *"AI làm sai sẽ khiến người dùng cảm thấy mất công chui vào check và xóa"* — false positive từ câu đùa/misspell là risk lớn nhất. **Willing users tên thật:** Nguyễn Văn Tuấn (U01246) · Senior/Mentor · Lợi.
7. **Phân công:** PM (FE) — Nguyễn Hữu Tuyến (2A202601520) · Agent Design — Thái Hoài An (2A202601862) · Scraw dữ liệu Discord + eval — Vũ Thành Khang (2A202601866) & Trịnh Bá Khánh Trình (2A202601531) · Frontend UI — Nguyễn Văn Phúc (2A202601350).
