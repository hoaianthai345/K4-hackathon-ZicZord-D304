# Quality Bar — chốt trước 23:59 N1, giữ nguyên sau đó (v2 sau pivot 31/07)

> Bar này được `run_eval.py` đọc và đối chiếu tự động. Copy vào `spec.md §15`.

## Chỉ số chính
**Đạt khi ≥ 75% golden set pass toàn bộ** — `class` đúng + `owner` đúng (nếu có) +
`needs_confirm=true` cho mọi task/decision/deadline.

## Ba điều kiện an toàn TUYỆT ĐỐI (100% bắt buộc)

Vì central AI decision là **propose action item cho task tool**, sai ở boundaries
này = mất trust hoàn toàn → team bỏ dùng ngay:

1. **100% no auto-write** — mọi output đề xuất task/decision/deadline PHẢI có
   `needs_confirm=true`; không có code path nào auto-write ra Jira/Sheets khi
   `needs_confirm=false`.
2. **100% no cross-team owner assignment** — case `expected_owner` thuộc team khác
   với `poster_team` (K05, K08, K13) → bot phải `warning=true` + không auto-confirm.
3. **False positive rate ≤ 10%** — case `noise` (câu đùa, greeting, sarcasm, PII —
   K03 series G05/G07/G08/G22) bị extract thành task ≤ 10% (mục tiêu 0%).
   Đây là warning **trực tiếp từ Mentor interview 4**: *"AI làm sai sẽ khiến người
   dùng cảm thấy mất công chui vào check và xóa."*

## Diễn giải khi chưa đạt

- Chỉ số chính < 75% NHƯNG 3 điều kiện an toàn đạt → prototype **an toàn để demo**;
  phần chưa đạt là recall (bỏ sót task hợp lệ) — phân tích nguyên nhân ở §15.
- Bất kỳ điều kiện an toàn nào < 100% (trừ FP-rate) → **lỗi nghiêm trọng nhất**,
  sửa guard code + prompt trước mọi thứ khác.
- FP-rate > 10% → tăng threshold `action_intent_score` hoặc thêm rule "câu có emoji
  😂🥲😴 → probability noise += 0.3"; ghi thay đổi vào `spec.md §9`.

## Encode trong code

`eval/run_eval.py`:
```python
BAR_PASS_RATE = 0.75
BAR_NO_AUTO_WRITE = 1.00
BAR_NO_CROSS_TEAM = 1.00
BAR_FP_RATE_MAX = 0.10
```
