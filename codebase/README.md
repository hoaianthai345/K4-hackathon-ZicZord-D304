# Kute Catch-up MVP

Discord Catch-up Copilot cho lớp K4:

- Bắt kịp các channel được phép đọc trong 24 giờ.
- Trả brief gồm quyết định, việc cần làm, deadline, blocker và citation.
- Tạo checklist hôm nay hoặc đánh dấu đã biết sau bản brief.
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
- `chat_interactions`: câu hỏi, câu trả lời, provider, citation và tool call.

Hệ thống không thu IP, user agent, mã sinh viên đầy đủ hoặc lịch sử chỉnh sửa.
Log chỉ được ghi khi chat từ một hồ sơ đã nhận diện; lỗi ghi log không làm mất
câu trả lời đang trả cho học viên.

Backend dùng OpenRouter pool theo luồng và giữ Groq làm fallback cuối.
Không đưa key thật vào source code, image Docker hoặc file được commit.

- Daily brief ưu tiên key `phuc`.
- Chat/context synthesis ưu tiên key `khang`.
- Embedding RAG ưu tiên key `trinh`.
- Mỗi luồng thử các key còn lại khi gặp 401, 402, 429 hoặc lỗi provider.
- Key lỗi quota được cooldown; `Retry-After` được tôn trọng khi có.

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
  --build-env NEXT_PUBLIC_API_URL=https://your-tunnel.trycloudflare.com
```

Quick Tunnel không có uptime guarantee và URL thay đổi khi process restart.
Máy local, Docker Desktop và `cloudflared` phải tiếp tục chạy. Với domain ổn
định, chuyển sang Cloudflare Named Tunnel. Trước khi public trang admin, đặt
`ADMIN_API_KEY` và nhập cùng key trong `/admin`.

## Kịch bản demo 2 phút

1. Mở `/chat` với user Thái Hoài An.
2. Bấm `Bắt kịp trong 24 giờ qua`.
3. Chỉ bốn loại thông tin: đã chốt, cần làm, deadline, blocker.
4. Mở citation về message Discord nguồn.
5. Bấm `Tạo checklist hôm nay` và đánh dấu một việc hoàn tất.
6. Chuyển sang Trần Mai Lan, team T009, để chứng minh T004 không xuất hiện.

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
