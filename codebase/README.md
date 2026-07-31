# ZicZord Catch-up MVP

Discord Catch-up Copilot cho lớp K4:

- Bắt kịp các channel được phép đọc trong 24 giờ.
- Trả brief gồm quyết định, việc cần làm, deadline, blocker và citation.
- Tạo checklist hôm nay hoặc đánh dấu đã biết sau bản brief.
- Đề xuất task từ hội thoại và thêm vào Google Calendar sau một lần xác nhận.
- Giữ scope authorization và confirmed memory làm hạ tầng phía dưới.
- Chuẩn hóa Discord export mà không sửa/xóa dữ liệu gốc.

Stack: Next.js 16, FastAPI, PostgreSQL 16, HKUDS/RAG-Anything,
Hindsight 0.8.6 và Docker Compose.

## Chạy ngay

```bash
cp .env.example .env
docker compose up --build
```

- Landing kiêm pitch: <http://localhost:3000>
- Discord Copilot: <http://localhost:3000/chat>
- Evaluation, context & memory admin: <http://localhost:3000/admin>
- FastAPI docs: <http://localhost:8000/docs>

Landing và chat vẫn dùng UI hiện tại. Khi chưa index, chat tự fallback về Discord
snapshot synthetic.

## Hồ sơ học viên và log hỏi đáp

Trang `/chat` hỏi họ tên và 5 số cuối mã sinh viên trong lần truy cập đầu tiên.
Frontend chỉ giữ `profile_id` trong `localStorage`; lần sau dùng ID này để khôi
phục hồ sơ và vào thẳng chat. Nếu học viên nhập lại cùng 5 số cuối, backend cập
nhật hồ sơ hiện có thay vì tạo bản trùng.

PostgreSQL lưu hai bảng tối giản:

- `learner_profiles`: họ tên, 5 số cuối, demo user mapping và thời điểm gần nhất.
- `chat_interactions`: nguồn web/Telegram, câu hỏi, câu trả lời, provider,
  citation và tool call.

Hệ thống không thu IP, user agent, mã sinh viên đầy đủ hoặc lịch sử chỉnh sửa.
Log chỉ được ghi khi chat từ một hồ sơ đã nhận diện; lỗi ghi log không làm mất
câu trả lời đang trả cho học viên.

## Telegram bot

Bot `@ZicZordAI20K4Bot` dùng cùng `ChatService`, context tools, RAG và scope gate
với web. Bot chỉ trả lời trong private chat; group chat bị từ chối để tránh lộ
context cá nhân/team. Mỗi câu hỏi hợp lệ được lưu vào `chat_interactions` với
`source=telegram` và Telegram user ID, không lưu username hay số điện thoại.

Đặt trong `.env`:

```dotenv
TELEGRAM_BOT_TOKEN=
TELEGRAM_WEBHOOK_SECRET=
TELEGRAM_PUBLIC_USER_ID=U01862
NEXT_PUBLIC_TELEGRAM_BOT_URL=https://t.me/ZicZordAI20K4Bot
```

`TELEGRAM_PUBLIC_USER_ID` bật demo công khai với scope của một demo user. Khi
triển khai thật, để trống biến này và tạo `config/telegram-users.json` từ file
example để map Telegram ID sang đúng học viên.

Sau khi backend có public HTTPS URL:

```bash
python3 scripts/setup-telegram-webhook.py \
  --url https://your-backend.example.com \
  --env-file .env
```

Backend dùng OpenRouter pool theo luồng và giữ Groq làm fallback cuối.
Không đưa key thật vào source code, image Docker hoặc file được commit.

- Daily brief ưu tiên key `phuc`.
- Chat/context synthesis ưu tiên key `khang`.
- Embedding RAG ưu tiên key `trinh`.
- Mỗi luồng thử các key còn lại khi gặp 401, 402, 429 hoặc lỗi provider.
- Key lỗi quota được cooldown; `Retry-After` được tôn trọng khi có.

