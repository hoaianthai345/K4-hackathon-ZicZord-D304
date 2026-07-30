"use client";

import {
  ArrowRight,
  Brain,
  Check,
  Database,
  DiscordLogo,
  Eye,
  Hash,
  LockKey,
  ShieldCheck,
  Sparkle,
  Stack,
  User,
  Users,
  UsersThree,
} from "@phosphor-icons/react";
import { motion, useReducedMotion } from "motion/react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { ChatShell } from "./chat-shell";
import { SiteNav } from "./site-nav";

const sections = ["home", "problem", "model", "scope", "demo", "trust", "next"];

function Reveal({
  children,
  className = "",
  delay = 0,
}: {
  children: React.ReactNode;
  className?: string;
  delay?: number;
}) {
  const reduceMotion = useReducedMotion();
  return (
    <motion.div
      initial={reduceMotion ? false : { opacity: 0, y: 20 }}
      whileInView={reduceMotion ? undefined : { opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.2 }}
      transition={{ duration: 0.5, delay, ease: [0.22, 1, 0.36, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <span className="section-label">{children}</span>;
}

export function PitchDeck() {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (!visible) return;
        const index = sections.indexOf(visible.target.id);
        if (index >= 0) setActive(index);
      },
      { threshold: [0.25, 0.55, 0.8] },
    );
    sections.forEach((id) => {
      const element = document.getElementById(id);
      if (element) observer.observe(element);
    });
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (["INPUT", "TEXTAREA", "SELECT"].includes((event.target as HTMLElement).tagName)) return;
      if (!["ArrowDown", "ArrowUp", "PageDown", "PageUp"].includes(event.key)) return;
      event.preventDefault();
      const direction = event.key === "ArrowDown" || event.key === "PageDown" ? 1 : -1;
      const next = Math.min(sections.length - 1, Math.max(0, active + direction));
      document.getElementById(sections[next])?.scrollIntoView({ behavior: "smooth" });
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [active]);

  return (
    <main className="pitch-root">
      <SiteNav />

      <nav className="pitch-pager" aria-label="Điều hướng pitch">
        {sections.map((id, index) => (
          <button
            key={id}
            type="button"
            className={active === index ? "pitch-dot pitch-dot-active" : "pitch-dot"}
            onClick={() => document.getElementById(id)?.scrollIntoView({ behavior: "smooth" })}
            aria-label={`Đến phần ${index + 1}`}
            aria-current={active === index ? "step" : undefined}
          />
        ))}
      </nav>

      <section id="home" className="pitch-section hero-section">
        <div className="pitch-container hero-layout">
          <Reveal className="hero-copy-block">
            <div className="mb-7 flex flex-wrap items-center gap-3">
              <span className="kicker">
                <DiscordLogo size={15} weight="fill" />
                Discord Learning Copilot
              </span>
              <span className="text-xs font-semibold text-muted">Hackathon · K4</span>
            </div>
            <h1 className="hero-title">
              <span className="block">Discord nhớ đúng.</span>
              <span className="block text-accent-strong">Từng người. Từng nhóm.</span>
            </h1>
            <p className="hero-copy">
              Tóm tắt hội thoại, nối bài giảng và recall memory đúng phạm vi của từng học viên.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/chat" className="button">
                Chạy demo live
                <ArrowRight size={17} weight="bold" />
              </Link>
              <a href="#problem" className="button-secondary">
                Xem pain point
              </a>
            </div>
            <div className="hero-proof">
              <div>
                <p className="proof-value">4</p>
                <p className="proof-label">người mỗi team</p>
              </div>
              <div>
                <p className="proof-value">6</p>
                <p className="proof-label">tuần làm project</p>
              </div>
              <div>
                <p className="proof-value">5</p>
                <p className="proof-label">tầng memory</p>
              </div>
            </div>
          </Reveal>

          <Reveal className="hero-product" delay={0.1}>
            <div className="product-window-top">
              <div className="window-dots" aria-hidden="true">
                <span />
                <span />
                <span />
              </div>
              <p>Kute Memory · live API</p>
              <span className="live-label">
                <span className="status-dot" />
                Ready
              </span>
            </div>
            <div className="hero-product-body">
              <ChatShell compact />
            </div>
          </Reveal>
        </div>
      </section>

      <section id="problem" className="pitch-section">
        <div className="pitch-container section-pad">
          <Reveal>
            <SectionLabel>Khoảng trống đang có trong Discord</SectionLabel>
            <div className="section-heading-grid">
              <h2 className="section-title">
                Bot có mặt trong server. Nhưng không hiểu lớp đang làm gì.
              </h2>
              <p className="section-copy">
                Cùng một câu hỏi cần đọc channel, vai trò, phòng học và lịch sử project trước khi trả lời.
              </p>
            </div>
          </Reveal>

          <div className="problem-layout">
            <Reveal className="failure-quote">
              <div className="quote-header">
                <span className="avatar avatar-bot">K</span>
                <div>
                  <p className="font-bold text-accent-strong">Trợ lý Kute <span className="bot-badge">APP</span></p>
                  <p className="text-xs text-muted">trong #💬-chung</p>
                </div>
              </div>
              <blockquote>
                “Mình chưa có đủ thông tin cho câu này, nên để đảm bảo chính xác, mình sẽ tag Mod giúp bạn nhé!”
              </blockquote>
              <div className="failure-result">
                <span className="failure-pulse" />
                <p>
                  Mỗi câu recap lại quay về moderator. Nhu cầu thật đã xuất hiện, nhưng bot không có context.
                </p>
              </div>
            </Reveal>

            <Reveal className="context-fragment" delay={0.08}>
              <p className="context-fragment-title">Một học viên đang sống trong nhiều context</p>
              <div className="fragment-list">
                {[
                  ["T004", "quyết định và task của 4 thành viên"],
                  ["G10", "feedback chung từ mentor"],
                  ["Lec-D302", "nội dung bài giảng"],
                  ["Lab-D304", "hướng dẫn thực hành"],
                  ["K4", "thông báo, hỏi đáp, chia sẻ"],
                ].map(([label, detail], index) => (
                  <div key={label} className="fragment-row">
                    <span className="fragment-index">{String(index + 1).padStart(2, "0")}</span>
                    <div>
                      <p className="font-bold">{label}</p>
                      <p className="mt-1 text-sm text-muted">{detail}</p>
                    </div>
                  </div>
                ))}
              </div>
            </Reveal>
          </div>
        </div>
      </section>

      <section id="model" className="pitch-section">
        <div className="pitch-container section-pad">
          <Reveal>
            <SectionLabel>Mô hình cộng đồng</SectionLabel>
            <h2 className="section-title mt-5 max-w-5xl">
              Danh tính tạo ra quyền truy cập. Quyền truy cập quyết định memory.
            </h2>
          </Reveal>

          <div className="hierarchy-map">
            <Reveal className="identity-card">
              <span className="identity-avatar">AN</span>
              <div>
                <p className="text-xs font-semibold text-accent-strong">CURRENT USER</p>
                <h3>Thái Hoài An</h3>
                <p>T004-Thái Hoài An-01862</p>
              </div>
            </Reveal>

            <div className="hierarchy-rail" aria-hidden="true" />

            <div className="hierarchy-branches">
              {[
                {
                  icon: UsersThree,
                  title: "Team T004",
                  detail: "4 học viên · project 6 tuần",
                  memory: "decision · task · blocker",
                },
                {
                  icon: Users,
                  title: "Group G10",
                  detail: "nhiều team · 1 mentor",
                  memory: "feedback · check-in",
                },
                {
                  icon: Stack,
                  title: "Phòng học",
                  detail: "Lec-D302 · Lab-D304",
                  memory: "lecture · lab note",
                },
                {
                  icon: Hash,
                  title: "Cộng đồng K4",
                  detail: "chung · hỏi đáp · chia sẻ",
                  memory: "announcement · knowledge",
                },
              ].map((item, index) => (
                <Reveal key={item.title} className="hierarchy-branch" delay={index * 0.06}>
                  <span className="branch-icon">
                    <item.icon size={20} weight="duotone" />
                  </span>
                  <div className="min-w-0">
                    <h3>{item.title}</h3>
                    <p>{item.detail}</p>
                    <code>{item.memory}</code>
                  </div>
                </Reveal>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section id="scope" className="pitch-section">
        <div className="pitch-container section-pad">
          <Reveal>
            <SectionLabel>Memory architecture</SectionLabel>
            <div className="section-heading-grid">
              <h2 className="section-title">Tin nhắn là bằng chứng. Memory là điều đã được chốt.</h2>
              <p className="section-copy">
                Hai lớp dữ liệu không bị trộn: snapshot dùng để trích nguồn, Hindsight giữ canonical memory theo scope.
              </p>
            </div>
          </Reveal>

          <div className="pipeline">
            <Reveal className="pipeline-source">
              <div className="pipeline-node-title">
                <DiscordLogo size={21} weight="fill" />
                <div>
                  <p>Discord</p>
                  <span>authorized server</span>
                </div>
              </div>
              <p className="pipeline-code">message · author · channel · time · permalink</p>
            </Reveal>

            <div className="pipeline-arrow">
              <span>Apify Dataset API</span>
              <ArrowRight size={22} />
            </div>

            <Reveal className="pipeline-gate" delay={0.07}>
              <div className="pipeline-node-title">
                <ShieldCheck size={21} weight="fill" />
                <div>
                  <p>Scope gate</p>
                  <span>server-side authorization</span>
                </div>
              </div>
              <div className="gate-checks">
                <span><Check size={12} /> map channel</span>
                <span><Check size={12} /> compute membership</span>
                <span><Check size={12} /> fail closed</span>
              </div>
            </Reveal>

            <div className="pipeline-arrow">
              <span>confirm</span>
              <ArrowRight size={22} />
            </div>

            <Reveal className="pipeline-memory" delay={0.14}>
              <div className="pipeline-node-title">
                <Brain size={21} weight="fill" />
                <div>
                  <p>Hindsight</p>
                  <span>one bank per scope</span>
                </div>
              </div>
              <div className="memory-banks">
                {["user:01862", "team:T004", "group:G10", "room:D302", "cohort:K4"].map(
                  (bank) => <code key={bank}>{bank}</code>,
                )}
              </div>
            </Reveal>
          </div>

          <Reveal className="architecture-note">
            <Database size={18} />
            <p>
              Actor output có thể thay đổi field. Adapter chuẩn hóa schema trước khi dữ liệu chạm vào memory layer.
            </p>
          </Reveal>
        </div>
      </section>

      <section id="demo" className="pitch-section demo-section">
        <div className="pitch-container section-pad">
          <Reveal className="demo-heading">
            <div>
              <SectionLabel>Live demo</SectionLabel>
              <h2 className="section-title mt-5">Ba câu hỏi. Một context graph.</h2>
            </div>
            <div className="demo-script">
              {[
                "Tóm tắt bài giảng ngày hôm qua",
                "Team mình đang chốt gì?",
                "Mentor G10 dặn gì?",
              ].map((text) => (
                <p key={text}><Sparkle size={13} weight="fill" /> {text}</p>
              ))}
            </div>
          </Reveal>
          <Reveal className="demo-stage" delay={0.08}>
            <ChatShell compact />
          </Reveal>
          <Reveal className="mt-6 flex justify-center">
            <Link href="/chat" className="button">
              Mở demo toàn màn hình
              <ArrowRight size={17} weight="bold" />
            </Link>
          </Reveal>
        </div>
      </section>

      <section id="trust" className="pitch-section">
        <div className="pitch-container section-pad">
          <Reveal>
            <SectionLabel>Trust boundary</SectionLabel>
            <h2 className="section-title mt-5 max-w-5xl">
              Không hỏi user được xem gì. Tự tính từ membership.
            </h2>
          </Reveal>

          <div className="trust-layout">
            <Reveal className="access-example">
              <div className="access-subject">
                <span className="identity-avatar identity-avatar-small">AN</span>
                <div>
                  <p className="font-bold">Thái Hoài An</p>
                  <p className="text-xs text-muted">U01862</p>
                </div>
              </div>
              <div className="access-path">
                {[
                  ["Identity", "U01862"],
                  ["Membership", "T004 · G10 · D302 · D304 · K4"],
                  ["Allowed banks", "6 scope keys"],
                  ["Recall", "all_strict"],
                ].map(([label, value], index) => (
                  <div key={label} className="access-step">
                    <span>{index + 1}</span>
                    <div>
                      <p>{label}</p>
                      <code>{value}</code>
                    </div>
                  </div>
                ))}
              </div>
            </Reveal>

            <div className="trust-rules">
              {[
                {
                  icon: LockKey,
                  title: "Không đọc chéo team",
                  text: "T004 không bao giờ nhận message hoặc memory của T009.",
                },
                {
                  icon: Eye,
                  title: "Luôn chỉ ra nguồn",
                  text: "Mỗi ý tóm tắt giữ permalink quay lại message Discord gốc.",
                },
                {
                  icon: User,
                  title: "Con người xác nhận",
                  text: "Chat evidence không tự động trở thành quyết định dài hạn.",
                },
              ].map((rule, index) => (
                <Reveal key={rule.title} className="trust-rule" delay={index * 0.07}>
                  <rule.icon size={22} weight="duotone" />
                  <div>
                    <h3>{rule.title}</h3>
                    <p>{rule.text}</p>
                  </div>
                </Reveal>
              ))}
            </div>
          </div>

          <Reveal className="guardrail-strip">
            <p>Guardrail của MVP</p>
            <div>
              <span><strong>0</strong> cross-team leaks</span>
              <span><strong>100%</strong> summary có citation</span>
              <span><strong>1</strong> click để confirm memory</span>
            </div>
          </Reveal>
        </div>
      </section>

      <section id="next" className="pitch-section close-section">
        <div className="pitch-container close-layout">
          <Reveal>
            <SectionLabel>Kết quả sau 24 giờ</SectionLabel>
            <h2 className="close-title mt-6">
              Mentor bớt trả lời lại.
              <span className="text-accent-strong"> Học viên không mất dấu.</span>
            </h2>
            <p className="section-copy mt-6 max-w-2xl">
              Một trợ lý dùng được ngay trong workflow hiện có, không bắt lớp chuyển sang thêm một ứng dụng.
            </p>
            <Link href="/chat" className="button mt-8">
              Pitch bằng demo thật
              <ArrowRight size={17} weight="bold" />
            </Link>
          </Reveal>

          <Reveal className="roadmap" delay={0.08}>
            <p className="context-fragment-title">Nếu có thêm một tuần</p>
            {[
              ["Discord bot", "Thay polling bằng bot event được server cấp quyền."],
              ["Memory review", "Mentor duyệt memory group và cohort theo batch."],
              ["Impact eval", "Đo thời gian mentor tiết kiệm và tỷ lệ câu hỏi tự phục vụ."],
            ].map(([title, text], index) => (
              <div key={title} className="roadmap-item">
                <span>{String(index + 1).padStart(2, "0")}</span>
                <div>
                  <h3>{title}</h3>
                  <p>{text}</p>
                </div>
              </div>
            ))}
          </Reveal>
        </div>
      </section>
    </main>
  );
}
