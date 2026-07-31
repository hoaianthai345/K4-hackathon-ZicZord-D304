# Kế hoạch điều hành hackathon 24 giờ: ZicZord

Product wedge: **AI trợ lý trong Discord nhớ đúng phạm vi**
Mục tiêu pitch: chứng minh học viên tự lấy lại context mà không phải tag moderator.

## Scope freeze

Build đúng một happy path:

```text
Discord snapshot
→ map channel và membership
→ recall đúng user/team/group/room/cohort
→ summary có citation
→ confirm một memory mới
```

Không build bot production, dashboard admin, notification, calendar hoặc analytics toàn lớp.

## Bốn lane cho team 4 người

| Lane | Output sở hữu | Gate |
|---|---|---|
| PM + Demo | spec, pitch narrative, 3 câu hỏi demo | Nói rõ pain và scope trong 30 giây |
| Backend + Data | Apify adapter, access gate, FastAPI | Test T004 không đọc được T009 |
| Memory + Eval | Hindsight banks, candidate promotion, golden cases | Proposed không được recall như canonical |
| Frontend + QA | landing pitch, Discord UI, browser regression | Demo không cần sửa dữ liệu bằng tay |

Mỗi artifact có một DRI và một reviewer. Kẹt quá 20 phút phải giảm scope hoặc dùng snapshot demo.

## Đồng hồ 24 giờ

| Giờ | Outcome |
|---:|---|
| H0 | Chốt user graph T004, G10, D302, D304, K4 và ba câu demo |
| H1 | Schema message, channel, membership, scoped memory được freeze |
| H3 | FastAPI trả Discord state đã lọc theo user |
| H5 | Ba query demo trả summary có citation |
| H7 | Candidate confirm chạy và test permission pass |
| H9 | Apify adapter normalize được fixture và bỏ unknown channel |
| H11 | Discord UI click được channel, bot command và context rail |
| H13 | Landing pitch kể đúng problem, model, demo, trust |
| H15 | Docker build và smoke test end-to-end |
| H17 | Golden test access, citations, ingest, confirm |
| H19 | Dry run lần một, sửa tối đa ba lỗi cản demo |
| H21 | Build freeze, quay backup video hoặc chụp backup |
| H23 | Dry run dưới 5 phút, kiểm tra key và dữ liệu nhạy cảm |
| H24 | Pitch bằng live app |

## Script pitch 5 phút

1. **Pain, 40 giây:** cho xem bot phải tag Mod vì không biết bài giảng và chat trước đó.
2. **Model, 50 giây:** An thuộc đồng thời T004, G10, Lec-D302, Lab-D304 và K4.
3. **Demo, 2 phút:** hỏi bài giảng hôm qua, team đang chốt gì, mentor dặn gì.
4. **Memory, 40 giây:** nói một quyết định mới, confirm scope T004.
5. **Trust, 35 giây:** chuyển sang user T009 và chứng minh không nhìn thấy T004.
6. **Close, 15 giây:** bot nằm trong workflow hiện tại, giảm câu hỏi lặp lại cho mentor.

## Kill switch

- Apify token lỗi: dùng snapshot synthetic, vẫn hiển thị rõ `Demo snapshot`.
- Hindsight lỗi: local JSON giữ source of truth và hiện `hindsight-fallback`.
- LLM chậm: response deterministic từ evidence demo, không giả trạng thái đang gọi model.
- Frontend lỗi panel phụ: giữ command channel, ba query và citation.
- Discord permalink demo không mở được server thật: vẫn giữ ID và label nguồn trong UI.

## Quality gates

1. `pytest`: access isolation, summary citation, candidate permission, Apify normalize.
2. `eslint` và `next build`.
3. Production dependency audit không có vulnerability đã biết.
4. Docker health và HTTP smoke.
5. Desktop, mobile, light, dark, loading, empty và error state.

## Điều cần con người bổ sung

- Tên thật của 4 thành viên và DRI.
- Apify Actor hoặc dataset đang dùng trong server được cấp quyền.
- Xác nhận của ban tổ chức về channel được ingest.
- Ít nhất 5 user test cho ba câu hỏi demo.
- Số phút đọc lại Discord và số câu moderator phải trả lời lặp, nếu muốn claim impact.
