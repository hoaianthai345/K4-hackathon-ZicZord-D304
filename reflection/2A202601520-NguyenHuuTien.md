# Reflection — 2A202601520 · Nguyễn Hữu Tuyến

## 1. Vai trò + phần mình làm cụ thể

- **Lane:** PM + Frontend lead (PM+Demo theo `PM-24H-PLAN.md`)

- **Deliverable có tên mình:**
  - [`spec.md`](../spec.md) — toàn bộ spec, trong đó phần mình tự viết nặng nhất là
    **§10 Impact table** (5 ứng viên, cột số người × tần suất × tốn gì mỗi lần ×
    cost-of-error), **§2 Lát cắt MỘT CÂU + quyết định automation `conditional-with-confirm`**,
    **§13 bảng 12 kịch bản K01–K12**, **§14 4 đường đi trải nghiệm**, **§16 phân công + willing users**.
  - [`canvas.md`](../canvas.md) — canvas 7 dòng CP1, và bản viết lại sau pivot 31/07.
  - **§9 Changelog** — 3 dòng ngày 31/07 (pivot slice, đổi automation, chốt 3 willing users):
    mình là người ra quyết định pivot và là người phải chịu trách nhiệm giải thích nó.
  - **Pitch narrative + orchestration frontend** — `codebase/frontend/src/components/pitch-deck.tsx`,
    landing 7 section scroll (`home → problem → model → scope → demo → trust → next`),
    khớp đúng thứ tự script pitch 5 phút trong `PM-24H-PLAN.md`; phần điều phối
    `site-nav.tsx` + `theme-toggle.tsx` + shell layout `app/layout.tsx`.

- **Đã tự tay làm** (không chỉ copy AI):
  - **Quyết định pivot slice sáng 31/07.** Sau khi đọc 5 transcript trong
    `validation/interview-transcripts.md`, mình đối chiếu 2 con số: slice cũ
    "Catch-up 24h" có **0/5 người chủ động nêu**, còn "Discord bị bỏ rơi vì thiếu
    task tool" có **5/5 chủ động nêu (100%)** và **3/5 nói sẽ dùng (60%)**. Mình cắt
    slice cũ xuống v2 và viết lại §2 quanh Extract + Sync. Đây là chỗ mình đánh đổi
    ~10 giờ code catch-up đã có để đổi lấy một lát cắt có bằng chứng trực tiếp.
  - **Xếp `automation = conditional-with-confirm` và bảo vệ nó bằng code-level guard.**
    Không phải mình tự nghĩ ra — nó đến từ đúng một câu của Mentor trong Interview 4:
    *"AI làm sai sẽ khiến người dùng cảm thấy mất công chui vào check và xóa"*.
    Mình chuyển câu đó thành **K11** trong §13 (mọi write ra external tool phải qua
    `POST /confirm` với `user_id + candidate_id`, không có auto-mode) và thành bar
    tuyệt đối **100% no auto-write** trong `eval/quality-bar.md`.
  - **Viết §12 HAX/PAIR bằng cách đi ngược từ code lên nguyên tắc**, không phải chép
    5 nguyên tắc rồi gán bừa. Với mỗi dòng mình mở file để chắc là chỗ đó tồn tại
    thật: G1 → `pitch-deck.tsx`; G2 → panel scope bên phải trong `chat-shell.tsx`;
    G10 → `backend/app/scopes.py` (`allowed_scope_keys`, `can_write_scope`) trả 403;
    G17 → `POST /api/memory-candidates/{id}/confirm` trong `backend/app/main.py:601`.
  - **Đặt bar tuyệt đối tách khỏi bar chính** trong `eval/quality-bar.md`: pass-rate
    là chỉ số *recall* (bỏ sót task hợp lệ — chấp nhận được), còn no-auto-write /
    no-cross-team-owner là chỉ số *trust* (vỡ 1 case là vỡ hết). Đây là quyết định
    PM, không phải quyết định kỹ thuật.

- **Chỗ mình chắc chắn giải thích được:**
  - **Tại sao chọn ứng viên #1 mà loại #2 (Catch-up), dù #2 đã code gần xong.**
    Vì #2 có pain hợp lệ nhưng **không interview nào chủ động nêu**; #1 có 5/5.
    Rubric R1 chấm bằng chứng, không chấm mức độ hoàn thiện — mình chọn đi theo
    bằng chứng và ghi rõ #2 vào §10 kèm lý do loại thay vì xoá dấu vết.
  - **Tại sao `conditional` chứ không `full automation`, diễn giải bằng cost-of-error:**
    sai thì đắt (user phải chui vào Jira dọn task rác → mất trust → team bỏ dùng,
    đúng cái pain ban đầu quay lại); prevent thì rẻ (thêm 1 click confirm).
  - **Tại sao K03 (câu đùa có action word) là case hiểm nhất, không phải K08 (cross-team).**
    Cross-team leak là lỗi có boundary rõ, chặn được bằng `scopes.py` một lần.
    K03 là lỗi *xác suất* nằm trong phán đoán của model — G05/G08/G22 trong
    `golden_set.csv` đều có từ "deploy" nhưng đều là `noise`; không có boundary nào
    chặn được, chỉ có threshold. Vì vậy bar cho nó là ≤10% chứ không phải 0%.
  - **Cấu trúc pitch 7 section và vì sao `trust` đứng trước `next`:** giám khảo phải
    thấy giới hạn của bot trước khi nghe roadmap, nếu không roadmap nghe như overclaim.

