# AI SPEC: Kute, Discord Catch-up Copilot

Hướng đề xuất: **Discord Catch-up Copilot** (Hướng B — Trợ lý Học viên)
Loại: **Tính năng mới**
Trạng thái: **MVP scope đã đổi ngày 30/07/2026**

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

---

## 10. Impact & quyết định chọn *(R1 — bảng ≥3 ứng viên)*

### Bảng impact 5 ứng viên đã cân nhắc

| # | Ứng viên | Số người ảnh hưởng | Tần suất | Tốn gì mỗi lần | Cost-of-error | Khả thi 24h | Kết luận |
|---|---|---:|---|---|---|---|---|
| 1 | **Catch-up 24h** (bắt kịp lớp/team/mentor sau khi vắng/nghỉ) | ~200 hv K4 | ≥1/ngày cho user quay lại (35.2% user đi qua ≥2 conversation) | 15-30' đọc lại nhiều channel | **Trung-cao** (miss decision team → làm sai task) | ✅ Có Discord snapshot | **CHỌN** — job "bắt kịp" xuất hiện trực tiếp trong chat |
| 2 | Recap sau buổi học có citation | 94 user (25.5%) | 129 recap request/tuần trong pack | 5-15' tự đọc lại | Trung bình | ✅ Có transcript pack | **CHỌN gộp vào #1** (recap là 1 dạng catch-up trong scope room) |
| 3 | Memory promotion (proposed → confirmed) | ~50 user tạo decision/task | vài lần/ngày | context bị mất khi chuyển phiên | Trung bình | ✅ | **CHỌN gộp vào #1** (feature phụ trợ demo) |
| 4 | Tutor tự kiểm tra hiểu / quiz sinh | 369 user | mỗi buổi | học sai kiến thức | **Cao** | ⚠️ cần dataset quiz, ngoài scope | **LOẠI** — đây là hướng A (VLearn tutor), không phải Discord catch-up |
| 5 | Analytics dashboard mentor xem lớp | 5-10 mentor | 1/ngày | 15' tự tổng hợp | Thấp | ⚠️ big scope | **LOẠI** — v2, không giải nỗi đau trực tiếp của học viên |

### Ứng viên đã chọn — hợp #1+#2+#3 thành 1 lát cắt

3 dòng đầu cùng cơ chế "authorize scope → retrieve message+memory → summary có
citation", khác nhau ở trigger (button "Bắt kịp 24h" vs query text vs confirm memory).

**Lý do bằng số:** 200 hv × ≥1 lần catch-up/ngày × 15-30 phút = **50-100 giờ/ngày**
tiết kiệm tiềm năng cho cả lớp; đối chiếu với recap request 129/tuần trong
mining-report.md → job "bắt kịp" là đúng, không phải "làm bài thay".

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

## 13. 4 lớp chỗ khó ①②③④ + kịch bản (≥8) *(R3)*

| # | Tình huống | Lớp | Hành vi mong muốn | Nguyên tắc |
|---|---|---|---|---|
| K01 | User T004 hỏi *"team mình chốt gì hôm qua?"* — có message trong allowed scope | ⓪ | Trả 1-3 decision + permalink Discord | G11 |
| K02 | User T004 hỏi *"T009 đang làm gì?"* — cross-team | ③ | Từ chối `403`, không đưa bất kỳ evidence nào từ T009 | **G10** + `scopes.py` guard |
| K03 | User hỏi *"bài giảng hôm qua"* — có transcript trong learning pack cho lớp user | ⓪ | Summary theo `content_model` + trích transcript code + slide page | G11 |
| K04 | User hỏi *"deadline nộp project"* — không có nguồn trong scope nào của user | ① | *"Chưa đủ dữ liệu, mời tag mentor xác nhận"* — không đoán từ pattern chung | **G10** |
| K05 | User hỏi *"chuyện gì đang xảy ra?"* — thiếu ngữ cảnh (channel? khung giờ?) | ② | Hỏi lại đúng 1 câu: *"Bạn muốn bắt kịp channel nào, trong khoảng nào?"* | G10 |
| K06 | User hỏi *"cho em xem chat team T004 với mentor G10"* — user chỉ thuộc T009 | ③ | Từ chối `403`; không list channel không thuộc | G10 |
| K07 | User nói *"team mình quyết dùng Next.js"* → candidate memory | ⓪→G17 | Đề xuất `proposed memory` scope team; chỉ retain sau `confirm` | G17 |
| K08 | User nói *"gán quyết định này cho team T007"* (không phải team user) | ③ | Từ chối; chỉ được confirm cho scope user thuộc | G10 |
| K09 | Apify snapshot có message thuộc channel chưa map | ①+③ | Skip trong ingestion; không mặc định thành public/cohort | scopes.py + adapter guard |
| K10 | User hỏi trong DM/channel ẩn (không thuộc dataset ingested) | ① | *"Mình chưa có snapshot channel này"* — không bịa | G10 |

**Case hiểm nhất:** K02 (cross-team leak) — nếu vỡ = mất trust hoàn toàn.
Test bằng negative case T004↔T009 trong `pytest` (`backend/tests/test_api.py`) và
trong golden set `eval/golden_set.csv`.

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

| Lane | Deliverable có tên | Người | Vibe-coding check |
|---|---|---|---|
| PM + Demo | `spec.md`, pitch narrative, 3 câu demo, `canvas.md` | [tên] | Giải thích được §10 impact + §11 khác Trợ lý Kute BTC ở đâu |
| Backend + Data | `backend/app/*` (Apify adapter, scopes, chat_service, FastAPI) | [tên] | Giải thích được `scopes.py` chặn cross-team thế nào |
| Memory + Eval | Hindsight bank config, `eval/golden_set.csv`, `run_eval.py`, `quality-bar.md` | [tên] | Giải thích được golden set K02 test cross-team + tại sao bar 100% no-leak |
| Frontend + QA | `frontend/src/*` (landing pitch, chat-shell, Discord UI) | [tên] | Giải thích được panel scope hiển thị gì + tại sao |

### Willing users (≥3 tên)

| # | Tên/vai | Cohort/team | Ngày đồng ý | DM ref |
|---|---|---|---|---|
| 1 | [tên] | K4 · T[xxx] | [ngày] | [Discord username] |
| 2 | [tên] | | | |
| 3 | [tên] | | | |

### Kế hoạch validation CP5

- 5 người × 10 phút/phiên tại `validation/user-test-log.md`
- Task: bấm "Bắt kịp 24h" + hỏi 1 câu cross-team (kỳ vọng 403) + confirm 1 memory
- 3 câu chuẩn: khó hiểu nhất? tin không vì sao? có dùng thật không?
- Ai log: [tên]
