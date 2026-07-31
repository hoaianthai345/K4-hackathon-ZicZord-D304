# AI SPEC: Kute, Discord Action-Item Copilot

Hướng đề xuất: **Discord Action-Item Copilot — bot đọc chat team, đề xuất task/deadline/decision, đồng bộ 1-click sang task tool** (Hướng B — Trợ lý Học viên)
Loại: **Tính năng mới**
Trạng thái: **MVP scope đã pivot ngày 31/07/2026 sau 5 interview — xem §9 Changelog**

## 🧭 Rubric section map — chấm ở section nào

Spec này giữ cấu trúc engineering của nhóm (§1-§9) và bổ sung §10-§16 để phủ đủ
rubric. Bảng dưới cho biết mỗi block rubric chấm ở đâu:

| Rubric | Chấm ở |
|---|---|
| R1 · Bằng chứng & impact (15đ) | §1 evidence + [evidence/mining-report.md](evidence/mining-report.md) + **§10 Impact table** |
| R2 · Lát cắt & thiết kế (15đ) | §2 Lát cắt + §6 Non-goals + **§11 Giải pháp tương tự** + **§12 HAX/PAIR áp cụ thể** |
| R3 · Chỗ khó & kịch bản (11đ) | §7 Trust/privacy + [architecture/](architecture/) + **§13 4 lớp ①②③④ + ≥8 kịch bản** + **§14 4 đường đi trải nghiệm** |
| R4 · Kiểm thử (15đ) | §8 Quality bar engineering + **§15 Golden set + quality bar %** + [eval/](eval/) |
| R5 · Prototype (8đ) | [codebase/](codebase/) + [architecture/data-flow.md](architecture/discord-scope-model.md) |
| R6 · Validation (8đ) | [validation/interview-script.md](validation/interview-script.md) + `validation/user-test-log.md` |
| R7 · Repo & phân công (3đ) | [README.md](README.md) roster + **§16 Phân công có tên** |

## 1. User và job

**Job executor:** học viên K4 đang làm project theo team 3-5 người trong 6 tuần
(ví dụ team T004 · group G10 có mentor · phòng LEC-D302 & LAB-D304 · cohort K4).

**Core JTBD (không tên sản phẩm/AI trong câu):**

> Khi team bàn công việc, giúp tôi ghi lại quyết định, task và deadline vào cùng
> một chỗ với to-do list team đang dùng — mà không phải copy tay từ chat sang tool
> khác.

**Problem statement (KHÔNG chữ AI):**

Team học viên K4 hầu như **KHÔNG dùng Discord Build Face để phân công công việc**
— dùng Zalo/Messenger/Trello/Google Sheets thay. Discord bị "bỏ rơi" (chỉ dùng
cho daily standup + weekly). Nguyên nhân: Discord không có task management tool
tích hợp, học viên phải chuyển tab sang tool khác để cập nhật task; action item
từ chat bị mất; deadline miss; thông tin phân tán qua ≥3 platform.

### Evidence

**Chuẩn A — khảo sát (đã có 5/20, log đầy đủ ở [validation/interview-transcripts.md](validation/interview-transcripts.md)):**

- **5/5 xác nhận pain** "Discord bị underused vì thiếu tool quản lý task" = **100%** ≥ ngưỡng 50%.
- Nền tảng thực tế đang dùng: **Trello · Messenger + Sheets · Discord + Sheets · Zalo + Discord standup · Zalo only**.
- **3/5 nói sẽ dùng bot** = 60% (Tuấn 1246, Mentor, Lợi). Xem [survey-log.md](validation/survey-log.md).
- ≥5 quote nguyên văn:
  1. **Duy (1780)** *"Em sử dụng nền tảng khác ạ... Là cái Trello."*
  2. **Minh (01306)** *"Không, mình bàn bạc trên Messenger... Mình dùng Google Docs để chia việc. Hoặc là cái Sheet."*
  3. **Tuấn (1246)** *"Mình thấy hợp lý"* + *"Nếu mà sửa được luôn bên Jira thì ok."*
  4. **Mentor** *"Đúng vai trò với ban tổ chức thôi. Nhưng mà đúng vai trò với từng cá nhân học sinh thì là chưa."*
  5. **Lợi** *"Đang chỉ nhắn Zalo thôi... nếu mà làm được như thế thì tốt, mình sẽ sử dụng"* → *"sẽ quay lại Discord."*