## Web search với Tavily

Web search chạy khi người dùng nói rõ ý định như `tìm trên web`,
`tra cứu Internet`, `nguồn web`, `latest news`, hoặc hỏi tự nhiên về kiến thức
công khai theo dạng `X là ai?`, `X là gì?`, `biết X không?`. Câu hỏi có dấu hiệu
team, mentor, bài học, deadline, blocker hoặc channel vẫn dùng các nguồn nội bộ
đã được cấp quyền.

Backend chỉ gửi chính câu hỏi hiện tại sang Tavily, không gửi Discord context,
confirmed memory hay danh tính học viên. Kết quả trả về có citation theo domain
và mở trực tiếp trang nguồn.

Đặt key thật trong `.env` đã được Git ignore:

```dotenv
TAVILY_API_KEY=
TAVILY_API_BASE_URL=https://api.tavily.com
TAVILY_SEARCH_DEPTH=basic
TAVILY_MAX_RESULTS=5
```

Ví dụ:

```text
Tìm trên web tài liệu chính thức về Tavily Search API
```

## Google Calendar action tool

Agent nhận câu tự nhiên như:

```text
Người dùng: Nhắc tôi hoàn thiện slide lúc 20h ngày mai
Agent: Email Google dùng cho Calendar của bạn là gì?
Người dùng: ban@example.com
```

Lượt đầu chỉ tạo draft. Email ở lượt hai là xác nhận rõ ràng để backend thêm
`attendees[].email` và gọi `events.insert?sendUpdates=all`. Google gửi invitation
tới người nhận; task đồng thời trở thành confirmed memory. Event ID được suy ra
từ candidate ID nên request retry không tạo sự kiện trùng.

Email được che trong chat history, PostgreSQL interaction log và Hindsight.
Địa chỉ được truyền thẳng trong bộ nhớ tới connector và không được ghi vào
candidate/calendar state, kể cả khi gửi thành công hoặc gặp lỗi.

### Gmail cá nhân làm organizer

1. Bật Google Calendar API, cấu hình OAuth consent screen dạng External và thêm
   Gmail organizer vào Test users.
2. Tạo OAuth Client ID loại **Desktop app**, tải JSON về
   `config/google-calendar-oauth-client.json`.
3. Điền `.env`:

```dotenv
GOOGLE_CALENDAR_AUTH_MODE=oauth
GOOGLE_CALENDAR_ID=primary
GOOGLE_CALENDAR_OAUTH_CLIENT_FILE=/app/config/google-calendar-oauth-client.json
GOOGLE_CALENDAR_OAUTH_TOKEN_FILE=/app/state/google-calendar-oauth-token.json
GOOGLE_CALENDAR_ORGANIZER_EMAIL=your-account@gmail.com
GOOGLE_CALENDAR_OAUTH_PORT=8765
GOOGLE_CALENDAR_TIMEZONE=Asia/Ho_Chi_Minh
GOOGLE_CALENDAR_DEFAULT_DURATION_MINUTES=60
```

4. Build backend rồi chạy flow kết nối một lần:

```bash
docker compose up -d --build backend
docker compose exec backend python -m app.google_calendar_oauth_setup
```

Mở URL được in ra, đăng nhập đúng Gmail organizer và chấp nhận scope
`calendar.events`. Refresh token được lưu trong volume `/app/state`, không nằm
trong frontend hoặc Git. `primary` là lịch chính của Gmail đã kết nối.

### Google Workspace service account

Đặt `GOOGLE_CALENDAR_AUTH_MODE=service-account`, lưu key tại
`config/google-service-account.json`, cấp scope
`https://www.googleapis.com/auth/calendar.events` bằng Domain-wide Delegation,
và cấu hình `GOOGLE_CALENDAR_DELEGATED_USER` là organizer trong Workspace.
Service account không có delegation sẽ bị chặn trước khi gửi attendee invitation.
Không commit bất kỳ JSON credential hoặc token nào.

