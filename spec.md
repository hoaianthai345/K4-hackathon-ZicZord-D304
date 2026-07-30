# AI SPEC: Kute Memory, Discord Learning Copilot

Hướng đề xuất: **Trợ lý học viên trong Discord**
Loại: **Tính năng mới**
Trạng thái: **MVP scope đã đổi ngày 30/07/2026**

## 1. User và job

User chính là học viên K4 đang làm project theo team 4 người trong 6 tuần.

Ví dụ quan hệ:

```text
Thái Hoài An, U01862
  thuộc team T004
  thuộc group G10 có mentor
  học lý thuyết tại Lec-D302
  học thực hành tại Lab-D304
  tham gia kênh chung, hỏi đáp và chia sẻ của K4
```

Core job:

> Khi quay lại Discord sau một ngày học và làm project, giúp tôi biết lớp, team và mentor đã chốt gì mà không phải đọc lại mọi channel.

Pain quan sát trực tiếp từ ảnh Discord:

- Học viên yêu cầu bot tóm tắt chat chính và bài giảng hôm qua.
- Bot hiện tại không có đủ context nên tag moderator.
- Trao đổi về repo, setup, nền tảng và requirement bị phân mảnh qua kênh chung, phòng học, group mentor và channel team.

Ảnh chỉ là evidence định tính. MVP không tự gán số phút tiết kiệm hoặc tỷ lệ nhu cầu khi chưa có survey.

## 2. Lát cắt MVP

> Một học viên hỏi Trợ lý Kute trong Discord; hệ thống tính các scope được phép từ membership, truy xuất message và memory liên quan, rồi trả summary có permalink nguồn.

Một quyết định AI trung tâm:

```text
authenticated user
  + channel membership
  + query intent
  + confirmed memory
→ chọn evidence nào được phép dùng để trả lời
```

Ba câu hỏi demo:

1. `Tóm tắt nội dung bài giảng ngày hôm qua`
2. `Team mình đang chốt gì và còn blocker nào?`
3. `Mentor G10 dặn gì trước buổi check-in?`

## 3. Data model và quyền

### Năm memory scope

| Scope | Ví dụ của An | Nội dung phù hợp |
|---|---|---|
| `user` | `U01862` | preference, reminder cá nhân |
| `team` | `T004` | quyết định, task, blocker project |
| `group` | `G10` | feedback, check-in từ mentor |
| `room` | `LEC-D302`, `LAB-D304` | bài giảng, hướng dẫn lab |
| `cohort` | `K4` | thông báo, hỏi đáp, chia sẻ |

Allowed scope được tính ở FastAPI. Client không gửi danh sách bank hoặc scope để tự mở rộng quyền.

### Access rule

```text
allowed(user) =
  user:<id>
  + team:<team_id>
  + group:<group_id>
  + room:<lecture_room_id>
  + room:<lab_room_id>
  + cohort:<cohort_id>
```

Message thuộc channel ngoài tập trên bị loại trước retrieval. Channel chưa map khi ingest Apify cũng bị bỏ, không mặc định thành public.

### Promotion rule

```text
Discord message = evidence quan sát được
memory candidate = proposed
confirmed memory = canonical memory có thể recall
```

Học viên có thể confirm memory cá nhân hoặc team mình. Memory group, room và cohort chỉ mentor có quyền sửa.

## 4. Nguồn dữ liệu

### Discord snapshot qua Apify

Backend đọc Apify Dataset API:

```text
GET /v2/datasets/{dataset_id}/items
Authorization: Bearer <APIFY_TOKEN>
format=json&clean=1&offset=...&limit=...
```

Adapter chuẩn hóa các Actor output khác nhau về:

```json
{
  "source_message_id": "string",
  "channel_id": "mapped internal channel",
  "author_id": "mapped community user",
  "author_name": "string",
  "content": "string",
  "created_at": "ISO-8601",
  "permalink": "https://discord.com/channels/..."
}
```

MVP chạy được không cần token bằng snapshot synthetic. Live mode chỉ cần `APIFY_TOKEN` và `APIFY_DATASET_ID`.

### Hindsight

- Source: `vectorize-io/hindsight`
- Pin: `0.8.6`
- Dùng một bank riêng cho mỗi scope.
- Recall chạy song song trên đúng tập bank server đã cấp.
- Tag canonical bắt buộc: `scope_type`, `scope_id`, `layer:canonical`, `status:confirmed`.
- JSON store là source of truth của demo; Hindsight là memory engine tùy chọn.

## 5. Product flow

### Happy path

1. Học viên mở `#🤖-gõ-commands`.
2. Hỏi về bài giảng, team hoặc mentor.
3. Bot trả tối đa ba ý, mỗi ý có citation về message Discord.
4. Panel bên phải hiển thị scope và confirmed memory được dùng.

### Xem channel nguồn

1. Học viên bấm một channel trong sidebar.
2. Giao diện hiện Discord snapshot ở chế độ chỉ đọc.
3. Bấm `Nhờ Kute tóm tắt kênh này`.
4. Trợ lý quay về command channel và trả lời có nguồn.

### Tạo memory

1. Học viên nói một quyết định, task, blocker hoặc preference.
2. Hệ thống tạo `proposed memory` với scope được suy ra từ channel và membership.
3. User xác nhận hoặc bỏ qua.
4. Chỉ sau confirm mới retain canonical memory.

### Ngoài phạm vi

- Query từ T004 không được dùng message hoặc memory T009.
- User không thuộc channel nhận `403`.
- Apify item từ channel chưa map bị skip.
- Không scrape DM hoặc channel ẩn.

## 6. Non-goals

1. Không xây bot Discord production hoặc self-bot.
2. Không scrape server khi chưa có quyền của ban tổ chức.
3. Không thay thế Discord search cho mọi use case.
4. Không tự biến mọi tin nhắn thành memory.
5. Không phân tích cảm xúc, năng lực hay hiệu suất cá nhân.
6. Không xây dashboard quản trị đầy đủ.

## 7. Trust và privacy

- Chỉ ingest server và channel được phép; không dùng user token để chạy self-bot.
- Apify token chỉ tồn tại ở backend và truyền bằng `Authorization` header.
- Response factual luôn có citation.
- Chưa đủ source thì nói không đủ dữ liệu.
- Memory có source message ID và có thể xóa.
- Access control được test bằng negative case T004 và T009.

## 8. Quality bar

MVP đạt khi:

- 0 message hoặc memory cross-team trong test.
- 100% ý summary demo có citation.
- 100% channel chưa map fail closed.
- Proposed memory không xuất hiện trong canonical recall.
- User không có quyền không thể confirm, sửa hoặc xóa memory.
- Landing, chat, API và Docker build chạy bằng một lệnh.

## 9. Changelog

| Ngày | Thay đổi | Lý do |
|---|---|---|
| 30/07/2026 | Đổi từ standalone learning tutor sang Discord Learning Copilot | Pain tóm tắt và thiếu context xuất hiện trực tiếp trong Discord |
| 30/07/2026 | Mở rộng memory từ per-user sang 5 scope | Phản ánh đúng cấu trúc user, team, group mentor, phòng học và cohort |
| 30/07/2026 | Thêm Apify Dataset adapter | Có đường ingest Discord snapshot thay được Actor |
| 30/07/2026 | Bank-per-scope và server-side authorization | Chặn recall sai team ở boundary mạnh hơn |
