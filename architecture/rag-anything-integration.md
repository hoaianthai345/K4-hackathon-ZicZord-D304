# PostgreSQL và RAG-Anything

## Vai trò của từng lớp

PostgreSQL là source of truth dẫn xuất cho dataset Discord và bài học. Ba bảng
`discord_messages`, `issue_episodes`, `painpoint_summary` giữ record Discord;
`learning_context` giữ transcript, slide và tutor Q&A. Tất cả đều có scope,
provenance và cờ `is_enabled` để audit/quản trị. `content_original` được giữ cục
bộ; `content_model` đã redact là field duy nhất có thể đi vào model.

RAG-Anything là retrieval engine. Image Docker clone repo chính thức HKUDS và
checkout commit `65b7ffdeb801309d4c87b6accf81bfe5cd9b175d`. Vì Discord export đã
được pipeline parse thành text/episode/painpoint, integration dùng
`insert_content_list()` thay cho MinerU.

FastAPI là authorization boundary. User không được truyền scope vào RAG service.
Backend lấy membership trong scope model, tính allow-list ở server, rồi mới gọi
RAG-Anything. Source endpoint cũng kiểm tra lại scope trước khi đọc PostgreSQL.

## Data flow

```text
Excel raw (read-only)
  -> non-destructive pipeline
  -> messages_clean / issue_episodes / painpoint_summary
       -> PostgreSQL: toàn bộ record + provenance
       -> RAG-Anything: hot index từ content_model đã redact
            -> LightRAG vector + knowledge graph trên volume riêng

User -> FastAPI -> server-computed scope allow-list -> RAG-Anything
     <- answer + source IDs
     -> PostgreSQL source endpoint -> redacted evidence

Transcript / slide / tutor Q&A (read-only)
  -> learning loader
  -> PostgreSQL learning_context
  -> local FTS + trigram search
  -> top redacted excerpts only -> answer LLM
```

Pack bài học không được bulk-embed ra provider ngoài. Dữ liệu đã có
text/provenance rõ, kích thước phù hợp để search local và rule của data pack yêu
cầu chỉ gửi phần tối thiểu cần thiết tới AI ngoài.

## Quyền truy cập

Scope key có dạng `user:U01862`, `team:T004`, `group:G10`,
`room:LEC-D302`, `room:LAB-D304`, `cohort:K4`. Dataset hiện tại là các channel
chung nên được index vào `cohort:K4`. Khi crawl có `channel_id`, roles và mapping
đầy đủ, loader sẽ gắn message vào team/group/room tương ứng và index từng working
directory độc lập.

## Index budget

Database không cắt dữ liệu: giữ 6.373 messages, 1.701 episodes và 1.283
painpoints từ batch hiện tại. RAG hot index là cấu hình vận hành cho demo 24 giờ:
ưu tiên painpoint có nhiều episode/reporter, episode có confidence cao và message
có reaction/attachment. Các biến `RAG_MAX_*` cho phép tăng ngân sách sau
hackathon mà không đổi schema.

Index manifest lưu digest của content. Chạy lại cùng input sẽ skip; thay input
sẽ tạo document ID mới. Volume `rag-anything-data` giữ vector, graph và LLM cache.

## Tool routing theo channel và thời gian

FastAPI lập plan deterministic trước khi gọi model:

1. Nhận diện lesson intent, alias channel, `day_code` và time expression.
2. Tính allowed scope từ membership; client không được truyền scope.
3. Chọn tool:
   - `get_current_datetime` để neo “hôm nay/hôm qua” theo giờ Việt Nam.
   - `search_learning_context` cho bài học, transcript, slide và khái niệm.
   - `search_discord_messages` cho channel/time cụ thể.
   - `inspect_context_date_range` để đối chiếu ngày hỏi với timestamp thực tế
     của context đã lấy.
   - `rag_anything_hybrid_search` cho semantic issue/pain point không có bộ lọc
     strict.
   - `recall_confirmed_memory` chỉ trên allowed scope.
4. Gửi top context đã redact vào LLM và chỉ hiển thị citation marker model dùng.

Các cụm “team mình”, “nhóm mình”, “mentor”, “kênh hỏi đáp”, “kênh chung”,
“lý thuyết” và “lab” được map sang channel nội bộ dựa trên membership của user.
`hôm nay`, `hôm qua`, `N giờ qua`, `N ngày qua` được hiểu trong timezone
`Asia/Ho_Chi_Minh` rồi đổi sang UTC để query.

Channel/time là hard constraint. Nếu exact query không có row, hệ thống không
fallback sang RAG của channel khác. Đây là guard chống citation đúng semantic
nhưng sai nơi hoặc sai thời điểm.

## Model provider

- Embedding: OpenRouter,
  `nvidia/nemotron-3-embed-1b:free`, vector 2.048 chiều.
- Query LLM: Groq, `qwen/qwen3.6-27b`.
- Qwen reasoning được đặt `reasoning_effort=none` cho retrieval query. RAG cần
  câu trả lời ngắn, grounded và đủ chỗ cho citation; không cần chain-of-thought
  dài trong completion.
- Chỉ `content_model` đã redact được gửi tới hai provider.

## API

- `POST /api/rag/query`: truy vấn RAG bằng scope do server tính.
- `GET /api/rag/sources/{source_type}/{source_id}`: evidence đã redact, có guard.
- `GET /health`: số row PostgreSQL, trạng thái RAG và các scope đã index.
- `POST /api/chat`: ưu tiên RAG khi có source; fallback flow hiện tại nếu RAG
  chưa sẵn sàng.
- `GET /api/admin/context`: lọc và xem context đã dẫn xuất.
- `PATCH /api/admin/context/{source_type}/{source_id}`: bật/tắt record mà không
  xóa dữ liệu.
- `POST /api/admin/context/plan`: xem tool calls, filter và source preview.
- `GET|POST|PATCH|DELETE /api/admin/memories`: quản lý confirmed memory.