## Pitch flow T004 → Google Tasks

Trang `/chat` có nút **Nạp context & tạo brief** cho thành viên T004. Luồng này:

1. Upsert 7 message pitch có ID cố định vào riêng channel `team-t004`.
2. Tạo brief với `scope=team`; mọi citation trong brief phải là `#t-004`.
3. Cho người dùng xác nhận từng task/blocker trước khi gọi Google Tasks.
4. Chặn user ngoài T004 và chặn brief dùng scope khác `team:T004`.

Loader không xóa hoặc sửa message ở `general`, cohort, group mentor, lecture, lab
hay team khác. Bấm lại không tạo message hoặc task trùng.

Mặc định `.env.example` dùng chế độ không phụ thuộc mạng:

```dotenv
GOOGLE_TASKS_MODE=mock
GOOGLE_TASKS_TASKLIST_ID=@default
```

UI sẽ ghi rõ `pitch-mock (chưa ghi ra tài khoản Google)`. Để tạo Google Task
thật, bật Google Tasks API, thực hiện OAuth consent cho đúng tài khoản với scope
`https://www.googleapis.com/auth/tasks`, rồi dùng một trong hai cách:

```dotenv
# Cách ổn định cho pitch: authorized-user JSON có refresh_token.
GOOGLE_TASKS_MODE=live
GOOGLE_TASKS_TASKLIST_ID=@default
GOOGLE_TASKS_CREDENTIALS_FILE=/app/config/google-tasks-oauth.json

# Hoặc access token ngắn hạn.
GOOGLE_TASKS_ACCESS_TOKEN=
```

File `config/google-tasks-oauth.json` đã được Git ignore và chỉ được mount
read-only vào backend. Google Tasks lưu deadline theo ngày; giờ gốc vẫn được giữ
trong phần notes cùng owner, scope và permalink Discord.

Có thể kiểm tra lớp cô lập mà không mở UI:

```bash
curl -X POST "http://localhost:8000/api/pitch/t004/context?user_id=U01862"

curl -X POST \
  "http://localhost:8000/api/pitch/t004/brief?user_id=U01862"
```

## Vercel frontend + Docker backend trên máy local

Backend có thể public tạm thời qua Cloudflare Quick Tunnel:

```bash
cloudflared tunnel --no-autoupdate --url http://localhost:8000
```

Lấy URL `https://...trycloudflare.com` từ output, sau đó khởi động lại backend
với citation URL và CORS của frontend:

```bash
FRONTEND_ORIGIN="http://localhost:3000,https://your-project.vercel.app" \
API_PUBLIC_URL="https://your-tunnel.trycloudflare.com" \
docker compose up -d --build backend
```

Deploy frontend:

```bash
cd frontend
vercel link --yes --project kute-discord-copilot
vercel --prod --yes \
  --build-env NEXT_PUBLIC_API_URL=https://your-tunnel.trycloudflare.com \
  --build-env NEXT_PUBLIC_TELEGRAM_BOT_URL=https://t.me/ZicZordAI20K4Bot
```

Quick Tunnel không có uptime guarantee và URL thay đổi khi process restart.
Máy local, Docker Desktop và `cloudflared` phải tiếp tục chạy. Với domain ổn
định, chuyển sang Cloudflare Named Tunnel. Trước khi public trang admin, đặt
`ADMIN_API_KEY` và nhập cùng key trong `/admin`.

## Kịch bản demo 2 phút

1. Mở `/chat` với user Thái Hoài An, team T004.
2. Bấm **Nạp context & tạo brief** trong Pitch mode.
3. Chỉ ra badge `team:T004 only` và mở một citation về đúng `#t-004`.
4. Bấm **Xác nhận & tạo Google Task** ở một việc cần làm.
5. Chỉ rõ kết quả là `Google Tasks thật` hoặc `pitch-mock`, không nhập nhằng.
6. Chuyển sang Trần Mai Lan, team T009: Pitch mode biến mất và API trả `403`.

