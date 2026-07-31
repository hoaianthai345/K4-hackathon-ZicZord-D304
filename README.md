# Nhóm ZicZord · Team T004 · Lớp D304 · Khoá 4 — Discord Action-Item Copilot

Hướng: **B — Trợ lý Học viên (Discord)** · Loại: **Tính năng mới**
Trạng thái: pivot 31/07/2026; **survey n=24 · 5 interview · eval 24/24** —
xem [spec.md §9 Changelog](spec.md).

**Lát cắt MỘT CÂU:** team học viên chat trong `#🤖-gõ-commands` → bot đọc + phân
loại message thành candidate action item (task/decision/deadline/blocker/noise)
trong scope allowed + đề xuất owner + đề xuất scope → user confirm bằng click/email
→ sync sang Google Calendar/task tool + notify owner + track deadline. **Bot chỉ
propose, KHÔNG BAO GIỜ tự write.**

## Thành viên & phân công

| # | Mã HV | Tên đầy đủ | Lane | Deliverable có tên |
|---|---|---|---|---|
| 1 | 2A202601520 | **Nguyễn Hữu Tuyến** | PM + Frontend lead | [spec.md](spec.md), [canvas.md](canvas.md), pitch narrative, orchestration frontend |
| 2 | 2A202601862 | **Thái Hoài An** | Agent Design (Backend + AI) | [codebase/backend/app/](codebase/backend/app/) — chat_service, extraction prompt, guardrails K03 filter, scopes |
| 3 | 2A202601866 | **Vũ Thành Khang** | Scraw dữ liệu + Eval | Apify adapter, scripts crawl Discord, [eval/golden_set.csv](eval/golden_set.csv), [eval/run_eval.py](eval/run_eval.py) |
| 4 | 2A202601531 | **Trịnh Bá Khánh Trình** | Scraw dữ liệu + Eval | Đồng deliverable với Khang; [validation/interview-transcripts.md](validation/interview-transcripts.md) |
| 5 | 2A202601350 | **Nguyễn Văn Phúc** | Frontend UI | [codebase/frontend/src/](codebase/frontend/src/) — chat shell, candidate card, sync view |

*(Vibe-coding rule: mỗi thành viên phải giải thích được deliverable có tên mình tại CP5/CP6.)*

## Artifact — chấm ở đâu

| Chấm | File |
|---|---|
| CP1 · Canvas | [canvas.md](canvas.md) |
| CP2 · Bấm được | [codebase/](codebase/) — `docker-compose up` |
| CP3 · AI thật + đo | [eval/results/](eval/results/) + [eval/traces/](eval/traces/) |
| CP4 · Spec (hạn cứng 23:59 N1) | [spec.md](spec.md) |
| Demo slides | [demo-slides.pdf](demo-slides.pdf) · [bản HTML](demo-slides.html) · [script 3 phút](PITCH-SCRIPT-3-MIN.md) |
| Backup demo | [landing production](demo/production-landing.png) · [brief T004](demo/production-t004-brief.png) |
| Checklist nộp | [SUBMISSION-CHECKLIST.md](SUBMISSION-CHECKLIST.md) |
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
docker compose up -d
# Backend: http://localhost:8000  ·  Frontend: http://localhost:3000
```

Chi tiết setup + smoke test + snapshot demo: [codebase/README.md](codebase/README.md).

## Demo production

- Web: https://kute-discord-copilot.vercel.app/
- Feedback: https://github.com/hoaianthai345/K4-hackathon-ZicZord-D304/issues/5
- Backend public dùng Cloudflare Quick Tunnel cho pitch; URL tunnel có thể đổi
  khi tiến trình local khởi động lại.
- Google Tasks production hiện ở **pitch-mock** vì chưa có OAuth authorized-user;
  UI nói rõ mode và không tuyên bố đã ghi task thật.

## Đo — 24 case executable + 22 case nguồn

```bash
python3 eval/run_eval.py
```

Kết quả submission: **24/24 (100%)**, 0 critical failure, đạt quality bar khóa
ở **≥80% + zero tolerance cho deadline**. Xem
[submission.json](eval/results/submission.json) và
[quality-bar.md](eval/quality-bar.md).

## Trạng thái checklist cuối

- Đã có: README + phân công, spec, codebase, eval baseline/final, survey n=24,
  5 interview, 3 willing users, demo-slides PDF và live demo.
- Cần con người hoàn tất trước khi nộp: thêm **2 user-test prototype** để đủ 5
  và viết reflection riêng cho Nguyễn Văn Phúc.
- Chi tiết bằng chứng/pass/blocker: [SUBMISSION-CHECKLIST.md](SUBMISSION-CHECKLIST.md).

## Tài liệu chương trình (không sửa)

- `01-de-bai.md` · `02-guide.md` · `03-template-ai-spec.md` · `04-rubric.md`
- `data/vlearn-pack/` — data pack cấp cho hackathon (không commit ra ngoài repo private)
- `tham-khao/` — JTBD Playbook + worksheet

## Điều bạn cần biết trước demo

- **Central AI decision:** authenticated user + membership + query intent + confirmed memory → chọn evidence được phép dùng để trả lời (spec §2).
- **Case hiểm nhất:** cross-team leak K02 (T004 hỏi T009) — test tự động trong `pytest` + golden set G08-G12.
- **Kill switch demo:** nếu Apify/Hindsight lỗi → snapshot synthetic + `hindsight-fallback` JSON store vẫn giữ được flow demo (xem PM-24H-PLAN.md).
