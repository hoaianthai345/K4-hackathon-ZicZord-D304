# Reflection — 2A202601350 · Nguyễn Văn Phúc

## 1. Vai trò + phần mình làm cụ thể

- **Lane:** Frontend UI
- **Deliverable có tên mình (`spec.md §16`):** `codebase/frontend/src/*` — chat
  shell, candidate card confirm/reject, sync view.
- **Các file/thành phần FE trong dự án (`codebase/frontend/src/`):**
  - `components/pitch-deck.tsx` — landing pitch / trang chủ.
  - `components/landing-page.tsx` — trang landing chính, có candidate card + sync view.
  - `components/chat-shell.tsx` — chat UI, candidate card confirm/reject, citation, checklist.
  - `components/admin-console.tsx` — quản lý context/memory, candidate/sync, xem retrieval trace.
  - `components/evaluation-dashboard.tsx` — hiển thị kết quả eval (golden set, quality bar).
  - `components/ziczord-avatar.tsx`, `components/logo.tsx`, `components/site-nav.tsx`,
    `components/theme-toggle.tsx` — UI phụ trợ (avatar bot, logo, nav, dark/light toggle).
  - `app/page.tsx`, `app/chat/page.tsx`, `app/admin/page.tsx`, `app/layout.tsx` — routing/layout.
  - `lib/api.ts`, `lib/types.ts` — gọi API backend + type dùng chung.
- **Việc cụ thể đã làm:**
  - Fix `Module not found: Can't resolve 'react-markdown'` khiến trang chủ trả
    lỗi 500 khi chạy `npm run dev` — `node_modules` thiếu `react-markdown` và
    các dependency phụ (`unist-util-visit`, `unist-util-is`) dù đã khai báo
    trong `package.json`. Fix bằng `npm install` lại toàn bộ.
  - Fix lỗi dấu tiếng Việt bị dính trong tiêu đề "Memory Architecture" (`Tin
    nhắn là bằng chứng. Memory là điều đã được chốt.`) — `.section-title`
    trong `globals.css` dùng `letter-spacing: -0.065em` quá mạnh trên
    font-size lớn, khiến dấu ghép (ăng, ằng, ứng...) đè lên ký tự kế tiếp.
    Giảm còn `-0.02em`, giữ nguyên font-size/line-height/font-weight.
  - Chạy dev server frontend độc lập (`npm run dev`) để sửa riêng trang chủ —
    landing không gọi API, chỉ `/chat` và `/admin` mới cần backend chạy song song.
- **Chỗ mình chắc chắn giải thích được:**
  - Flow UI: chat → card đề xuất → ✓/✗ → sync → notify (vibe-coding check theo `spec.md §16`).
  - Vì sao trang chủ 500 (thiếu dependency) và vì sao title bị dính dấu (letter-spacing âm quá mạnh trên font có dấu ghép tiếng Việt).

## 2. AI hỗ trợ mình thế nào

- **Tool:** Claude Code
- **Prompt điển hình:** hỏi cách chạy riêng frontend, báo lỗi console/log thực
  tế và nhờ tìm nguyên nhân thay vì đoán.
- **AI làm được ngay:** đọc log lỗi Next.js, tra ra đúng dòng CSS gây lỗi
  (`letter-spacing` ở `.section-title`) và gói thiếu (`react-markdown`) mà
  không cần tự dò từng file.
- **AI sinh sai, mình sửa:** [điền nếu có — case cụ thể AI đề xuất sai và mình
  tự sửa lại]

## 3. Một bài học từ case fail của chính nhóm

**Case fail cụ thể:**
- Eval baseline ngày 31/07/2026 09:44 chỉ đạt **8/24 (33,3%)** với **4 critical
  fail** (xem `spec.md §9` + `§15`). Nguyên nhân: state của eval không cô lập —
  case read-only bị "làm bẩn" bởi pending Calendar sync còn treo, và guardrail
  (lọc câu đùa K03, chặn cross-team K05) chạy **sau** retrieval thay vì trước,
  nên vài case lẽ ra phải bị chặn lại lọt qua thành kết quả sai.
- Về phía FE, hệ quả trực tiếp là màn hình candidate card/sync view có thể
  hiển thị một trạng thái "đã sync" trong khi backend thực chất đang ở trạng
  thái pending chưa xác nhận — nếu không có ai bắt ra bằng eval, UI vẫn hiển
  thị bình thường mà không tự phát hiện được sai lệch đó.

**Bài học:**
- Guardrail/access-control phải chạy **trước** retrieval, không phải hậu kiểm
  sau khi đã lấy dữ liệu — post-filter dễ bị bỏ sót khi thêm code path mới.
- FE không nên chỉ tin y nguyên field trạng thái (`pending`/`confirmed`,
  `synced`) do backend trả về mà không có cách nào đối chiếu — cần eval/test
  từ đầu-đến-cuối (không chỉ test riêng backend) để bắt được lỗi kiểu "UI hiển
  thị đúng field nhưng field đó sai từ gốc".

## 4. Nếu làm lại từ đầu, mình sẽ làm khác gì

- Kiểm tra `npm install`/dependency ngay từ đầu setup máy mới thay vì để tới
  lúc chạy `npm run dev` mới phát hiện thiếu gói (`react-markdown` và các gói
  phụ) — nên có bước "chạy thử toàn bộ app trên máy sạch" sớm hơn trong tuần,
  không để tới gần deadline.
- Với các thuộc tính CSS ảnh hưởng trực tiếp tới việc đọc được tiếng Việt
  (`letter-spacing`, `line-height`), test riêng với câu tiếng Việt có dấu ghép
  (ăng, ằng, ứng, ẵng...) ngay khi style, thay vì chỉ nhìn preview bằng chữ
  tiếng Anh rồi mới phát hiện lỗi lúc demo.
- Phối hợp sớm hơn với bên Backend/Eval để biết trạng thái nào (pending/
  confirmed/synced) là "sự thật" cần hiển thị đúng, tránh việc FE hiển thị một
  trạng thái nhìn "đẹp" nhưng không phản ánh đúng dữ liệu thật — đúng bài học
  từ case eval baseline 8/24 ở mục 3.

*(Ghi chú: mục 3–4 được dựng dựa trên số liệu và bối cảnh thật đã có sẵn trong
`spec.md` — Phúc nên đọc lại và chỉnh câu chữ cho đúng giọng/trải nghiệm cá
nhân của mình trước khi nộp, vì đây là phần phản ánh cá nhân.)*
