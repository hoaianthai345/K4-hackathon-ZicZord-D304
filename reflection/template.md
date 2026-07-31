# Reflection — [Mã HV] · [Tên đầy đủ]

## 1. Vai trò + phần mình làm cụ thể

- **Lane:** [PM+Demo / Backend+Data / Memory+Eval / Frontend+QA]
- **Deliverable có tên mình:**
  - [ví dụ] `backend/app/scopes.py` — access rule tính allowed scopes từ membership
  - [ví dụ] `eval/golden_set.csv` case G08-G12 (cross-team K02)
- **Đã tự tay làm** (không chỉ copy AI):
  - [ví dụ] Debug tại sao Hindsight bank `kute-team-t009` xuất hiện trong recall của user T004 → fix ở `scopes.py:allowed_banks`
- **Chỗ mình chắc chắn giải thích được:**
  - [ví dụ] Tại sao bank-per-scope thay vì tag filter → giải thích cross-team leak risk

## 2. AI hỗ trợ mình thế nào

- **Tool:** [ChatGPT / Claude / Cursor / Copilot / …]
- **Prompt điển hình:** [1-2 prompt thực]
- **AI làm được ngay:** [ví dụ] boilerplate Pydantic model
- **AI sinh sai, mình sửa:**
  - [ví dụ] AI đề xuất filter tags trên 1 bank chung → không đảm bảo isolation → mình đổi sang bank-per-scope

## 3. Một bài học từ case fail của chính nhóm

**Case fail cụ thể:**
- [ví dụ] Lượt eval đầu, case G08 T004→T009 leak 1 evidence vì `chat_service.py` gọi Hindsight recall trước khi filter bank. Fix: đổi thứ tự — filter allowed banks trước, recall sau.

**Bài học:**
- [ví dụ] Guard authorization phải ở **boundary sớm nhất** (trước khi retrieval chạy), không phải post-filter — post-filter dễ bị bypass khi thêm code path mới.

## 4. Nếu làm lại từ đầu, mình sẽ làm khác gì

- [ví dụ] Viết test cross-team NGAY từ H0 thay vì H17 — sẽ phát hiện leak sớm hơn 15h
- [ví dụ] Dùng type để chặn cross-scope thay vì runtime check