## 2. AI hỗ trợ mình thế nào

- **Tool:** Claude Code (Opus) trong terminal — dùng cho spec + frontend.
  *(Nếu mình có dùng thêm tool khác ở CP nào thì bổ sung dòng này trước CP5.)*

- **Prompt điển hình** (2 prompt thật, rút gọn):
  1. *"Đọc `validation/interview-transcripts.md`. Với mỗi ứng viên trong bảng impact
     §10, đếm xem có bao nhiêu/5 người **chủ động** nêu pain đó — chủ động nghĩa là
     nói ra trước khi người phỏng vấn mô tả giải pháp. Đừng tính lượt họ chỉ đồng ý
     sau khi được pitch."*
  2. *"Với mỗi nguyên tắc HAX mình liệt kê ở §12, mở file mình chỉ ra và xác nhận
     đoạn code đó có thật. Cái nào không tìm được thì nói không tìm được, đừng suy ra."*

- **AI làm được ngay:**
  - Sinh khung bảng markdown cho §10/§13/§14 và giữ format nhất quán qua nhiều lần sửa.
  - Rà chéo file: chỉ ra `spec.md` §7 rubric map đang trỏ tới `validation/user-test-log.md`
    — file không tồn tại (thực tế là `interview-transcripts.md` + `survey-log.md`).
  - Boilerplate scroll-spy `IntersectionObserver` + `useReducedMotion` cho `pitch-deck.tsx`.

- **AI sinh sai, mình sửa:**
  - **AI viết bảng impact với con số tròn kiểu "~500 học viên bị ảnh hưởng"** — nghe
    to nhưng không kiểm lại được. Mình đổi sang cách đếm truy được: *~50-80 team ×
    3-5 hv = 150-400 hv đang chạy project*, có mẫu số rõ để người ngoài kiểm lại.
    Rubric R1 yêu cầu "phương pháp đếm kiểm lại được", không yêu cầu số to.
  - **AI đề xuất để bot auto-write task khi confidence > 0.8** ("giảm ma sát cho user").
    Mình bỏ hẳn nhánh này: nó vi phạm trực tiếp warning của Mentor, và một khi tồn tại
    code path auto-write thì bar "100% no auto-write" không còn nghĩa gì. Thay bằng
    K11 — guard ở server, **không có auto-mode kể cả confidence = 1.0**.
  - **AI gán nguyên tắc HAX theo tên nghe hợp lý** (kiểu "G5 — kết quả có liên quan")
    mà không trỏ được vào file nào. Mình cắt xuống còn 5 nguyên tắc trỏ được vào code
    thật. Rubric cho điểm ở "mỗi nguyên tắc trỏ được vào chỗ cụ thể trong prototype",
    liệt kê 8 cái rỗng còn tệ hơn 5 cái có địa chỉ.
  - **AI muốn xoá ứng viên đã loại khỏi §10** cho bảng gọn. Mình giữ lại — rubric có
    3 điểm riêng cho "ứng viên bị loại được giữ lại + lý do chọn bằng số".

## 3. Một bài học từ case fail của chính nhóm

**Case fail cụ thể — pivot spec nhưng không pivot những thứ ăn theo spec:**

Sáng 31/07 mình pivot slice và viết lại `spec.md` + `canvas.md` + `golden_set.csv`
(commit `6b358b6`). Mình coi như xong. Nhưng pivot làm vỡ **4 chỗ ăn theo mà mình
không đi rà**, và đều là chỗ bị chấm điểm:

1. **`eval/run_eval.py` chết ngay dòng đầu.** Runner viết ở CP4 (commit `7b9e43a`)
   đọc `row["expected_needs_source"]`, `row["forbidden_scopes"]`, `row["user_id"]`,
   `row["question"]`. Golden set sau pivot đổi cột thành `expected_needs_confirm`,
   `forbidden_action`, `poster_user`, `message` → `KeyError` ngay case G01.
   **Hệ quả: bảng kết quả §15 vẫn trống (dòng L1 rỗng)** — đúng 4 điểm R4 "bảng kết
   quả chạy trọn bộ ≥1 lượt".
2. **Bar bị hai con số.** `run_eval.py` hardcode `BAR_PASS_RATE = 0.80`; `quality-bar.md`
   sau pivot ghi **75%** + 3 bar mới (no-auto-write / no-cross-team-owner / FP ≤10%);
   `spec.md` §15 và `README.md` vẫn ghi 80% + bar cũ (no-leak / không bịa). Rubric
   yêu cầu bar **chốt 23:59 N1 và giữ nguyên** — ba con số lệch nhau làm chính mình
   khó chứng minh là đã giữ nguyên.