**Chuẩn B — mining (đã có, xem [evidence/mining-report.md](evidence/mining-report.md)):**
- 2.522 dòng chatlog VLearn, 369 học viên ẩn danh, 585 conversation.
- Recap request patterns → xác nhận nhu cầu "bắt kịp/tổng hợp" tồn tại; kết hợp với chuẩn A cho thấy nhu cầu **task management** là gap thật.

**Warning từ interview (áp cho §5 + §13):**
- **Mentor:** *"AI làm sai sẽ khiến người dùng cảm thấy mất công chui vào check và xóa"* — false positive từ câu đùa/misspell là risk lớn nhất → automation phải là **conditional với confirm step**, KHÔNG auto-write ra task tool.
- **Mentor:** *"Quản lý memory của agent, với số lượng 1000 học viên hiện tại thì hơi nhiều"* — MVP demo scope 1 team T004 chấp nhận được.

## 2. Lát cắt MVP — MỘT CÂU

> **Team học viên** *(1 user)* **chat trong `#🤖-gõ-commands`** *(1 việc: bàn công việc)* **→ bot đọc + phân loại message thành candidate action item (task/decision/deadline/blocker/noise) trong scope allowed + đề xuất owner + đề xuất scope** *(1 quyết định AI)* **→ user 1-click confirm/edit → sync sang task tool (Jira/Sheets adapter) + notify owner + track deadline** *(1 kết quả)*.

**Central AI decision:** classify(message, membership) → `{class ∈ [noise, task, decision, deadline, blocker], suggested_owner, suggested_scope, evidence_span}` — HỆ THỐNG KHÔNG BAO GIỜ TỰ WRITE task, chỉ propose; user confirm mới ghi ra Jira/Sheets.

**Automation: conditional** — lý do cost-of-error (mentor cảnh báo trực tiếp trong interview 4):
- **Sai thì đắt:** gán task từ câu đùa / gán owner sai / deadline sai → user phải dọn dẹp → mất trust → team bỏ dùng.
- **Sửa rẻ nếu prevent:** bắt buộc confirm step trước khi write ra external system.

Happy path demo:

1. Team T004 chat: *"@Tuấn deploy backend trước tối mai nhé"*.
2. Bot ghim reply có card đề xuất: **task**: "Deploy backend"; **owner suggest**: Tuấn (U01246); **deadline suggest**: 2026-08-01 23:59; **scope**: team T004.
3. Tuấn bấm ✓ confirm → task ghi ra Jira (hoặc Sheets fallback).
4. Bot xác nhận: link Jira + đếm ngược deadline; notify Tuấn.
5. Nếu Tuấn bấm ✗ hoặc bot phân loại là `noise` (câu đùa) → không ghi, không hỏi lại.

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
| **31/07/2026** | **PIVOT lát cắt: từ "Catch-up 24h" sang "Action-Item Extract + Sync"** | Sau 5 interview ([validation/interview-transcripts.md](validation/interview-transcripts.md)): 5/5 xác nhận pain "Discord bị bỏ rơi vì thiếu task tool"; 3/5 nói sẽ dùng nếu bot đọc chat + đồng bộ task tool. Value prop mạnh nhất: **Lợi "sẽ quay lại Discord"**. Slice cũ (catch-up) chưa được validate trực tiếp — giữ lại cho v2. |
| 31/07/2026 | Chuyển automation từ "trả lời tự động" sang **conditional-with-confirm** | Warning từ Mentor: *"AI làm sai sẽ khiến người dùng cảm thấy mất công chui vào check và xóa"* — false positive từ câu đùa là risk lớn nhất. Bot chỉ được **propose candidate**; user confirm mới write ra external tool. |
| 31/07/2026 | Cập nhật §16 willing users với 3 tên thật | Interview 3 (Tuấn 1246), 4 (Mentor), 5 (Lợi) đồng ý test — đủ tiêu chí 5 nghiệm thu. |

