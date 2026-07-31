"use client";

import {
  ArrowClockwise,
  ArrowRight,
  ArrowUpRight,
  CalendarBlank,
  Check,
  CheckCircle,
  CirclesThreePlus,
  Clock,
  Database,
  DiscordLogo,
  FlowArrow,
  Kanban,
  LockKey,
  PlugsConnected,
  Robot,
  ShieldCheck,
  Sparkle,
  Target,
  UserCircleCheck,
  UsersThree,
  WarningCircle,
  X,
} from "@phosphor-icons/react";
import { motion, useReducedMotion } from "motion/react";
import Image from "next/image";
import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";

import { Logo } from "./logo";
import { ThemeToggle } from "./theme-toggle";
import styles from "./landing-page.module.css";

type SyncState = "idle" | "syncing" | "synced" | "dismissed" | "error";

const revealEase = [0.16, 1, 0.3, 1] as const;

function Reveal({
  children,
  className,
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
}) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      className={className}
      initial={reduceMotion ? false : { y: 24 }}
      whileInView={{ y: 0 }}
      viewport={{ once: true, amount: 0.18 }}
      transition={{ duration: 0.65, delay, ease: revealEase }}
    >
      {children}
    </motion.div>
  );
}

function LandingNav() {
  return (
    <header className={styles.navShell}>
      <div className={styles.navInner}>
        <Logo />
        <nav className={styles.navLinks} aria-label="Điều hướng landing page">
          <a href="#problem">Vấn đề</a>
          <a href="#demo">Demo</a>
          <a href="#architecture">Kiến trúc</a>
          <a href="#evidence">Bằng chứng</a>
        </nav>
        <div className={styles.navActions}>
          <ThemeToggle />
          <Link href="/chat" className={styles.navCta}>
            Chạy demo
            <ArrowRight size={16} weight="bold" />
          </Link>
        </div>
      </div>
    </header>
  );
}

function ActionItemDemo() {
  const [state, setState] = useState<SyncState>("idle");
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    if (state !== "syncing") return;
    const timer = window.setTimeout(() => setState("synced"), reduceMotion ? 80 : 900);
    return () => window.clearTimeout(timer);
  }, [reduceMotion, state]);

  if (state === "dismissed") {
    return (
      <div className={styles.demoEmpty} aria-live="polite">
        <span className={styles.demoEmptyIcon}>
          <X size={22} weight="bold" />
        </span>
        <div>
          <h3>Không có task nào được tạo</h3>
          <p>Candidate đã bị bỏ qua. ZicZord không tự ghi sang công cụ ngoài.</p>
        </div>
        <button type="button" onClick={() => setState("idle")} className={styles.textButton}>
          <ArrowClockwise size={16} weight="bold" />
          Thử lại
        </button>
      </div>
    );
  }

  return (
    <div className={styles.productDemo}>
      <div className={styles.demoTopbar}>
        <div className={styles.demoChannel}>
          <DiscordLogo size={21} weight="fill" />
          <div>
            <strong>#gõ-commands</strong>
            <span>Team T004</span>
          </div>
        </div>
        <span className={styles.liveState}>
          <span />
          Agent đang nghe
        </span>
      </div>

      <div className={styles.demoConversation}>
        <div className={styles.messageAvatar}>A</div>
        <div className={styles.messageBody}>
          <p className={styles.messageMeta}>
            <strong>An</strong>
            <span>09:42</span>
          </p>
          <p>@Tuấn deploy backend trước tối mai nhé</p>
        </div>
      </div>

      <div className={styles.agentReply}>
        <div className={styles.agentHeading}>
          <span className={styles.agentAvatar}>
            <Robot size={18} weight="duotone" />
          </span>
          <div>
            <strong>ZicZord</strong>
            <span>Đã tìm thấy action item</span>
          </div>
          <span className={styles.confidence}>high confidence</span>
        </div>

        <div className={styles.candidateGrid}>
          <div>
            <span>Việc cần làm</span>
            <strong>Deploy backend</strong>
          </div>
          <div>
            <span>Owner</span>
            <strong>Tuấn</strong>
          </div>
          <div>
            <span>Deadline</span>
            <strong>Tối mai</strong>
          </div>
          <div>
            <span>Scope</span>
            <strong>Team T004</strong>
          </div>
        </div>

        {state === "synced" ? (
          <div className={styles.syncedState} aria-live="polite">
            <CheckCircle size={22} weight="fill" />
            <div>
              <strong>Đã tạo issue trong Jira sandbox</strong>
              <span>Candidate được lưu cùng nguồn Discord để truy vết.</span>
            </div>
            <a href="#architecture" aria-label="Xem kiến trúc connector">
              K4-128
              <ArrowUpRight size={14} weight="bold" />
            </a>
          </div>
        ) : state === "error" ? (
          <div className={styles.errorState} role="alert">
            <WarningCircle size={22} weight="fill" />
            <div>
              <strong>Jira connector chưa phản hồi</strong>
              <span>Candidate vẫn được giữ. Retry không tạo task trùng.</span>
            </div>
            <button type="button" onClick={() => setState("idle")}>
              Thử lại
            </button>
          </div>
        ) : (
          <div className={styles.demoActions}>
            <button
              type="button"
              onClick={() => setState("syncing")}
              disabled={state === "syncing"}
              className={styles.syncButton}
            >
              {state === "syncing" ? (
                <>
                  <span className={styles.syncingMark} aria-hidden="true" />
                  Đang đồng bộ
                </>
              ) : (
                <>
                  <Kanban size={17} weight="fill" />
                  Đồng bộ Jira
                </>
              )}
            </button>
            <button
              type="button"
              onClick={() => setState("dismissed")}
              disabled={state === "syncing"}
              className={styles.dismissButton}
            >
              Bỏ qua
            </button>
          </div>
        )}
      </div>

      <div className={styles.demoFooter}>
        <ShieldCheck size={16} weight="fill" />
        Chỉ user có quyền trong T004 mới được xác nhận
        <button type="button" onClick={() => setState("error")}>
          Test fallback
        </button>
      </div>
    </div>
  );
}

