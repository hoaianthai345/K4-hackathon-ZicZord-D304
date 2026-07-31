# Reflection — 2A202601531 · Trịnh Bá Khánh Trình

**Lane:** Scraw dữ liệu Discord + Eval 

## 1. Vai trò + phần mình làm cụ thể

**Deliverable có tên mình — 4 mảng công việc:**

**a) Evidence chuẩn B — crawl + mining Discord**
- Crawl kênh `#chung` khoá 4 thành `Crawl đoạn chat chung.xlsx` — 2.703 message, 7 ngày (22-30/07/2026). Đây là nguồn chính chuẩn B thay vì chỉ dựa VLearn tutor chatlog (thiếu ngữ cảnh Direction B).
- Cùng crawl thêm file `tonghop_painpoints_vlearn.csv` (455 msg curate tay) dùng để đối chiếu chéo.
- Kết quả mining: bóc 211 câu hỏi học viên, phân loại thành 10 nhóm logistics (47 lập nhóm · 24 slide/record · 22 GitHub · 13 deadline …), đo được **35% chờ TA >10 phút, 27% off-hours, cụm GitHub invite 47 msg lặp**. Số này là input trực tiếp cho `painpoint-analysis.md` §2-§5.

**b) Evidence chuẩn A — 5 phỏng vấn 1-1**
- Trực tiếp phỏng vấn 5 người ngoài nhóm: **Đào Hoàng Duy (U01780)**, **Đức Minh (U01306)**, **Nguyễn Văn Tuấn (U01246)**, **1 Senior/Mentor**, **Lợi** — ghi âm, sau đó tự transcribe + clean thành script sạch tại [`validation/interview-transcripts.md`](../validation/interview-transcripts.md).
- Điền [`validation/survey-log.md`](../validation/survey-log.md) 5/20 hàng đầu với cột "xác nhận pain" phân loại rõ (5/5 xác nhận, 3/5 sẽ dùng).
- Xác nhận 3 willing users tên thật (Tuấn/Mentor/Lợi) đủ tiêu chí 5 nghiệm thu.

**c) Quyết định pivot slice + orchestration spec**
- Chủ trì quyết định **pivot** từ *Kute Memory / Catch-up 24h* sang *Extract Action-Item + Sync task tool* sau khi có 5 interview — trực tiếp so sánh câu pitch đã hỏi user với slice trong spec cũ và phát hiện mismatch.
- Điều phối cập nhật **7 file** sau pivot: `spec.md` (§1/§2/§9/§10/§13/§16), `canvas.md`, `README.md`, `eval/golden_set.csv`, `eval/quality-bar.md`, `validation/interview-transcripts.md`, `validation/survey-log.md`.
- Cung cấp roster đầy đủ 5 thành viên với mã HV để điền vào 3 nơi (README/canvas/spec §16).

**d) Cùng Khang chốt cơ cấu golden set + quality bar sau pivot**
- 22 case cho slice Extract: 5 answerable · 4 noise (câu đùa/greeting/sarcasm) · 3 ambiguous · 4 cross-team/PII · 3 high-stakes deadline · 3 bonus.
- Đặc biệt **4 case K03** (G05/G07/G08/G22 — test câu đùa/emoji bị extract thành task) được thêm trực tiếp dựa trên warning Mentor.
- Chốt quality bar v2: ≥75% pass + **100% no auto-write** + **100% no cross-team owner** + **FP rate ≤ 10%**.

**e) QA + feedback loop trên prototype**
- Test bản prototype cá nhân [D:\...\codebase](D:\Batch03-K4-AI-Product-Hackathon-main\Batch03-K4-AI-Product-Hackathon-main\codebase) và phát hiện 2 lỗi UX: **web không scroll được** (bug grid child thiếu `min-height: 0`) + **tab kênh không bấm được gây hiểu nhầm** — báo lại để fix ngay bằng toast giải thích + mờ 55% các kênh mockup.
- Sửa hiểu nhầm về Trợ lý Kute BTC vs bot nhóm — dẫn tới quyết định KHÔNG cố tích hợp bot BTC mà **mở rộng corpus** từ 16 → 49 mẩu.

