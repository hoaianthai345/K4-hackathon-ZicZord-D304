# Nhóm ZicZord · Zone [X] · Lớp D304 · Khoá 4 — Kute, Discord Catch-up Copilot

Hướng: **B — Trợ lý Học viên (Discord)** · Loại: **Tính năng mới**

**Lát cắt MỘT CÂU:** học viên hỏi Trợ lý Kute trong `#🤖-gõ-commands` → hệ thống
tính scope được phép từ membership (user/team/group/room/cohort) + truy xuất
message & memory liên quan → trả summary có permalink nguồn, hoặc từ chối `403`
khi cross-scope, hoặc *"chưa đủ dữ liệu"* khi không có evidence.

## Thành viên & phân công

| # | Mã HV | Tên đầy đủ | Lane | Deliverable có tên |
|---|---|---|---|---|
| 1 | [U____] | [Tên 1] | PM + Demo | [spec.md](spec.md), [canvas.md](canvas.md), demo-slides.pdf, pitch narrative |
| 2 | [U____] | [Tên 2] | Backend + Data | [codebase/backend/app/](codebase/backend/app/) — Apify adapter, scopes, chat_service, FastAPI |
| 3 | [U____] | [Tên 3] | Memory + Eval | Hindsight bank config, [eval/golden_set.csv](eval/golden_set.csv), [eval/run_eval.py](eval/run_eval.py), [eval/quality-bar.md](eval/quality-bar.md) |
| 4 | [U____] | [Tên 4] | Frontend + QA | [codebase/frontend/src/](codebase/frontend/src/) — landing pitch, chat-shell, Discord UI |

*(Vibe-coding rule: mỗi thành viên phải giải thích được deliverable có tên mình tại CP5/CP6.)*

## Artifact — chấm ở đâu

| Chấm | File |
|---|---|
| CP1 · Canvas | [canvas.md](canvas.md) |
| CP2 · Bấm được | [codebase/](codebase/) — `docker-compose up` |
| CP3 · AI thật + đo | [eval/results/](eval/results/) + [eval/traces/](eval/traces/) |
| CP4 · Spec (hạn cứng 23:59 N1) | [spec.md](spec.md) |
| R1 · Bằng chứng & impact | spec.md §1 + [evidence/mining-report.md](evidence/mining-report.md) + spec.md §10 |
| R2 · Lát cắt & thiết kế | spec.md §2 + §6 + §11 + §12 |
| R3 · Chỗ khó & kịch bản | spec.md §7 + [architecture/](architecture/) + spec.md §13 + §14 |
| R4 · Kiểm thử | spec.md §8 + §15 + [eval/](eval/) |
| R5 · Prototype | [codebase/](codebase/) + [architecture/discord-scope-model.md](architecture/discord-scope-model.md) |
| R6 · Validation | [validation/](validation/) |
| R7 · Repo & phân công | Bảng trên + spec.md §16 |
| Reflection cá nhân | [reflection/](reflection/) — mỗi người 1 file |

## Chạy prototype

```bash
cd codebase
docker-compose up -d
# Backend: http://localhost:8000  ·  Frontend: http://localhost:3000
```

Chi tiết setup + smoke test + snapshot demo: [codebase/README.md](codebase/README.md).

## Đo — golden set 22 case

```bash
python eval/run_eval.py --endpoint http://localhost:8000/chat
```

Quality bar: **≥80% pass + 100% no cross-scope leak + 100% không bịa khi không nguồn**.
Chi tiết [eval/quality-bar.md](eval/quality-bar.md).

## Tài liệu chương trình (không sửa)

- `01-de-bai.md` · `02-guide.md` · `03-template-ai-spec.md` · `04-rubric.md`
- `data/vlearn-pack/` — data pack cấp cho hackathon (không commit ra ngoài repo private)
- `tham-khao/` — JTBD Playbook + worksheet

## Điều bạn cần biết trước demo

- **Central AI decision:** authenticated user + membership + query intent + confirmed memory → chọn evidence được phép dùng để trả lời (spec §2).
- **Case hiểm nhất:** cross-team leak K02 (T004 hỏi T009) — test tự động trong `pytest` + golden set G08-G12.
- **Kill switch demo:** nếu Apify/Hindsight lỗi → snapshot synthetic + `hindsight-fallback` JSON store vẫn giữ được flow demo (xem PM-24H-PLAN.md).
