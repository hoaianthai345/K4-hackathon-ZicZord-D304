# Canvas CP1 · Nhóm ZicZord · Zone [X] · Lớp D304

*(7 dòng theo `02-guide.md §1.5` — hạn K4: 15:00 N1)*

1. **Hướng:** B — Trợ lý Học viên (Discord). Loại: tính năng mới — **Kute Memory / Discord Learning Copilot**.
2. **Job executor:** học viên K4 (ví dụ An, U01862 · team T004 · group G10 · lớp LEC-D302 & LAB-D304 · cohort K4) khi quay lại Discord sau một ngày học/làm project và cần biết lớp/team/mentor đã chốt gì mà không phải đọc lại mọi channel.
3. **Pain 1 câu:** học viên tag bot yêu cầu tóm tắt chat & bài giảng hôm qua, nhưng bot hiện tại thiếu context (25.5% user có recap request, 65.1% recap không citation, 0 misconception tracking — [evidence/mining-report.md](evidence/mining-report.md)) → phải tag moderator hoặc bỏ qua, thông tin chốt phân mảnh qua ≥5 channel (chung/team/group mentor/lớp/lab).
4. **Bằng chứng đầu:** mining `data/vlearn-pack/chatlog` — 2.522 dòng, 369 học viên ẩn danh, 585 conversation; 130/369 (35.2%) user đi qua nhiều conversation; 129 recap request từ 94 user; ≥5 quote nguyên văn (T0303 "bạn có nhớ câu hỏi mà tôi trả lời không", T0985 "tóm tắt lại hôm nay đã học những gì", …).
5. **Lát cắt MỘT CÂU:** học viên hỏi Trợ lý Kute trong `#🤖-gõ-commands` → hệ thống tính scope được phép từ membership (user/team/group/room/cohort) + truy xuất message & memory liên quan trong đúng bank được authorize → trả summary có permalink nguồn hoặc từ chối rõ khi không đủ evidence.
6. **Automation: conditional** — auto trả với query có evidence trong allowed scope; refuse `403` với cross-scope; propose memory chờ user confirm với candidate mới. Lý do cost-of-error: gán quyết định sai team → học viên nhận info sai → quyết định sai. **Willing users dự kiến:** [tên1 · An U01862 T004] · [tên2 · …] · [tên3 · …].
7. **Phân công:** PM+Demo — [tên] · Backend+Data (Apify adapter, FastAPI, access gate) — [tên] · Memory+Eval (Hindsight banks, golden cases) — [tên] · Frontend+QA (landing pitch, Discord UI) — [tên].
