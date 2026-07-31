# eval/ — Golden set + Quality bar cho Kute Memory

**Deliverable CP3 + R4 (15đ).**

## File

| File | Mục đích |
|---|---|
| `golden_set.csv` | 22 case, cơ cấu ≥2/lớp chỗ khó + ≥10 từ data thật |
| `quality-bar.md` | Bar chốt trước 23:59 N1 — copy vào `spec.md §15` |
| `run_eval.py` | Runner: POST tới endpoint chat + so kết quả với expected |
| `results/` | Bảng CSV mỗi lượt chạy (được tạo tự động) |
| `traces/.gitkeep` | Trace log AI call (backend tự ghi khi request tới) |

## Chạy

```bash
# 1. Boot backend
cd codebase
docker-compose up -d
# đợi backend healthy tại http://localhost:8000

# 2. Chạy eval
cd ../eval
python run_eval.py --endpoint http://localhost:8000/chat
```

Output:
- `eval/results/results-<ts>.csv` — bảng kết quả 22 case
- Stdout: bảng %, breakdown theo class, đối chiếu quality bar

## Adapt cho endpoint thực

`run_eval.py` mặc định POST body `{"user_id": ..., "question": ...}` và mong đợi
response `{"class": ..., "citations": [...], "used_scopes": [...], ...}`.

Nếu API của nhóm khác, edit function `call_endpoint()` và `parse_response()` ở
đầu file — 2 chỗ duy nhất cần đổi.

## Vì sao 22 case (không phải nhiều hơn)

Guide `02-guide.md §2.6` yêu cầu ≥20. 22 case đủ phủ 4 lớp chỗ khó (mỗi lớp ≥3)
+ ≥10 từ chatlog/transcript thật + case cross-team K02 (case hiểm nhất). Thêm
case sau khi có feedback CP5 — ghi vào changelog spec §9.