---

## 10. Impact & quyết định chọn *(R1 — bảng ≥3 ứng viên, cập nhật 31/07 sau interview)*

### Bảng impact 5 ứng viên đã cân nhắc

| # | Ứng viên | Số người ảnh hưởng | Tần suất | Tốn gì mỗi lần | Cost-of-error | Khả thi 24h | Kết luận |
|---|---|---:|---|---|---|---|---|
| 1 | **Extract + sync action item** (bot đọc chat → propose task/deadline → sync Jira/Sheets qua confirm) | ~50-80 team × 3-5 hv = 150-400 hv có team đang chạy project | vài lần/ngày mỗi team | 3-5' copy tay từ chat sang tool khác × mỗi task; **cost hiện tại: team bỏ Discord** | **Trung-cao** (false positive → user dọn dẹp, mất trust) | ✅ Có Apify snapshot + adapter mock task tool | **✅ CHỌN** — 5/5 interview xác nhận pain; 3/5 sẽ dùng; 1 nói "sẽ quay lại Discord" |
| 2 | Catch-up 24h (bắt kịp sau khi vắng/nghỉ) | ~200 hv K4 | ≥1/ngày cho user quay lại | 15-30' đọc lại nhiều channel | Trung-cao | ✅ | **LOẠI cho v1** — chưa được validate trực tiếp bởi interview; feature phụ trợ, có thể v2 |
| 3 | Recap sau buổi học có citation | 94 user (25.5% từ mining) | 129 recap request/tuần | 5-15' tự đọc lại | Trung bình | ✅ | **LOẠI** — hướng A (VLearn tutor recap), không phải Discord task |
| 4 | Tutor tự kiểm tra hiểu / quiz sinh | 369 user | mỗi buổi | học sai kiến thức | **Cao** | ⚠️ cần dataset quiz | **LOẠI** — hướng A, không phải Direction B |
| 5 | Analytics dashboard mentor xem lớp | 5-10 mentor | 1/ngày | 15' tự tổng hợp | Thấp | ⚠️ big scope | **LOẠI** — v2, không giải pain trực tiếp học viên |

### Ứng viên đã chọn — #1 (Extract + sync)

**Lý do chọn bằng số:**
- **5/5 interview (100%) xác nhận pain** — Discord bị underused vì thiếu task tool (Trello/Sheets/Zalo/Messenger đang thay).
- **3/5 (60%) sẽ dùng** — trong đó **Lợi (100% Zalo hiện tại) nói "sẽ quay lại Discord"** — bằng chứng trực tiếp cho value prop "kéo team về Discord".
- **Tuấn (dùng Discord+Sheets)** xin thêm feature 2-way sync — dấu hiệu user sẵn sàng dùng nhiều hơn nếu ma sát giảm.
- **Cost-of-error đã có mitigation cụ thể** (từ Mentor): confirm step trước khi write.

**Ứng viên loại — lý do bằng số/từ interview:**
- #2 Catch-up: pain hợp lệ nhưng KHÔNG có interview nào chủ động nêu — trong khi #1 có 5/5 chủ động nêu. Ưu tiên bằng chứng trực tiếp.
- #3-#4: hướng A, không phải Direction B.
- #5: 5-10 mentor << 150-400 hv target — impact/effort thấp.

## 11. Giải pháp tương tự đã nghiên cứu *(R2)*

