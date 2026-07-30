# AI SPEC: Kute, Discord Catch-up Copilot

Hướng đề xuất: **Discord Catch-up Copilot**
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

> Khi quay lại Discord sau một ngày, giúp tôi biết ngay có gì thay đổi, mình cần làm gì và vấn đề nào đang chặn team—không phải đọc lại nhiều channel.

Pain quan sát trực tiếp từ ảnh Discord:

- Học viên yêu cầu bot tóm tắt chat chính và bài giảng hôm qua.
- Bot hiện tại không có đủ context nên tag moderator.
- Trao đổi về repo, setup, nền tảng và requirement bị phân mảnh qua kênh chung, phòng học, group mentor và channel team.

Ảnh chỉ là evidence định tính. MVP không tự gán số phút tiết kiệm hoặc tỷ lệ nhu cầu khi chưa có survey.

## 2. Lát cắt MVP

> Một học viên bấm “Bắt kịp 24 giờ qua”; hệ thống tính scope từ membership, đọc đúng channel rồi trả brief có quyết định, task, deadline, blocker và permalink nguồn.

Một quyết định AI trung tâm:

```text
authenticated user
  + channel membership
  + query intent
  + confirmed memory
→ chọn evidence nào được phép dùng để trả lời
```

Happy path demo:

1. Bấm `Bắt kịp trong 24 giờ qua`.
2. Xem brief theo bốn loại thông tin.
3. Mở nguồn Discord của một ý.
4. Bấm `Tạo checklist hôm nay`.
5. Đánh dấu một việc hoàn tất hoặc hỏi tiếp.

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

### Dataset processing không phá huỷ

File Excel gốc chỉ đọc. Pipeline tạo ba dataset dẫn xuất:

- `messages_clean`: NFC, whitespace, search lowercase, model text đã redact, cờ noise/intent, attachment và reaction chuẩn hóa.
- `issue_episodes`: anchor → context topic-aware → answer/resolution.
- `painpoint_summary`: vector cluster theo `canonical_problem + product_area + entities`.

Dot/greeting không vào model context nhưng không ngắt episode. Acknowledgement được
giữ để nhận biết resolved signal. Report giống nhau từ người khác nhau không bị xóa.

### Hindsight

- Source: `vectorize-io/hindsight`
- Pin: `0.8.6`
- Dùng một bank riêng cho mỗi scope.
- Recall chạy song song trên đúng tập bank server đã cấp.
- Tag canonical bắt buộc: `scope_type`, `scope_id`, `layer:canonical`, `status:confirmed`.
- JSON store là source of truth của demo; Hindsight là memory engine tùy chọn.

### PostgreSQL + RAG-Anything

- PostgreSQL giữ toàn bộ `messages_clean`, `issue_episodes` và
  `painpoint_summary`, bao gồm provenance tới file/sheet/row.
- RAG dùng repo chính thức `HKUDS/RAG-Anything`, direct content insertion và
  LightRAG hybrid retrieval.
- Chỉ `content_model` đã redact được embed/index; raw text không rời audit DB.
- FastAPI tính allow-list scope ở server. RAG response mang source ID để mở
  evidence đã redact và kiểm tra quyền lần hai.
- Chat UI không đổi: có index thì dùng RAG thật, chưa có thì fallback demo cũ.

### Learning context pack

- Mount read-only transcript, slide PDF và tutor chatlog từ `data/vlearn-pack`.
- Loader tạo 2.019 record `learning_context`: 700 transcript segment, 58 slide
  page và 1.261 tutor Q&A.
- Search bài học dùng PostgreSQL FTS/trigram cục bộ; không bulk-embed pack ra
  provider ngoài.
- Chỉ excerpt `content_model` đã redact được gửi tới LLM; citation quay về đúng
  transcript code, slide page hoặc Q&A record.

### Retrieval plan

```text
lesson intent
  -> local learning search

explicit channel or time window
  -> exact Discord SQL search
  -> never broaden to another channel when empty

generic recurring problem
  -> RAG-Anything hybrid search

all paths
  -> confirmed memory recall within server-computed scopes
```

Time expression dùng timezone `Asia/Ho_Chi_Minh`. Alias “team mình”, “mentor”,
“hỏi đáp”, “lý thuyết” và “lab” được map sang channel thực của user từ
membership.

## 5. Product flow

### Happy path

1. Học viên mở `#🤖-gõ-commands`.
2. Bấm `Bắt kịp trong 24 giờ qua`.
3. Bot trả decision, task, deadline, blocker và announcement có citation.
4. Học viên tạo checklist, đánh dấu đã biết hoặc hỏi thêm.
5. Panel bên phải ưu tiên checklist; scope và memory lùi xuống trust layer.

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
6. Không xây analytics dashboard lớn; admin MVP chỉ quản lý context, memory và
   xem retrieval trace.

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
- File raw dataset không đổi checksum sau pipeline.
- Dot/greeting không vào episode context cuối; acknowledgement không bị xóa.
- Brief 24 giờ tạo checklist và lưu completed state.
- Learning loader chạy lặp lại vẫn giữ đúng 2.019 record.
- Query có time/channel không được tự mở rộng sang channel khác khi không có kết quả.
- Context tắt ở admin không xuất hiện trong search hoặc source endpoint.

## 9. Changelog

| Ngày | Thay đổi | Lý do |
|---|---|---|
| 30/07/2026 | Đổi từ standalone learning tutor sang Discord Learning Copilot | Pain tóm tắt và thiếu context xuất hiện trực tiếp trong Discord |
| 30/07/2026 | Mở rộng memory từ per-user sang 5 scope | Phản ánh đúng cấu trúc user, team, group mentor, phòng học và cohort |
| 30/07/2026 | Thêm Apify Dataset adapter | Có đường ingest Discord snapshot thay được Actor |
| 30/07/2026 | Bank-per-scope và server-side authorization | Chặn recall sai team ở boundary mạnh hơn |
| 30/07/2026 | Đổi định vị thành Discord Catch-up Copilot | Job rõ hơn: quay lại, bắt kịp và hành động |
| 30/07/2026 | Thêm non-destructive dataset pipeline | Giữ raw, tách episode theo topic và aggregate pain point |
| 30/07/2026 | Thêm brief 24h và checklist | Biến summary thành workflow có bước tiếp theo |
| 30/07/2026 | Thêm PostgreSQL + HKUDS/RAG-Anything | Truy vấn dữ liệu thật, có provenance và citation kiểm tra quyền |
| 30/07/2026 | Thêm learning context và admin | Hỏi được bài học thật, quản lý context/memory và kiểm tra retrieval plan |
| 30/07/2026 | Thêm strict time/channel routing | Ngăn semantic retrieval lấy đúng chủ đề nhưng sai channel hoặc thời điểm |
