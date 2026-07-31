# ZicZord evaluation suite

Bộ eval kiểm tra một AI decision cụ thể:

> AI đọc các kênh Discord người dùng được phép xem và quyết định tin nào là
> decision, task, deadline hoặc blocker để tạo daily brief, dùng
> `qwen/qwen3.6-27b` qua OpenRouter pool.

## Cam kết trước khi chạy

- Chuẩn toàn bộ: ít nhất 80% câu đạt.
- Zero tolerance: không được trả lời sai deadline dù chỉ một lần.
- Cam kết nằm trong `cases.json` và trường `locked` phải luôn là `true`.

## Cấu trúc

- `cases.json`: 24 case chạy trực tiếp qua backend hiện tại.
- `results/baseline.json`: kết quả lần chạy đầu tiên, bao gồm cả case fail.
- `results/latest.json`: lần chạy gần nhất ở local, không commit.
- `results/runs/`: lịch sử các lần chạy local, không commit.
- `golden_set.csv`: 22 case rubric CP3/R4 do team xây dựng trước đó.
- `quality-bar.md`: quality bar gốc đã chốt cho golden set.
- `traces/`: vị trí lưu trace cục bộ khi cần phân tích sâu.

Hai bộ case đều được giữ lại. `cases.json` là bộ executable chính của release
v0.4; `golden_set.csv` là bằng chứng nguồn và coverage từ giai đoạn validation.

Mỗi case trong `cases.json` có các trường bắt buộc:

- `input`: user, channel và câu hỏi đưa vào sản phẩm.
- `expected_behavior`: sản phẩm phải phản hồi thế nào.
- `risk_types`: một hoặc nhiều nhóm rủi ro.
- `origin`: nguồn thực tế hay tình huống synthetic.
- `checks`: các điều kiện deterministic dùng để chấm.

## Chạy lại

Backend Docker phải đang chạy và đã cấu hình `ADMIN_API_KEY`.

```bash
python3 eval/run_eval.py
```

Script đọc admin key từ `codebase/.env`, chạy từng case qua admin API với
`persist=False` và ghi checkpoint sau mỗi câu. Kết quả mới được lưu vào
`eval/results/latest.json`; chat history và memory thật không bị thay đổi.

Chỉ dùng cờ sau cho lần baseline đầu tiên:

```bash
python3 eval/run_eval.py --baseline
```

Không ghi đè `acceptance_threshold` sau khi đã nhìn thấy kết quả.

Baseline đầu tiên hiện đạt **8/24 câu (33,3%)**. Cả bốn case deadline critical
đều fail, nên baseline chưa đạt zero-tolerance rule. Kết quả thấp được giữ nguyên
để làm bằng chứng cho các failure path cần sửa.