## Xử lý dataset local

```bash
python3 -m pip install -r data_pipeline/requirements.txt
python3 -m data_pipeline.process_discord_exports \
  --input "/absolute/path/to/Dataset" \
  --output data/processed
```

Pipeline sinh `messages_clean`, `issue_episodes` và `painpoint_summary`. Output bị
Git ignore vì vẫn giữ content gốc; xem [hướng dẫn pipeline](data_pipeline/README.md)
và [report aggregate](../evidence/dataset-processing-report.md).

## PostgreSQL và RAG-Anything

RAG service dùng repo chính thức
[HKUDS/RAG-Anything](https://github.com/HKUDS/RAG-Anything), pin commit
`65b7ffdeb801309d4c87b6accf81bfe5cd9b175d` (release code `1.3.1`).
Discord JSONL đã được parse nên service dùng direct content insertion, không cần
MinerU.

```bash
# Khởi động database, RAG service, FastAPI và UI.
docker compose up -d --build

# Nạp toàn bộ messages/episodes/painpoints vào PostgreSQL.
docker compose --profile index run --rm dataset-loader

# Tạo hot index LightRAG từ content_model đã redact.
docker compose --profile index run --rm rag-indexer
```

Loader và indexer đều idempotent. PostgreSQL giữ toàn bộ record chuẩn hóa để
audit/citation. Hot index mặc định ưu tiên 8 message, 12 episode và 24 painpoint
có tín hiệu mạnh để vừa ngân sách hackathon; có thể tăng bằng
`RAG_MAX_MESSAGES`, `RAG_MAX_EPISODES`, `RAG_MAX_PAINPOINTS`.

RAG dùng OpenRouter cho embedding
`nvidia/nemotron-3-embed-1b:free` và có thể dùng Groq riêng cho phần sinh đáp án
với `qwen/qwen3.6-27b`. Adapter tắt reasoning của Qwen cho query RAG để tránh
reasoning token chiếm completion budget và làm câu trả lời/citation bị cắt.

Kiểm tra:

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/api/rag/query \
  -H 'Content-Type: application/json' \
  -d '{"user_id":"U01862","query":"Vì sao không nhận được GitHub Organization invite?"}'
```

FastAPI tự tính scope từ membership. Client chỉ gửi `user_id` và câu hỏi, không
được tự cấp `scope_keys`. Citation trả về endpoint
`/api/rag/sources/{type}/{id}`; endpoint này kiểm tra scope lần nữa và chỉ trả
text đã redact, không trả `content_original`.

## Nạp context bài học

Pack bài học được mount read-only từ `../data/vlearn-pack`; loader không sửa
transcript, slide PDF hoặc chatlog gốc.

```bash
docker compose --profile index run --rm learning-loader
```

Kết quả hiện tại là 2.019 context:

- 700 đoạn transcript có citation code.
- 58 trang slide.
- 1.261 cặp hỏi đáp học viên/tutor.

Toàn bộ context được giữ trong bảng `learning_context`. `content_original` chỉ
để audit cục bộ; `content_model` đã redact email, số điện thoại và chuỗi giống
API key. Search bài học chạy local bằng PostgreSQL FTS/trigram, không gửi cả
pack sang embedding bên ngoài. Chỉ các excerpt đứng đầu mới đi vào LLM để tổng
hợp câu trả lời.

## Context tool routing

Backend lập retrieval plan trước khi gọi model:

| Câu hỏi | Tool chính | Ràng buộc |
|---|---|---|
| “Hôm nay/hôm qua” | `get_current_datetime` | ngày hiện tại theo Asia/Ho_Chi_Minh |
| Khái niệm/bài giảng/slide | `search_learning_context` | `day_code`, loại nguồn |
| “Kênh hỏi đáp hôm qua” | `search_discord_messages` | channel + mốc giờ UTC đổi từ Asia/Ho_Chi_Minh |
| Đối chiếu ngày nguồn | `inspect_context_date_range` | ngày được hỏi + timestamp đầu/cuối của context |
| “Team/nhóm mình” | `search_discord_messages` | đúng channel của team từ membership |
| Lỗi/pain point lặp lại không chỉ rõ thời gian | `rag_anything_hybrid_search` | scope allow-list do server tính |
| Memory đã xác nhận | `recall_confirmed_memory` | user/team/group/room/cohort được phép |

Query có channel hoặc time window là strict: nếu không có kết quả, backend
không tự mở rộng sang channel khác bằng semantic RAG. Retrieval trace có thể
kiểm tra tại tab **Tool inspector** của `/admin`.

Answer LLM nhận time facts riêng, nhưng UI không hiển thị tên section/tool hoặc
quá trình suy luận. Nội dung bot được render bằng Markdown an toàn; raw HTML bị
bỏ và link mở ở tab mới.

Trang admin còn hỗ trợ:

- Evaluation dashboard trả lời đủ AI decision, model, số câu thử, bốn nhóm rủi
  ro, số câu từ quan sát thật, baseline và chuẩn đạt đã khóa.
- Chạy lại 24 eval case mà không ghi chúng vào chat history hoặc memory.
- Tìm và bật/tắt lesson, Discord message, issue episode và pain point.
- Tạo, sửa, xóa confirmed memory theo scope.
- Re-index Discord RAG theo digest idempotent.

Bộ thử nằm ở `../eval/`. Baseline đầu tiên đạt `8/24` câu, thấp hơn chuẩn khóa
`80%`; các lỗi deadline critical cũng chưa đạt zero-tolerance rule. Xem toàn bộ
câu pass/fail trong `../eval/results/baseline.json`.

Production nên đặt `ADMIN_API_KEY`; UI giữ key trong `sessionStorage` và gửi qua
`X-Admin-Key`. Khi biến này trống, admin được mở để demo local.

## Nối Apify

Đặt trong `.env`:

```dotenv
APIFY_TOKEN=apify_api_...
APIFY_DATASET_ID=your_dataset_id
```

Gọi:

```bash
curl -X POST http://localhost:8000/api/ingest/apify \
  -H 'Content-Type: application/json' \
  -d '{"max_items":250}'
```

Adapter chấp nhận một số tên field thường gặp như `messageId`, `channelId`, `author.id`, `content`, `timestamp` và `url`. Channel phải được map trong `app/seed.py`; channel lạ bị skip.

Chỉ ingest server và channel đã được chủ server cho phép. Không dùng Discord user token hoặc self-bot.

## Chạy với Hindsight

```dotenv
MEMORY_PROVIDER=hindsight
HINDSIGHT_API_LLM_PROVIDER=gemini
HINDSIGHT_API_LLM_API_KEY=
```

```bash
docker compose --profile hindsight up --build
```

Hindsight UI: <http://localhost:9999>

Bank ID:

```text
kute-user-u01862
kute-team-t004
kute-group-g10
kute-room-lec-d302
kute-cohort-k4
```

Recall dùng strict tags và chỉ chạy trên bank server tính từ membership.

## Phát triển và kiểm tra

```bash
docker compose run --rm -v "$PWD/backend:/app" backend pytest -q

python3 -m pytest data_pipeline/test_process_discord_exports.py -q

cd frontend
npm run lint
npm run build
npm audit --omit=dev
```

Tài liệu:

- [Scope model](../architecture/discord-scope-model.md)
- [Hindsight integration](../architecture/hindsight-integration.md)
- [PostgreSQL và RAG-Anything](../architecture/rag-anything-integration.md)
- [Product spec](../spec.md)
- [Kế hoạch 24 giờ](../PM-24H-PLAN.md)