**Chỗ mình chắc chắn giải thích được:**
- **Tại sao chọn `#chung` để crawl** thay vì kênh khác: là kênh chính học viên hỏi logistics & bàn công việc, mật độ message cao nhất, không giới hạn quyền → dễ mining reproducible.
- **Cách 5 phỏng vấn được thiết kế** — hỏi hành vi hiện tại trước (nền tảng chat, tool task), rồi mới trình bày pitch; theo nguyên tắc `02-guide.md §1.3` (*"hỏi lần gần nhất, tránh hỏi ý kiến 'bạn có cần X không'"*).
- **Tại sao giữ nguyên đoạn hội thoại lặp/lỗi trong file gốc** — evidence chuẩn A yêu cầu log nguyên văn; sau đó mới clean thành script.
- **Tại sao golden set có 4 case cho lớp `noise`** — trực tiếp từ warning Mentor: *"AI làm sai sẽ khiến người dùng cảm thấy mất công chui vào check và xóa"* — false positive là risk chốt tử.
- **Tại sao pivot mà không giữ 2 slice** — 24h không đủ để build cả hai; chuẩn A trên slice cũ (Catch-up) = 0 interview, chuẩn A trên slice mới (Extract) = 5/5 xác nhận pain → chọn cái có bằng chứng.
- **Tại sao FP rate là bar cứng ≤10% chứ không chỉ pass tổng ≥75%** — Mentor cảnh báo trực tiếp; nếu FP cao user sẽ mất trust ngay lập tức → không recall được kể cả khi precision còn tốt.

## 2. AI hỗ trợ mình thế nào

**Tool đã dùng:** Claude Code (Opus 4.7).

**Prompt điển hình (5 cái đáng nhớ):**
1. *"Đọc file crawl Discord, đếm câu hỏi học viên có bao nhiêu là logistics, tính thời gian chờ TA rep"* → AI viết pandas script chạy trực tiếp trên xlsx, trả về 131/211 câu logistics + p75 = 17 phút.
2. *"Painpoint đau nhất cho startup ở đây là gì?"* → AI phân tích ra 3 cụm rồi mình chọn cụm "câu logistics lặp lại" — dẫn tới painpoint-analysis.md.
3. *"Sau 5 interview này, phân tích xem pain có match slice hiện tại không"* → AI phát hiện lát cắt spec cũ (Catch-up 24h) khác với câu đã hỏi user (Extract+Sync) → dẫn tới quyết định pivot.
4. *"So sánh repo nhóm và bản cá nhân theo tiêu chí chương trình"* → AI trả bảng gap R1-R7 → dẫn tới port canvas/eval/reflection/spec-appendix sang ZicZord.
5. *"Web không scroll được và tab không bấm được — CP2 chưa đáp ứng?"* → AI tách 2 vấn đề: bug thật (`min-height: 0`) vs design intent (kênh mockup) → fix từng cái không confuse các mối lo.

**Chỗ AI làm được ngay:**
- Sinh pandas script mining + đếm cluster fuzzy dedup (nhóm 47 msg GitHub invite) trong lần chạy đầu.
- Draft spec §10 impact table đúng format bảng ≥3 ứng viên có ứng viên loại.
- Build prototype web Discord-style trong 1 lượt (HTML/CSS/JS + FastAPI backend).
- Sinh threat-model 20 case + data-flow diagram cho `architecture/`.