| Sản phẩm | Flow | Đáng học | Đáng né | Mình khác gì |
|---|---|---|---|---|
| **Trợ lý Kute (BTC)** hiện có | tag → text reply | có mặt trong Discord flow học viên | không phân scope; không hiển thị lý do trả lời | **scope authorization server-side** (bank-per-scope), citation dẫn tới permalink Discord |
| **NotebookLM** (Google) | upload nguồn → hỏi → inline citation | UX citation nhảy về nguồn | user tự upload | corpus + memory theo scope tự động từ membership, không cần user upload |
| **Slack summary bots** (Loops, Notta) | tóm tắt channel/DM | button "catch me up" đúng job | không có access control chi tiết | phân biệt user/team/group/room/cohort thay vì flat channel-level |

## 12. Nguyên tắc HAX/PAIR đã áp *(R2 — mỗi cái trỏ vào chỗ cụ thể)*

| Nguyên tắc | Áp cụ thể ở đâu trong prototype |
|---|---|
| **G1 — Làm rõ hệ thống làm được gì** | Landing pitch (`codebase/frontend/src/components/pitch-deck.tsx`) + label 3 câu demo cố định trong `#🤖-gõ-commands` |
| **G2 — Làm rõ nó làm tốt đến đâu** | Panel bên phải hiển thị scope + confirmed memory được dùng cho mỗi câu trả lời (`chat-shell.tsx`) — user biết bot đang query từ đâu |
| **G10 — Thu hẹp phạm vi khi nghi ngờ (BẮT BUỘC)** | `backend/app/scopes.py` — cross-scope query trả `403`; retrieval plan `strict time/channel routing` không tự mở rộng sang channel khác khi empty |
| **G11 — Giải thích vì sao** | Mỗi ý summary demo có permalink về source message (spec §7: "Response factual luôn có citation") — user click về đúng message Discord |
| **G17 — Quyền kiểm soát tổng** | Memory promotion: candidate chờ user `confirm`; user có thể `delete` memory cá nhân và team mình; mentor có quyền cho group/room/cohort (`architecture/discord-scope-model.md` write permissions matrix) |

*(HAX toolkit: microsoft.com/haxtoolkit · PAIR: pair.withgoogle.com/guidebook)*

## 13. 4 lớp chỗ khó ①②③④ + kịch bản (≥10) *(R3, cập nhật cho slice Extract)*

| # | Message team chat | Lớp | Hành vi mong muốn của bot | Nguyên tắc |
|---|---|---|---|---|
| K01 | *"@Tuấn deploy backend trước tối mai nhé"* — action words rõ + owner + deadline | ⓪ | Card đề xuất: `task="Deploy backend"`, `owner=Tuấn(U01246)`, `deadline=2026-08-01 23:59`, `scope=T004` — chờ confirm | G11 |
| K02 | *"Team mình quyết dùng Next.js"* — decision rõ | ⓪ | Card decision + scope T004; chờ confirm; ghi vào Jira decision log | G11 |
| K03 | *"Chán quá deploy hoài lỗi 😂"* — câu than, có action word "deploy" nhưng KHÔNG PHẢI task | ①/noise | **Skip**, KHÔNG propose. Đây là case Mentor cảnh báo trực tiếp. | **G10** + guard "action_intent_score < threshold" |
| K04 | *"Deploy backend"* — thiếu owner, thiếu deadline | ② | Card đề xuất với `owner=?`, `deadline=?`; hỏi lại 1 câu: *"Ai làm và bao giờ xong?"* | G10 |
| K05 | *"@Minh deploy backend"* — nhưng Minh không thuộc team T004 (user posting là T004) | ③ | Đề xuất với `owner=null + warning`: *"Minh không thuộc team T004 — chọn owner khác hoặc bỏ qua"* | **G10** + `scopes.py` |
| K06 | *"Cho @Duy 3 ngày nữa nhé"* — deadline mơ hồ ("3 ngày nữa" từ khi nào?) | ② | Card với `deadline=?`; đề xuất "3 ngày từ hôm nay = 2026-08-03"; user confirm hoặc sửa | G11 |
| K07 | User bấm ✗ reject 3 lần liên tiếp cho cùng 1 owner | ② | Bot tạm ngưng propose cho message của user đó trong 5 phút; gợi ý mở feedback | G15 |
| K08 | Team T009 hỏi bot tạo task cho member team T004 (cross-team) | ③ | Từ chối `403`; bot không được confirm cross-team | scopes.py guard |
| K09 | Message chứa PII/số điện thoại/mật khẩu | ③ | Skip, không đề xuất task; log warning | privacy layer |
| K10 | Deadline gần (< 24h) mà không có owner rõ | ④ | Card với warning màu đỏ; **luôn kèm khuyến cáo** "kiểm tra lại với team lead"; conf tối đa 0.5 | **G10** — cost-of-error deadline cao |
| K11 | Bot tự confirm hộ user (auto-write không có click) | ④ (chống) | **Guard code chặn**: mọi write ra external tool phải qua endpoint `POST /confirm` với `user_id + candidate_id` — không có auto-mode | server-side gate |
| K12 | Adapter Jira/Sheets down | ① | Card giữ trong app state; báo user *"Chưa sync được — thử lại"*; không mất data | resilience |