const architectureSteps = [
  {
    icon: DiscordLogo,
    title: "Discord",
    detail: "Message, member, channel",
  },
  {
    icon: Robot,
    title: "Action agent",
    detail: "Task, owner, deadline",
  },
  {
    icon: PlugsConnected,
    title: "MCP tools",
    detail: "Connector có schema",
  },
  {
    icon: Kanban,
    title: "Jira",
    detail: "Issue sau xác nhận",
  },
];

export function LandingPage() {
  const reduceMotion = useReducedMotion();

  return (
    <main className={styles.root}>
      <LandingNav />

      <section className={styles.hero} id="home">
        <div className={styles.heroGrid}>
          <motion.div
            className={styles.heroCopy}
            initial={reduceMotion ? false : { y: 28 }}
            animate={{ y: 0 }}
            transition={{ duration: 0.75, ease: revealEase }}
          >
            <span className={styles.eyebrow}>
              <DiscordLogo size={15} weight="fill" />
              Discord Action Copilot
            </span>
            <h1>
              Chat Discord.
              <span>Task đã chốt.</span>
            </h1>
            <p>
              ZicZord đề xuất owner, deadline và đồng bộ Jira sau một lần xác nhận.
            </p>
            <div className={styles.heroActions}>
              <Link href="/chat" className={styles.primaryCta}>
                Chạy demo
                <ArrowRight size={18} weight="bold" />
              </Link>
              <a href="#demo" className={styles.secondaryCta}>
                Xem cách chạy
              </a>
            </div>
          </motion.div>

          <motion.div
            className={styles.heroVisual}
            initial={reduceMotion ? false : { scale: 0.97, x: 28 }}
            animate={{ scale: 1, x: 0 }}
            transition={{ duration: 0.85, delay: 0.08, ease: revealEase }}
          >
            <div className={styles.heroImageFrame}>
              <Image
                src="/images/ziczord-mcp-workflow.png"
                alt="Luồng hội thoại được MCP chuyển thành task có owner và trạng thái"
                width={1448}
                height={1086}
                sizes="(max-width: 860px) 100vw, 52vw"
                preload
              />
            </div>
            <div className={styles.heroVisualLabel}>
              <span>
                <CirclesThreePlus size={17} weight="duotone" />
                MCP tool layer
              </span>
              <strong>Human-confirmed sync</strong>
            </div>
          </motion.div>
        </div>
      </section>

      <section className={styles.signalBand} aria-label="Bằng chứng validation">
        <div className={styles.signalInner}>
          <div>
            <strong>5/5</strong>
            <span>xác nhận Discord thiếu task flow</span>
          </div>
          <div>
            <strong>3/5</strong>
            <span>sẵn sàng dùng thử bot</span>
          </div>
          <div>
            <strong>22</strong>
            <span>case trong golden set</span>
          </div>
          <div>
            <strong>0</strong>
            <span>auto-write khi chưa confirm</span>
          </div>
        </div>
      </section>

      <section className={styles.problemSection} id="problem">
        <div className={styles.sectionInner}>
          <Reveal className={styles.problemIntro}>
            <h2>Cuộc trò chuyện xong. Việc cần làm thì thất lạc.</h2>
            <p>
              Team phải copy task từ Discord sang Sheets, Trello hoặc Jira. Context bị đứt
              ngay tại khoảnh khắc cần hành động.
            </p>
          </Reveal>

          <div className={styles.evidenceComposition}>
            <Reveal className={styles.interviewPhoto}>
              <div className={styles.interviewMedia}>
                <Image
                  src="/images/duong-duc-minh.jpg"
                  alt="Buổi phỏng vấn học viên K4 về cách theo dõi công việc nhóm"
                  fill
                  sizes="(max-width: 760px) 100vw, 38vw"
                />
              </div>
              <div className={styles.photoCaption}>
                <strong>Dương Đức Minh</strong>
                <span>Phỏng vấn người dùng K4</span>
              </div>
            </Reveal>

            <div className={styles.quoteStack}>
              <Reveal className={styles.primaryQuote} delay={0.05}>
                <Sparkle size={24} weight="fill" />
                <blockquote>
                  “Nếu mà sửa được luôn bên Jira thì ok.”
                </blockquote>
                <p>Tuấn, học viên đang dùng Discord và Sheets</p>
              </Reveal>
              <Reveal className={styles.secondaryQuote} delay={0.1}>
                <blockquote>
                  “Nếu làm được như thế thì tốt, mình sẽ sử dụng. Mình sẽ quay lại Discord.”
                </blockquote>
                <p>Lợi, học viên đang dùng Zalo</p>
              </Reveal>
            </div>
          </div>
        </div>
      </section>

      <section className={styles.demoSection} id="demo">
        <div className={styles.sectionInner}>
          <Reveal className={styles.demoIntro}>
            <span className={styles.sectionTag}>Live product moment</span>
            <h2>Một message. Một task. Không đổi tab.</h2>
            <p>
              Agent chỉ đề xuất. User kiểm tra owner, deadline và scope trước khi ghi ra
              công cụ của team.
            </p>
          </Reveal>
          <Reveal className={styles.demoCanvas} delay={0.08}>
            <div className={styles.demoAside}>
              <div>
                <span>Detect</span>
                <strong>Action intent</strong>
              </div>
              <FlowArrow size={20} weight="duotone" />
              <div>
                <span>Propose</span>
                <strong>Owner + deadline</strong>
              </div>
              <FlowArrow size={20} weight="duotone" />
              <div>
                <span>Confirm</span>
                <strong>Write once</strong>
              </div>
            </div>
            <ActionItemDemo />
          </Reveal>
          <p className={styles.demoDisclosure}>
            Jira đang ở chế độ prototype connector. Flow confirm và Google Calendar
            adapter đã có backend thật.
          </p>
        </div>
      </section>

      <section className={styles.architectureSection} id="architecture">
        <div className={styles.sectionInner}>
          <Reveal className={styles.architectureIntro}>
            <span className={styles.sectionTag}>MCP architecture</span>
            <h2>Đổi công cụ, không phải viết lại agent.</h2>
            <p>
              MCP tách reasoning khỏi connector. Jira hôm nay, Calendar hoặc Tasks ngày mai
              vẫn dùng cùng một contract.
            </p>
          </Reveal>

          <Reveal className={styles.architectureRail} delay={0.08}>
            {architectureSteps.map((step, index) => (
              <div className={styles.architectureStep} key={step.title}>
                <span className={styles.stepIcon}>
                  <step.icon size={24} weight={index === 0 ? "fill" : "duotone"} />
                </span>
                <div>
                  <h3>{step.title}</h3>
                  <p>{step.detail}</p>
                </div>
                {index < architectureSteps.length - 1 && (
                  <ArrowRight className={styles.stepArrow} size={20} weight="bold" />
                )}
              </div>
            ))}
          </Reveal>

          <div className={styles.architectureNotes}>
            <Reveal>
              <LockKey size={21} weight="duotone" />
              <h3>Fail closed</h3>
              <p>Không map được membership thì không đọc và không ghi.</p>
            </Reveal>
            <Reveal delay={0.05}>
              <Database size={21} weight="duotone" />
              <h3>Idempotent write</h3>
              <p>Retry connector không tạo trùng task từ cùng candidate.</p>
            </Reveal>
            <Reveal delay={0.1}>
              <UserCircleCheck size={21} weight="duotone" />
              <h3>Human gate</h3>
              <p>Câu đùa, sai owner hoặc deadline mơ hồ đều dừng trước write.</p>
            </Reveal>
          </div>
        </div>
      </section>

      <section className={styles.capabilitySection}>
        <div className={styles.sectionInner}>
          <Reveal className={styles.capabilityIntro}>
            <h2>Mọi thứ team cần, nằm đúng nơi team đang nói chuyện.</h2>
          </Reveal>

          <div
            className={styles.capabilityGrid}
            tabIndex={0}
            role="region"
            aria-label="Các năng lực chính của ZicZord"
          >
            <Reveal className={`${styles.capabilityCell} ${styles.capabilityDiscord}`}>
              <DiscordLogo size={31} weight="fill" />
              <div>
                <h3>Discord-native</h3>
                <p>Đề xuất task ngay dưới message nguồn, không mở thêm app.</p>
              </div>
            </Reveal>

            <Reveal
              className={`${styles.capabilityCell} ${styles.capabilityMcp}`}
              delay={0.04}
            >
              <PlugsConnected size={30} weight="duotone" />
              <div>
                <h3>MCP-ready tools</h3>
                <p>Connector có schema rõ, dễ thay Jira, Calendar hoặc task service.</p>
              </div>
              <div className={styles.toolConstellation} aria-hidden="true">
                <span>discord.read</span>
                <span>task.propose</span>
                <span>jira.create</span>
              </div>
            </Reveal>

            <Reveal
              className={`${styles.capabilityCell} ${styles.capabilityTrust}`}
              delay={0.08}
            >
              <ShieldCheck size={29} weight="duotone" />
              <div>
                <h3>Scope-safe</h3>
                <p>Membership quyết định dữ liệu user được đọc và được ghi.</p>
              </div>
            </Reveal>

            <Reveal
              className={`${styles.capabilityCell} ${styles.capabilityMemory}`}
              delay={0.12}
            >
              <Database size={29} weight="duotone" />
              <div>
                <h3>Memory có nguồn</h3>
                <p>Mỗi action item giữ permalink về message Discord gốc.</p>
              </div>
            </Reveal>

            <Reveal
              className={`${styles.capabilityCell} ${styles.capabilityTeam}`}
              delay={0.16}
            >
              <UsersThree size={31} weight="duotone" />
              <div>
                <h3>Quản lý đội nhóm</h3>
                <p>Owner, deadline, decision và blocker cùng nằm trong team scope.</p>
              </div>
            </Reveal>
          </div>
        </div>
      </section>

      <section className={styles.evidenceSection} id="evidence">
        <div className={styles.sectionInner}>
          <Reveal className={styles.evidenceHeader}>
            <Target size={36} weight="duotone" />
            <h2>Pitch bằng bằng chứng, không bằng lời hứa.</h2>
          </Reveal>

          <div className={styles.evidenceGrid}>
            <Reveal className={styles.evidenceLead}>
              <strong>100%</strong>
              <h3>người được phỏng vấn xác nhận pain</h3>
              <p>
                5 trên 5 học viên nói Discord đang thiếu một flow quản lý task đủ gần với
                cách team làm việc.
              </p>
            </Reveal>
            <Reveal className={styles.evidenceList} delay={0.06}>
              <div>
                <Check size={18} weight="bold" />
                <p>
                  <strong>Validation thật</strong>
                  5 transcript có quote và bối cảnh sử dụng.
                </p>
              </div>
              <div>
                <Check size={18} weight="bold" />
                <p>
                  <strong>Golden set</strong>
                  22 case gồm noise, ambiguity và cross-team.
                </p>
              </div>
              <div>
                <Check size={18} weight="bold" />
                <p>
                  <strong>Prototype thật</strong>
                  API, scoped memory và Calendar adapter chạy được.
                </p>
              </div>
            </Reveal>
            <Reveal className={styles.qualityBar} delay={0.12}>
              <Clock size={25} weight="duotone" />
              <div>
                <span>North-star moment</span>
                <strong>Message đến task trong một lần xác nhận</strong>
              </div>
              <CalendarBlank size={25} weight="duotone" />
            </Reveal>
          </div>
        </div>
      </section>

      <section className={styles.finalSection}>
        <div className={styles.finalInner}>
          <Reveal className={styles.finalCopy}>
            <h2>Đừng bắt team rời Discord để hoàn thành việc bắt đầu trong Discord.</h2>
            <p>ZicZord biến hội thoại thành hành động, có quyền hạn và có con người kiểm tra.</p>
            <Link href="/chat" className={styles.primaryCta}>
              Chạy demo
              <ArrowRight size={18} weight="bold" />
            </Link>
          </Reveal>
          <Reveal className={styles.finalMark} delay={0.08}>
            <span>Z</span>
            <div>
              <strong>ZicZord</strong>
              <p>Discord Action Copilot</p>
            </div>
          </Reveal>
        </div>
      </section>

      <footer className={styles.footer}>
        <Logo />
        <p>Built for Mini-Hackathon K4 by Team ZicZord.</p>
        <div>
          <a href="#home">Về đầu trang</a>
          <Link href="/admin">Evaluation</Link>
        </div>
      </footer>
    </main>
  );
}