**Chỗ AI sinh sai, mình phải sửa:**
- AI ban đầu viết pain statement có chữ "AI" — mình bỏ ra để đạt yêu cầu `03-template-ai-spec.md` §1 *"Problem statement KHÔNG chữ AI"*.
- AI đề xuất giữ nguyên slice cũ và ghi 5 interview vào Changelog cho v2 — mình quyết pivot ngay vì bằng chứng chuẩn A rõ hơn giả thuyết cũ, không đợi được.
- AI khi build canvas ban đầu điền `[tên]` placeholder — mình cung cấp mã HV 5 thành viên để điền tất cả chỗ.
- AI đề xuất **tích hợp bot Discord thật** (option 3 ban đầu) — mình đổi sang web UI style Discord vì không cần Developer Portal + demo tự chủ hơn.
- AI ban đầu tưởng bot cá nhân đang trả lời dựa trên 2 CSV — mình phải làm rõ 2 CSV là input MINING, bot dùng `corpus.md` khác; nếu không làm rõ AI sẽ mở rộng nhầm corpus.
- AI viết spec §11 giải pháp tương tự so sánh với NotebookLM/Slack summary — chưa đúng cho slice Extract mới; đối thủ trực tiếp hơn là Zapier/Notion AI, sẽ cần rewrite ở phiên bản sau.

## 3. Một bài học từ case fail của chính nhóm

**Case fail cụ thể:**
Nhóm viết spec Kute Memory / Catch-up 24h TRƯỚC khi có interview thật. Đến 31/07 khi mình chạy 5 phỏng vấn, phát hiện câu pitch mình ĐANG HỎI USER là *"bot đọc chat + đồng bộ Jira"* (Extract+Sync) — **hoàn toàn khác** slice trong spec (Catch-up). 5/5 xác nhận pain Extract, nhưng nếu grader đọc spec cũ + interview mới sẽ hỏi *"rốt cuộc bạn build cái nào?"*

Hậu quả: mất ~4h ngày 31/07 để pivot spec (§1, §2, §9, §10, §13, §16), rewrite golden set 22 case cho slice mới, cập nhật canvas. Nếu phát hiện muộn hơn (sau CP4 spec đã commit) sẽ mất 5đ CP4 + rủi ro grader R1-R4.

**Bài học:**
- **Interview thật ≥ giả thuyết đẹp trên giấy.** Guide `02-guide.md §1.1` nói "5 câu hỏi phải tự trả lời trước" nhưng dễ nghĩ "trả lời được rồi = biết" — thực ra chưa. Phải hỏi user thật trước khi lock spec.
- **Câu pitch cho user phải khớp lát cắt spec ngay từ đầu.** Nếu 2 câu khác nhau, tín hiệu từ interview không quy về spec được.
- **Chuẩn A + chuẩn B kết hợp mạnh hơn từng cái riêng lẻ** — chuẩn B (mining Discord) chỉ chứng minh pain tồn tại; chuẩn A (5 interview) chứng minh 3/5 sẽ dùng giải pháp cụ thể → mới đủ căn cứ chọn slice.

## 4. Nếu làm lại từ đầu, mình sẽ làm khác gì

- **H0 chạy 3 phỏng vấn ngắn trước khi viết Canvas CP1**, chứ không phải sau CP4. Đổi 30 phút ngày 1 lấy 4 giờ ngày 2.
- **Câu pitch trong phỏng vấn phải đúng chính xác chữ lát cắt spec** — kể cả từ ngữ ("bot đọc chat + đồng bộ" thay vì "bot tóm tắt catch-up"). Nếu không thì tín hiệu thu về không ánh xạ được spec.
- **Crawl Discord từ ngày 1** thay vì đợi tới khi có Apify — dùng Discord native export hoặc script Selenium, không cần vendor tool. Đã có `Crawl đoạn chat chung.xlsx` từ 30/07, nếu có sớm 1 ngày thì mining-report cũng sớm 1 ngày.
- **Log warning từ mentor ngay vào architecture/threat-model.md** — không phải chờ chuyển thành golden set case. Warning "false positive từ câu đùa" đáng được note riêng ở threat model chứ không chỉ là 1 dòng trong survey-log.