**Case hiểm nhất:** K03 (câu đùa bị extract thành task). Đây là warning **trực tiếp
từ Interview 4 (Mentor)**: *"AI làm sai sẽ khiến người dùng cảm thấy mất công chui
vào check và xóa"*. Metric bar: false positive rate ≤ 10% trong golden set (§15).

## 14. 4 đường đi của trải nghiệm *(R3)*

| Đường | Ví dụ | UI hiển thị |
|---|---|---|
| **Happy path** | User T004 bấm "Bắt kịp 24h" | Summary 3 ý (decision/task/deadline) + permalink Discord + panel scope T004+G10+D302+D304+K4 |
| **Low-confidence ②** | *"chuyện gì đang xảy ra?"* thiếu ngữ cảnh | 1 câu hỏi lại (channel nào, khung giờ nào) |
| **Failure/không căn cứ ①** | Query không có evidence trong allowed scope | *"Chưa đủ dữ liệu"*, không cite, gợi ý tag mentor |
| **Correction** | User confirm sai memory | Delete được — memory có source ID; hoàn tác trong 5s (undo toast) |
| **Ngoài phạm vi ③** | T004 hỏi về T009 | `403` + message rõ: *"Bạn không thuộc scope này"* |
| **Đặc thù domain ④** | Bot gán decision cho sai team | Guard server-side: `scopes.py` chặn write ngoài membership; test T004↔T009 phải 0 leak |

## 15. Kiểm thử — Golden set + Quality bar % *(R4)*

### Chiều chất lượng có định nghĩa kiểm chứng được

| Chiều | Định nghĩa pass (đo tự động) |
|---|---|
| **class đúng** | Output `class` == `expected_class` |
| **scope authorization đúng** | `got_scopes ⊆ user_allowed_scopes` (không leak) |
| **citation có** | Với case `0_answerable`, response phải có ≥1 citation (source_message_id hoặc transcript_code) |
| **no cross-scope leak** | Số evidence từ scope không thuộc user = 0 (bar tuyệt đối) |

### Golden set — 22 case tại `eval/golden_set.csv`

Cơ cấu theo `02-guide.md §2.6`:
- ⓪ `0_answerable` (có evidence trong scope): 7 case
- ① `1_no_source`: 4 case
- ② `2_ambiguous`: 3 case
- ③ `3_out_of_scope` (cross-scope, cross-team, hỏi thẩm quyền): 5 case
- ④ `4_high_stakes` (gán decision/deadline sai): 3 case
- ≥10 case dùng chatlog/transcript thật từ `data/vlearn-pack/`

### Quality bar — chốt từ 23:59 N1, giữ nguyên sau đó

**Đạt khi:**
1. **≥ 80% golden set pass toàn bộ** (class + scope + citation)
2. **100% no cross-scope leak** (bar tuyệt đối — không được vỡ ngay 1 case)
3. **100% case `1_no_source` chấp nhận "chưa đủ dữ liệu"** (không đoán/bịa)