3. **Cơ cấu golden set trong spec không khớp file.** §15 khai ⓪7 · ①4 · ②3 · ③5 · ④3;
   đếm thật trong `golden_set.csv` là ⓪6 · ①6 · ②4 · ③3 · ④3. Tổng vẫn 22 nên nhìn
   qua không ai thấy.
4. **Prototype vẫn kể câu chuyện cũ.** `catchup_service.py` phân loại bằng regex, chưa
   có adapter Jira/Sheets, chưa có candidate action-item + `needs_confirm`; `pitch-deck.tsx`
   vẫn là *"Ba câu hỏi. Một context graph."*; §14 happy path vẫn viết "bấm Bắt kịp 24h"
   ngay trong một spec đã pivot sang Extract + Sync. Tức là R5 "chạy end-to-end theo
   **lát cắt đã khai**" đang bị chính spec của mình tố.

**Bài học:**

Mình đã đối xử với spec như **tài liệu** trong khi nó là **interface**. `golden_set.csv`
là contract giữa spec và `run_eval.py`; câu lát cắt §2 là contract giữa spec và
`pitch-deck.tsx` + backend. Đổi một interface mà không đi hết danh sách consumer thì
không phải "cập nhật tài liệu" — đó là **breaking change im lặng**, và nó im lặng đúng
đến lúc chạy eval thì mới nổ, tức là muộn nhất có thể.

Cụ thể hơn: sai của mình là ở **thứ tự**. Mình sửa từ tài liệu xuống code (spec → csv →
hy vọng runner ổn). Đúng ra phải sửa **từ chỗ chạy được lên**: đổi `golden_set.csv` →
chạy `run_eval.py` cho nó nổ ngay → sửa runner → **lúc đó** mới viết lại §15 bằng con số
thật vừa chạy ra. Cái nào chạy được thì cái đó là source of truth, tài liệu đi sau.
Đây cũng đúng là vai trò PM mà mình làm thiếu: pivot là quyết định của mình, nên
**blast radius của pivot cũng là việc của mình**, không phải việc của người sở hữu file bị vỡ.

## 4. Nếu làm lại từ đầu, mình sẽ làm khác gì

1. **Chạy `run_eval.py` một lần ở H1 với endpoint rỗng, trước khi có model.** Chỉ cần
   nó đọc trọn CSV và in ra `0/22 pass` là đủ — từ đó mọi lần đổi golden set đều nổ
   ngay trong 30 giây thay vì nổ ở H17. Contract phải chạy được trước khi có nội dung.
2. **Một con số bar, một chỗ duy nhất.** Cho `run_eval.py` **đọc** bar từ
   `eval/quality-bar.md` (hoặc `eval/bar.json`) thay vì hardcode `BAR_PASS_RATE = 0.80`,
   rồi `spec.md` §15 nhúng lại từ đó. Bar tồn tại 3 bản copy tay là bar chắc chắn sẽ lệch.
3. **Coi pivot là task có checklist consumer, không phải một commit sửa spec.** Trước khi
   pivot, viết ra danh sách "ai đang đọc câu lát cắt này": golden set · runner · spec §14 ·
   `pitch-deck.tsx` · backend service · README · canvas. Pivot chỉ được coi là xong khi
   hết danh sách — và ping trực tiếp người sở hữu từng file (An/Khang/Trình/Phúc) thay vì
   sửa spec rồi cho rằng cả nhóm tự đọc thấy.
4. **Interview 5 người **trước** khi build, không phải song song.** 5 interview mất
   khoảng 1 giờ và chúng đảo hoàn toàn lát cắt. Mình đã để nhóm code catch-up ~10 giờ
   rồi mới đi hỏi user. Đổi thứ tự đó là thứ rẻ nhất và có lợi nhất trong cả 24 giờ.
5. **Chốt lát cắt bằng bài test, không bằng câu văn.** Câu §2 dài và đẹp nên vẫn đọc trôi
   sau khi đã lệch khỏi bản build. Nếu §2 kèm 3 case cụ thể trong golden set là "định
   nghĩa sống" của lát cắt (G01 task rõ · G05 câu đùa · G12 cross-team owner), thì lúc
   prototype lệch khỏi lát cắt, **eval đỏ** — không cần ai đọc lại spec mới phát hiện.

---

### Việc mình phải đóng trước CP5 *(hệ quả trực tiếp của §3)*

- [ ] Sửa `run_eval.py` khớp schema golden set mới → chạy 1 lượt trọn 22 case → điền dòng L1 §15.
- [ ] Đồng bộ bar về **một** con số (75% hay 80%) ở `run_eval.py` · `quality-bar.md` · `spec.md` §15 · `README.md`.
- [ ] Sửa cơ cấu case §15 cho khớp `golden_set.csv` (⓪6 · ①6 · ②4 · ③3 · ④3).
- [ ] Sửa link chết `validation/user-test-log.md` trong `spec.md` §7 rubric map.
- [ ] Điền placeholder còn lại: họ tên đầy đủ Mentor + Lợi (§16), người phụ trách validation, Zone.
- [ ] Cập nhật `pitch-deck.tsx` + §14 happy path sang câu chuyện Extract + Sync.
