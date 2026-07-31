# Reflection — 2A202601862 · Thái Hoài An

## 1. Vai trò + phần mình làm cụ thể

- **Lane:** Agent Design — Backend + AI.

- **Deliverable có tên mình:**
  - [`codebase/backend/app/chat_service.py`](../codebase/backend/app/chat_service.py)
    — luồng chat chính, router hội thoại/guardrail, tạo memory candidate,
    human confirmation và tách chế độ evaluation khỏi state thật.
  - [`codebase/backend/app/scopes.py`](../codebase/backend/app/scopes.py) — tính
    `allowed_scope_keys`, kiểm tra quyền đọc channel và quyền ghi memory theo
    user/team/group/room/cohort.
  - [`codebase/backend/app/context_tools.py`](../codebase/backend/app/context_tools.py)
    và
    [`rag_anything_gateway.py`](../codebase/backend/app/rag_anything_gateway.py) —
    route câu hỏi sang đúng nguồn Discord/bài học và loại phản hồi
    `[no-context]` trước khi coi nó là câu trả lời có căn cứ.
  - [`codebase/backend/tests/test_evaluation.py`](../codebase/backend/tests/test_evaluation.py),
    `test_api.py` và `test_learning_context.py` — regression test cho state
    isolation, ambiguous/forbidden request, deadline quan trọng, cross-team scope
    và câu hỏi rộng từ Telegram.

- **Những việc mình trực tiếp chịu trách nhiệm:**
  - Từ ảnh lỗi Telegram, mình truy vết câu *“Mọi người học cái
    gì?”* qua webhook → `chat_service` → RAG. Provider trả về câu từ chối
    *“not able to provide… [no-context]”* nhưng vẫn kèm source, nên backend
    nhầm nó là grounded answer. Mình thêm `is_no_context_answer()` để reject
    abstention và cho phép fallback sang context tool. Đồng thời bổ sung các
    intent như `học gì`, `đang học gì`, `nội dung khóa học` vào
    `LESSON_TERMS`. Sau fix, câu hỏi rộng về Discord trả câu trả lời
    tiếng Việt có 3 citation, không còn `[no-context]`.
  - Mình debug lượt eval chỉ có **3/24 case pass**. Nguyên nhân không
    phải model yếu mà là một Google Calendar candidate đang chờ email bị lưu
    trong store; tất cả câu eval sau đó bị hiểu nhầm là email follow-up và
    trả *“Email này chưa hợp lệ”*. Mình sửa `chat(..., persist=False)`
    để eval không kế thừa pending flow và không ghi thêm state. Sau khi
    cô lập state, kết quả tăng lên 9/24; sau khi bổ sung guardrail và câu
    trả lời high-consequence có nguồn, bộ submission đạt **24/24**, 0
    critical failure mà không sửa case hay hạ quality bar 80%.
  - Mình giữ authorization ở backend thay vì tin vào channel do frontend gửi
    lên. `can_access_channel()` chặn đọc ngoài membership; `can_write_scope()`
    chặn user thường ghi vào group/cohort/room. Câu yêu cầu đọc team T009
    của user T004 bị từ chối trước retrieval và không có citation T009.
  - Mình giữ nguyên tắc **AI chỉ propose, user phải confirm trước khi
    write**. Với Google Tasks chưa có OAuth authorized-user, hệ thống ghi rõ
    `pitch-mock`, chỉ tạo bản nháp và không tuyên bố đã ghi task thật.

- **Chỗ mình chắc chắn giải thích được:**
  - Tại sao scope guard phải ở server và trước retrieval, không chỉ ẩn
    channel trên UI hoặc lọc citation sau khi model đã đọc dữ liệu.
  - Tại sao `[no-context]` là một **abstention**, không phải grounded answer,
    kể cả khi provider gửi kèm danh sách source.
  - Tại sao state cũng là input của model pipeline; test có cùng prompt vẫn
    có thể cho kết quả khác nếu còn pending candidate.
  - Tại sao deadline, secret và cross-team access cần deterministic guardrail;
    pass rate cao không thể bù cho một lần bịa deadline hoặc lộ dữ liệu.

## 2. AI hỗ trợ mình thế nào

- **Tool:** Codex trong workspace, ChatGPT và OpenRouter model pool của prototype.

- **Prompt/yêu cầu điển hình:**
  1. *“Telegram hiện đang không sử dụng được”* kèm ảnh chụp có
     `[no-context]`; mình yêu cầu AI truy vết endpoint và không chỉ sửa
     câu chữ hiển thị.
  2. *“Nạp context mock và tạo brief/task chỉ trong team T004, không làm
     ảnh hưởng context chung”*; yêu cầu này được chuyển thành scope
     guard và smoke test `preserved_non_team_message_count`.
  3. *“Chạy toàn bộ eval và không đổi quality bar”*; AI giúp so sánh
     baseline, trace case fail và sinh regression test cho từng nguyên nhân.

- **AI làm được nhanh:**
  - Lập bản đồ call path từ FastAPI/Telegram webhook tới context tool, RAG,
    LLM và citation; nhờ đó mình khoanh vùng lỗi nhanh hơn log thủ công.
  - Sinh khung unit test cho provider abstention, lesson intent, pending Calendar
    isolation và forbidden request.
  - Chạy đồng loạt test/eval, so sánh output và nhắc những chỗ tài liệu
    không khớp với production.