Lý do 2+3 tuyệt đối: gán decision sai team hoặc leak cross-team = mất trust hoàn
toàn — ưu tiên không bao giờ vỡ hơn là trả nhiều. Chi tiết ở [eval/quality-bar.md](eval/quality-bar.md).

### Kết quả các lượt chạy

| Lượt | Timestamp | Case | Pass | No-leak | Verdict | Ghi chú |
|---|---|---|---|---|---|---|
| L1 | *(sẽ điền sau lượt chạy đầu)* | 22 | | | | |

Cách reproduce: `python eval/run_eval.py --endpoint http://localhost:8000/chat`.

## 16. Phân công có tên & willing users *(R7)*

### Phân công

| Lane | Deliverable có tên | Người (mã HV) | Vibe-coding check |
|---|---|---|---|
| PM + Frontend lead | `spec.md`, `canvas.md`, pitch narrative, orchestration frontend | **Nguyễn Hữu Tuyến** (2A202601520) | Giải thích được §10 impact table + §2 lát cắt pivot lý do |
| Agent Design (Backend + AI) | `backend/app/chat_service.py`, extraction prompt, guardrails (K03 câu đùa filter), `scopes.py` | **Thái Hoài An** (2A202601862) | Giải thích được cây quyết định phân class task/decision/deadline/noise + guard code chặn auto-write |
| Scraw dữ liệu + Eval | Apify adapter, scripts crawl Discord, `eval/golden_set.csv`, `eval/run_eval.py`, `quality-bar.md` | **Vũ Thành Khang** (2A202601866) + **Trịnh Bá Khánh Trình** (2A202601531) | Giải thích được cơ cấu golden set K03 FP + K05 cross-team + tại sao bar 100% no-auto-write |
| Frontend UI | `frontend/src/*` — chat shell, candidate card confirm/reject, sync view | **Nguyễn Văn Phúc** (2A202601350) | Giải thích được flow UI: chat → card đề xuất → ✓/✗ → sync → notify |

### Willing users (≥3 tên — đã có từ interview)

| # | Tên/vai | Mã HV | Cohort | Ngày đồng ý | Nguồn |
|---|---|---|---|---|---|
| 1 | **Nguyễn Văn Tuấn** | U01246 | K4 | 2026-07-30 | Interview 3 — "Mình thấy hợp lý" + xin feature 2-way sync |
| 2 | **Senior/Mentor** *(cần điền tên đầy đủ)* | *(mentor không có mã HV)* | K4 | 2026-07-30 | Interview 4 — "đáng thử" + warning về false positive |
| 3 | **Lợi** *(cần điền họ tên đầy đủ + mã HV)* | *(cần điền)* | K4 | 2026-07-31 | Interview 5 — "sẽ sử dụng" + "sẽ quay lại Discord" |
| *bonus* | Đào Hoàng Duy | U01780 | K4 | *(không cam kết)* | Interview 1 — user Trello, có thể là **contra-user** để test bot có kéo được không |
| *bonus* | Đức Minh | U01306 | K4 | *(lukewarm)* | Interview 2 — test cho segment "team nhỏ không cảm thấy cần" |

### Kế hoạch validation CP5

- 5 người × 10 phút/phiên tại `validation/user-test-log.md` — ưu tiên 3 willing users ở trên (Tuấn, Mentor, Lợi) + 2 người zone khác.
- **Task giao thật (không thuyết minh):**
  1. Team T004 mẫu chat 5 message (mix: 2 task rõ, 1 câu đùa, 1 task thiếu owner, 1 decision) → user xem bot đề xuất → confirm/reject.
  2. Chat 1 message "@Minh deploy trước tối mai" với Minh không thuộc team → user xem bot xử lý (kỳ vọng: warning, không auto-confirm).
  3. User bấm ✗ 1 candidate → xem đã ghi feedback chưa.
- **3 câu chuẩn:** khó hiểu nhất? tin không vì sao? có dùng thật không?
- **Metric quan sát:** user có bấm confirm khi bot đúng không? user có bực khi bot propose câu đùa không?
- Ai log: [tên phụ trách demo/validation]
