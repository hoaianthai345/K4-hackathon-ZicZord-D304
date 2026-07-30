# Kute Memory MVP

Discord Learning Copilot cho lớp K4:

- Đọc Discord snapshot từ Apify Dataset API.
- Giữ message nguồn với author, channel, time và permalink.
- Tính access theo user, team, group mentor, phòng học và cohort.
- Recall confirmed memory từ đúng scope.
- Trả summary có citation và cho user confirm memory mới.

Stack: Next.js 16, FastAPI, Hindsight 0.8.6 và Docker Compose.

## Chạy ngay

```bash
cp .env.example .env
docker compose up --build
```

- Landing kiêm pitch: <http://localhost:3000>
- Discord Copilot: <http://localhost:3000/chat>
- FastAPI docs: <http://localhost:8000/docs>

Mặc định app dùng Discord snapshot synthetic nên không cần API key.

Nếu có `OPENROUTER_API_KEY`, local demo dùng model miễn phí ổn định
`google/gemma-4-26b-a4b-it:free`. Có thể đổi sang
`qwen/qwen3.6-27b` khi tài khoản OpenRouter có credit.

## Kịch bản demo 2 phút

1. Mở `/chat` với user Thái Hoài An.
2. Gửi `Tóm tắt nội dung bài giảng ngày hôm qua`.
3. Mở citation `#Lec-D302`.
4. Gửi `Team mình đang chốt gì và còn blocker nào?`.
5. Chỉ panel context: `U01862`, `T004`, `G10`, `D302`, `D304`, `K4`.
6. Gửi `Team mình chốt demo scope memory trước 18h.` rồi confirm memory T004.
7. Chuyển sang Trần Mai Lan, team T009, để chứng minh T004 không xuất hiện.

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
cd backend
python3 -m pytest -q

cd ../frontend
npm run lint
npm run build
npm audit --omit=dev
```

Tài liệu:

- [Scope model](../architecture/discord-scope-model.md)
- [Hindsight integration](../architecture/hindsight-integration.md)
- [Product spec](../spec.md)
- [Kế hoạch 24 giờ](../PM-24H-PLAN.md)