- **AI đề xuất chưa đủ an toàn, mình phải kiểm lại:**
  - Khi chuẩn hóa câu trả lời *“Daily trước 10h”*, việc hard-code để
    pass eval sẽ là gian lận nếu không có nguồn. Mình lần theo origin
    E019 tới `messages_clean.jsonl#bot-commands-751` và đối chiếu các bản
    ghi `bot-commands-316/332`: nộp sau 10h vẫn ghi nhận nhưng không có
    XP. Chỉ sau khi kiểm chứng mình mới giữ reply chuẩn hóa.
  - AI có thể coi **24/24** là đã hoàn thiện sản phẩm. Mình tách
    rõ: eval đạt nhưng user test mới 3/5 và Google Tasks vẫn là
    pitch-mock. Hai giới hạn này phải xuất hiện trong README, slide và UI.
  - Sau lần deploy đầu, AI báo production hoạt động nhưng landing page
    vẫn ghi *“Jira sandbox”* trong khi demo thật đang dùng Google Tasks
    pitch-mock. Mình kiểm tra HTML production, sửa toàn bộ solution copy,
    build và deploy lại thay vì chỉ tin vào HTTP 200.

## 3. Một bài học từ case fail của chính nhóm

**Case fail cụ thể — state Calendar làm nhiễm toàn bộ eval:**

Trong lần chạy full suite đầu tiên, hệ thống chỉ pass **3/24**. Log của
nhiều case không hề liên quan đều trả về *“Email này chưa hợp lệ”*. Trước
đó, một luồng Google Calendar đã tạo candidate và chờ người dùng cung cấp
email. `chat_service.chat()` đọc pending candidate này trước khi phân loại
query mới, nên case E002, E003… bị xem như câu trả lời cho flow cũ.

Mình đã không xóa store để “làm test xanh”, vì cách đó che giấu bug và
có thể xóa context demo thật. Thay vào đó, mình định nghĩa evaluation là
read-only: khi `persist=False`, service không nhận pending Calendar flow, không ghi
message/candidate và không gọi external write. Mình thêm test
`test_read_only_evaluation_ignores_pending_calendar_flow` để lỗi này không quay lại.

**Bài học:**

State ẩn cũng là một phần của input. Một golden set có prompt và expected
output rõ vẫn không reproducible nếu runner dùng chung state với phiên demo. Với
AI agent có memory và tool call, test isolation phải bao gồm **conversation state,
pending action và external side effect**, không chỉ cố định model/temperature.

Bài học thứ hai là pass rate chỉ có nghĩa khi môi trường chạy đúng. Từ
3/24 lên 9/24 là sửa **harness/state**; từ 9/24 lên 24/24 mới là sửa
**product behavior**. Gộp hai việc thành một con số sẽ khiến nhóm không biết
chất lượng model thật sự thay đổi ở đâu.

## 4. Nếu làm lại từ đầu, mình sẽ làm khác gì

1. **Tách reasoning khỏi side effect ngay từ interface đầu tiên.** Thay vì một
   `chat()` vừa retrieve, generate, ghi store và gọi connector, mình sẽ tách
   `plan_read_only()` và `commit_confirmed_action()`. Khi đó eval chỉ có thể gọi
   nhánh read-only, không cần dựa vào cờ runtime.
2. **Viết ba contract test ngay từ H0:** T004 không đọc T009; provider
   `[no-context]` phải fallback/abstain; pending action cũ không được nuốt query
   mới. Đây là ba boundary có cost-of-error cao nhất của backend.
3. **Dùng structured intent/result thay cho chuỗi tự do ở boundary.** RAG gateway
   nên trả `status = grounded | abstain | error` thay vì buộc backend nhận diện
   cụm `[no-context]`. Router cũng nên trả intent + confidence + required scope
   để log và test dễ hơn.
4. **Chạy eval trên fresh ephemeral store trong CI cho mỗi run**, sau đó chạy
   thêm một suite stateful riêng cho multi-turn. Như vậy test đơn lượt
   reproducible nhưng vẫn không bỏ sót lỗi hội thoại nhiều bước.
5. **Giải quyết OAuth Google Tasks sớm hơn.** Connector schema và luồng
   confirm đã có, nhưng không có authorized-user thì chỉ có thể demo
   pitch-mock. Mình sẽ xin OAuth owner ngay đầu hackathon hoặc chốt từ H0
   rằng deliverable chỉ là draft để tránh lệch kỳ vọng.

---

### Các con số mình có thể bảo vệ khi bị hỏi

- Backend test: **80 passed**.
- Eval baseline: **8/24 (33,3%)**, 4 critical failure.
- Lượt bị nhiễm state khi debug: **3/24**; sau isolation: **9/24**.
- Eval submission: **24/24 (100%)**, 0 critical failure; bar giữ nguyên 80%.
- Telegram smoke test sau fix: không còn `[no-context]`, có **3 citation**;
  webhook pending update = 0.
- Giới hạn còn lại: Google Tasks là **pitch-mock** cho đến khi có OAuth.
