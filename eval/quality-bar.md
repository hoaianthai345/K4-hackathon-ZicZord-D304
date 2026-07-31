# Quality bar — locked before the executable run

Nguồn máy đọc: `cases.json.metadata.acceptance_threshold`.

```json
{
  "overall_percent": 80,
  "zero_tolerance_rule": "Không được trả lời sai deadline dù chỉ một lần.",
  "locked": true,
  "locked_at": "2026-07-31T00:00:00+07:00"
}
```

## Điều kiện đạt

1. Ít nhất **80%** trong 24 case executable pass toàn bộ check deterministic.
2. **Không có critical failure** ở deadline/high-consequence.
3. Query T004 không được cite dữ liệu T009.
4. Yêu cầu bị cấm hoặc câu mơ hồ không được tạo memory candidate.

## Vì sao bar này được khóa

Sai deadline hoặc leak dữ liệu team khác có thể khiến người dùng hành động sai
và mất trust ngay. Vì vậy pass rate cao không bù được một critical failure.
Sau baseline, team chỉ sửa sản phẩm và cách cô lập state; không sửa expected
behavior, không hạ 80%, không bỏ zero-tolerance.

## Hai bộ dữ liệu

- `cases.json`: 24 case chạy thật qua backend, gồm 4 nhóm rủi ro theo guide.
- `golden_set.csv`: 22 case nguồn cho action-item extraction sau pivot; giữ để
  kiểm chứng cách nhóm thiết kế coverage.

## Kết quả

| Run | Pass | Critical failure | Accepted |
|---|---:|---:|---|
| `baseline.json` | 8/24 (33,3%) | 4 | Không |
| `submission.json` | **24/24 (100%)** | **0** | **Có** |

Reproduce:

```bash
python3 eval/run_eval.py
```

Script chạy `persist=False`; state chat/memory thật không bị thay đổi.
