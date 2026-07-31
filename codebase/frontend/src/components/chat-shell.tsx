"use client";

import {
  ArrowClockwise,
  ArrowSquareOut,
  ArrowUp,
  Brain,
  CalendarBlank,
  CaretDown,
  Check,
  GlobeSimple,
  Hash,
  IdentificationCard,
  LockKey,
  MagnifyingGlass,
  ShieldCheck,
  Sparkle,
  Trash,
  UsersThree,
  X,
} from "@phosphor-icons/react";
import { AnimatePresence, motion } from "motion/react";
import { FormEvent, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";

import {
  addCandidateToGoogleCalendar,
  confirmCandidate,
  createCatchup,
  createGoogleTaskFromBrief,
  createLearnerProfile,
  createTeamBrief,
  deleteMemory,
  dismissCandidate,
  getDiscordState,
  getLearnerProfile,
  loadT004PitchContext,
  resetDemo,
  sendChat,
} from "@/lib/api";
import type {
  AssistantMessage,
  CatchupBrief,
  CatchupItem,
  DiscordMessage,
  DiscordState,
  GoogleTaskResponse,
  LearnerProfile,
  Memory,
  MemoryCandidate,
  ScopeType,
} from "@/lib/types";
import { ZicZordAvatar } from "./ziczord-avatar";

const PROFILE_STORAGE_KEY = "kute-learner-profile-id";

const MEMORY_LABELS = {
  decision: "Quyết định",
  task: "Việc cần làm",
  blocker: "Blocker",
  preference: "Sở thích",
  learning_note: "Bài học",
};

const SCOPE_LABELS: Record<ScopeType, string> = {
  user: "Cá nhân",
  team: "Team",
  group: "Group",
  room: "Phòng học",
  cohort: "Cộng đồng",
};

const BRIEF_LABELS = {
  decision: "Quyết định",
  task: "Việc cần làm",
  blocker: "Blocker",
  announcement: "Thông báo",
};
const googleTasksLive =
  process.env.NEXT_PUBLIC_GOOGLE_TASKS_MODE === "live";

function initials(name: string) {
  return name
    .split(/[\s-]+/)
    .filter(Boolean)
    .slice(-2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function MarkdownMessage({ content }: { content: string }) {
  return (
    <div className="message-markdown">
      <ReactMarkdown
        skipHtml
        components={{
          a({ href, children }) {
            return (
              <a href={href} target="_blank" rel="noreferrer">
                {children}
              </a>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="grid h-full place-items-center p-8" role="status">
      <div className="w-full max-w-md space-y-4">
        <div className="skeleton h-5 w-32" />
        <div className="skeleton h-20 w-4/5" />
        <div className="skeleton h-24 w-11/12" />
      </div>
      <span className="sr-only">Đang đồng bộ Discord snapshot</span>
    </div>
  );
}

function LearnerGate({
  checking,
  submitting,
  error,
  onSubmit,
}: {
  checking: boolean;
  submitting: boolean;
  error: string | null;
  onSubmit: (fullName: string, studentIdLast5: string) => Promise<void>;
}) {
  const [fullName, setFullName] = useState("");
  const [studentIdLast5, setStudentIdLast5] = useState("");

  async function submitProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSubmit(fullName.trim(), studentIdLast5);
  }

  return (
    <section className="learner-gate" aria-labelledby="learner-gate-title">
      <div className="learner-onboarding">
        <span className="learner-onboarding-mark" aria-hidden="true">
          <IdentificationCard size={25} weight="duotone" />
        </span>
        {checking ? (
          <div role="status">
            <p className="eyebrow text-accent-strong">Trợ lý ZicZord</p>
            <h1 id="learner-gate-title">Đang nhận diện bạn</h1>
            <p className="learner-onboarding-copy">
              ZicZord đang kiểm tra thông tin đã lưu trên thiết bị này.
            </p>
            <div className="learner-loading-lines" aria-hidden="true">
              <span className="skeleton" />
              <span className="skeleton" />
            </div>
            <span className="sr-only">Đang kiểm tra hồ sơ học viên</span>
          </div>
        ) : (
          <>
            <p className="eyebrow text-accent-strong">Trước khi bắt đầu</p>
            <h1 id="learner-gate-title">Bạn là ai trong lớp?</h1>
            <p className="learner-onboarding-copy">
              Thông tin này chỉ dùng để liên kết log hỏi đáp và cải thiện ZicZord.
            </p>
            <form className="learner-form" onSubmit={submitProfile}>
              <label className="learner-field">
                <span>Họ và tên</span>
                <input
                  name="full_name"
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  autoComplete="name"
                  minLength={2}
                  maxLength={100}
                  required
                />
              </label>
              <label className="learner-field">
                <span>5 số cuối mã sinh viên</span>
                <input
                  name="student_id_last5"
                  value={studentIdLast5}
                  onChange={(event) =>
                    setStudentIdLast5(event.target.value.replace(/\D/g, "").slice(0, 5))
                  }
                  inputMode="numeric"
                  autoComplete="off"
                  pattern="[0-9]{5}"
                  maxLength={5}
                  required
                />
                <small>Không nhập toàn bộ mã sinh viên.</small>
              </label>
              {error && (
                <p className="learner-form-error" role="alert">
                  {error}
                </p>
              )}
              <button type="submit" className="button learner-submit" disabled={submitting}>
                {submitting ? "Đang lưu thông tin" : "Vào phòng chat"}
                {!submitting && <ArrowUp size={16} weight="bold" />}
              </button>
            </form>
            <p className="learner-privacy">
              <LockKey size={13} />
              Chỉ lưu họ tên, 5 số cuối và nội dung hỏi đáp.
            </p>
          </>
        )}
      </div>
    </section>
  );
}

function CandidateCard({
  candidate,
  onAddToCalendar,
  onConfirm,
  onDismiss,
  busy,
}: {
  candidate: MemoryCandidate;
  onAddToCalendar: () => void;
  onConfirm: () => void;
  onDismiss: () => void;
  busy: boolean;
}) {
  const calendarEvent = candidate.calendar_event;
  const calendarSchedule = calendarEvent
    ? calendarEvent.all_day && calendarEvent.start_date
      ? `Cả ngày · ${calendarEvent.start_date.split("-").reverse().join("/")}`
      : calendarEvent.start_at
        ? new Intl.DateTimeFormat("vi-VN", {
            dateStyle: "medium",
            timeStyle: "short",
            timeZone: calendarEvent.time_zone,
          }).format(new Date(calendarEvent.start_at))
        : null
    : null;

  return (
    <motion.aside
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      className="memory-proposal"
    >
      <span className="proposal-icon">
        {calendarEvent ? (
          <CalendarBlank size={17} weight="fill" />
        ) : (
          <Brain size={17} weight="fill" />
        )}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="eyebrow text-accent-strong">
            {calendarEvent ? "Đề xuất Google Calendar" : "Đề xuất memory"}
          </p>
          <span className="scope-chip scope-chip-team">
            {SCOPE_LABELS[candidate.scope_type]} · {candidate.scope_id}
          </span>
        </div>
        <p className="mt-2 text-sm font-semibold leading-6">
          {calendarEvent?.summary ?? candidate.content}
        </p>
        {calendarSchedule && (
          <p className="mt-1 flex items-center gap-1.5 text-xs text-muted">
            <CalendarBlank size={13} weight="bold" />
            {calendarSchedule} · {calendarEvent?.time_zone}
          </p>
        )}
        {calendarEvent?.attendee_email ? (
          <p className="mt-1 text-xs text-muted">
            Lời mời: {calendarEvent.attendee_email}
          </p>
        ) : calendarEvent ? (
          <p className="mt-1 text-xs text-muted">
            Đang chờ email Google Calendar trong khung chat.
          </p>
        ) : null}
        <p className="mt-1 text-xs text-muted">
          {calendarEvent
            ? calendarEvent.attendee_email
              ? "Email đã được xác nhận; bạn có thể thử gửi lại nếu connector vừa lỗi."
              : "Trả lời email ở tin nhắn tiếp theo để agent gửi invitation."
            : "Chỉ trở thành memory dài hạn sau khi bạn xác nhận."}
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {calendarEvent?.attendee_email && (
            <button
              type="button"
              onClick={onAddToCalendar}
              disabled={busy}
              className="button button-small"
            >
              <CalendarBlank size={15} weight="bold" />
              {busy ? "Đang gửi lời mời" : "Thử gửi lại lời mời"}
            </button>
          )}
          <button
            type="button"
            onClick={onConfirm}
            disabled={busy}
            className={
              calendarEvent
                ? "button-secondary button-small"
                : "button button-small"
            }
          >
            <Check size={15} weight="bold" />
            {busy
              ? "Đang lưu"
              : calendarEvent
                ? "Chỉ lưu memory"
                : "Xác nhận đúng scope"}
          </button>
          <button
            type="button"
            onClick={onDismiss}
            className="button-secondary button-small"
          >
            Bỏ qua
          </button>
        </div>
      </div>
      <button
        type="button"
        onClick={onDismiss}
        className="icon-button size-8"
        aria-label="Bỏ đề xuất memory"
        title="Bỏ qua"
      >
        <X size={15} />
      </button>
    </motion.aside>
  );
}

function AssistantTurn({ message }: { message: AssistantMessage }) {
  const assistant = message.role === "assistant";
  const displayAuthor = assistant ? "Trợ lý ZicZord" : message.author_name;
  return (
    <motion.article
      initial={{ opacity: 0, y: 7 }}
      animate={{ opacity: 1, y: 0 }}
      className="discord-turn"
    >
      {assistant ? (
        <ZicZordAvatar />
      ) : (
        <span className="avatar avatar-user">{initials(message.author_name)}</span>
      )}
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
          <p className={assistant ? "message-author text-accent-strong" : "message-author"}>
            {displayAuthor}
          </p>
          {assistant && <span className="bot-badge">APP</span>}
          <time className="message-time">vừa xong</time>
        </div>
        {assistant ? (
          <MarkdownMessage content={message.content} />
        ) : (
          <p className="mt-1 whitespace-pre-line text-sm leading-6 text-ink/88">
            {message.content}
          </p>
        )}
        {message.citations.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {message.citations.map((citation) => {
              const webSource = citation.channel_id === "web";
              return (
                <a
                  key={citation.message_id}
                  href={citation.permalink}
                  target="_blank"
                  rel="noreferrer"
                  className="citation-chip"
                  title={webSource ? "Mở nguồn web" : "Mở tin nhắn nguồn trên Discord"}
                >
                  {webSource ? (
                    <GlobeSimple size={12} weight="bold" />
                  ) : (
                    <Hash size={12} weight="bold" />
                  )}
                  {citation.channel_name}
                  <ArrowSquareOut size={11} />
                </a>
              );
            })}
          </div>
        )}
      </div>
    </motion.article>
  );
}

function SourceMessage({ message }: { message: DiscordMessage }) {
  return (
    <article className="discord-turn">
      <span className="avatar avatar-user">{initials(message.author_name)}</span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline gap-x-2">
          <p className="message-author">{message.author_name}</p>
          <time className="message-time">
            {new Intl.DateTimeFormat("vi-VN", {
              hour: "2-digit",
              minute: "2-digit",
            }).format(new Date(message.created_at))}
          </time>
        </div>
        <p className="mt-1 text-sm leading-6 text-ink/88">{message.content}</p>
      </div>
    </article>
  );
}

function MemoryCard({
  memory,
  onDelete,
  canDelete,
}: {
  memory: Memory;
  onDelete: () => void;
  canDelete: boolean;
}) {
  return (
    <article className="memory-card">
      <div className="flex items-center justify-between gap-2">
        <span className={`scope-chip scope-chip-${memory.scope_type}`}>
          {SCOPE_LABELS[memory.scope_type]} · {memory.scope_id}
        </span>
        {canDelete && (
          <button
            type="button"
            onClick={onDelete}
            className="icon-button size-7 opacity-60 hover:opacity-100"
            aria-label={`Xóa memory: ${memory.content}`}
            title="Xóa memory"
          >
            <Trash size={13} />
          </button>
        )}
      </div>
      <p className="mt-3 text-sm leading-5">{memory.content}</p>
      <div className="mt-3 flex items-center justify-between gap-2 text-[11px] text-muted">
        <span>{MEMORY_LABELS[memory.kind]}</span>
        <span className="flex items-center gap-1">
          <Check size={11} weight="bold" className="text-accent-strong" />
          Confirmed
        </span>
      </div>
    </article>
  );
}

function TeamBriefPanel({
  brief,
  syncedTasks,
  busyItemId,
  onCreateTask,
  mode = "pitch",
}: {
  brief: CatchupBrief;
  syncedTasks: Record<string, GoogleTaskResponse>;
  busyItemId: string | null;
  onCreateTask?: (item: CatchupItem) => void;
  mode?: "pitch" | "catchup";
}) {
  const isCatchup = mode === "catchup";
  return (
    <motion.section
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-4 mb-5 overflow-hidden rounded-2xl border border-line bg-surface/70"
      aria-labelledby="team-brief-title"
    >
      <header className="flex flex-wrap items-start justify-between gap-3 border-b border-line px-4 py-4">
        <div>
          <p className="eyebrow text-accent-strong">
            {isCatchup ? "Bản cập nhật có nguồn" : "Brief thật từ context mock"}
          </p>
          <h3 id="team-brief-title" className="mt-1 text-base font-bold">
            {isCatchup ? "Bạn cần biết · 24 giờ qua" : "Team T004 · 24 giờ qua"}
          </h3>
          <p className="mt-1 text-xs text-muted">
            {brief.summary} · {brief.source_message_count} nguồn · {brief.provider}
          </p>
          {!isCatchup && (
            <p
              className={`mt-2 text-xs font-semibold ${
                googleTasksLive ? "text-accent-strong" : "text-danger"
              }`}
            >
              {googleTasksLive
                ? "Google Tasks live · thao tác xác nhận sẽ ghi vào tài khoản Google."
                : "Pitch-mock · thao tác xác nhận chỉ tạo bản nháp demo, chưa ghi vào tài khoản Google."}
            </p>
          )}
        </div>
        <span className="safe-badge">
          <ShieldCheck size={13} weight="fill" />
          {brief.scope_key} only
        </span>
      </header>
      <div className="space-y-3 p-4">
        {brief.items.length === 0 && (
          <p className="rounded-xl border border-line bg-paper p-4 text-sm text-muted">
            Chưa có quyết định, task, blocker hoặc thông báo đủ bằng chứng trong cửa sổ này.
          </p>
        )}
        {brief.items.map((item) => {
          const synced = syncedTasks[item.id];
          const actionable = item.kind === "task" || item.kind === "blocker";
          return (
            <article
              key={item.id}
              className="rounded-xl border border-line bg-paper p-3.5"
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="scope-chip scope-chip-team">
                  {BRIEF_LABELS[item.kind]}
                </span>
                {item.owner && (
                  <span className="text-[11px] font-semibold text-muted">
                    Owner · {item.owner}
                  </span>
                )}
                {item.deadline && (
                  <span className="flex items-center gap-1 text-[11px] font-semibold text-danger">
                    <CalendarBlank size={12} weight="bold" />
                    {item.deadline}
                  </span>
                )}
              </div>
              <p className="mt-2 text-sm font-bold leading-5">{item.title}</p>
              <p className="mt-1 text-xs leading-5 text-muted">{item.detail}</p>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                {item.citations.map((citation) => (
                  <a
                    key={citation.message_id}
                    href={citation.permalink}
                    target="_blank"
                    rel="noreferrer"
                    className="citation-chip"
                  >
                    <Hash size={12} weight="bold" />
                    #{citation.channel_name}
                    <ArrowSquareOut size={11} />
                  </a>
                ))}
                {actionable && onCreateTask && !synced && (
                  <button
                    type="button"
                    className="button button-small ml-auto"
                    onClick={() => onCreateTask(item)}
                    disabled={busyItemId !== null}
                  >
                    <Check size={14} weight="bold" />
                    {busyItemId === item.id
                      ? "Đang tạo task"
                      : googleTasksLive
                        ? "Xác nhận & tạo Google Task"
                        : "Xác nhận & tạo bản nháp"}
                  </button>
                )}
                {synced && (
                  <a
                    href={synced.html_link}
                    target="_blank"
                    rel="noreferrer"
                    className="button-secondary button-small ml-auto"
                  >
                    <Check size={14} weight="bold" />
                    {synced.provider === "google-tasks"
                      ? "Đã tạo Google Task"
                      : "Đã tạo pitch-mock"}
                    <ArrowSquareOut size={12} />
                  </a>
                )}
              </div>
            </article>
          );
        })}
      </div>
    </motion.section>
  );
}

export function ChatShell({ compact = false }: { compact?: boolean }) {
  const [state, setState] = useState<DiscordState | null>(null);
  const [profile, setProfile] = useState<LearnerProfile | null>(null);
  const [profileChecking, setProfileChecking] = useState(!compact);
  const [profileSubmitting, setProfileSubmitting] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [activeUser, setActiveUser] = useState("U01862");
  const [activeChannel, setActiveChannel] = useState("bot-commands");
  const [input, setInput] = useState("");
  const [candidate, setCandidate] = useState<MemoryCandidate | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [memoryBusy, setMemoryBusy] = useState(false);
  const [pitchBrief, setPitchBrief] = useState<CatchupBrief | null>(null);
  const [catchupBrief, setCatchupBrief] = useState<CatchupBrief | null>(null);
  const [pitchBusy, setPitchBusy] = useState(false);
  const [taskBusyItemId, setTaskBusyItemId] = useState<string | null>(null);
  const [syncedTasks, setSyncedTasks] = useState<
    Record<string, GoogleTaskResponse>
  >({});
  const [error, setError] = useState<string | null>(null);
  const threadRef = useRef<HTMLDivElement>(null);
  const optimisticCounter = useRef(0);

  const currentChannel = state?.channels.find((channel) => channel.id === activeChannel);
  const sourceMessages =
    state?.discord_messages.filter((message) => message.channel_id === activeChannel) ?? [];
  const channelGroups = Array.from(new Set(state?.channels.map((channel) => channel.category) ?? []));

  async function reload(userId: string) {
    setLoading(true);
    setError(null);
    try {
      const nextState = await getDiscordState(userId);
      setState(nextState);
      setCandidate(nextState.candidates.at(-1) ?? null);
      if (!nextState.channels.some((channel) => channel.id === activeChannel)) {
        setActiveChannel("bot-commands");
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Không thể tải demo.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (compact) return;
    let cancelled = false;
    const storedProfileId = window.localStorage.getItem(PROFILE_STORAGE_KEY);
    if (!storedProfileId) {
      queueMicrotask(() => {
        if (!cancelled) setProfileChecking(false);
      });
      return () => {
        cancelled = true;
      };
    }

    getLearnerProfile(storedProfileId)
      .then((savedProfile) => {
        if (cancelled) return;
        setProfile(savedProfile);
        setActiveUser(savedProfile.demo_user_id);
      })
      .catch(() => {
        if (cancelled) return;
        window.localStorage.removeItem(PROFILE_STORAGE_KEY);
      })
      .finally(() => {
        if (!cancelled) setProfileChecking(false);
      });

    return () => {
      cancelled = true;
    };
  }, [compact]);

  useEffect(() => {
    let cancelled = false;
    getDiscordState(activeUser)
      .then((nextState) => {
        if (cancelled) return;
        setState(nextState);
        setCandidate(nextState.candidates.at(-1) ?? null);
        setError(null);
      })
      .catch((loadError) => {
        if (cancelled) return;
        setError(loadError instanceof Error ? loadError.message : "Không thể tải demo.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activeUser]);

  useEffect(() => {
    if (activeChannel !== "bot-commands" || !threadRef.current) return;
    const thread = threadRef.current;
    const frame = window.requestAnimationFrame(() => {
      thread.scrollTo({
        top: thread.scrollHeight,
        behavior: "smooth",
      });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [state?.assistant_messages, candidate, sending, activeChannel, catchupBrief]);

  async function submitLearnerProfile(fullName: string, studentIdLast5: string) {
    setProfileSubmitting(true);
    setProfileError(null);
    try {
      const savedProfile = await createLearnerProfile({
        full_name: fullName,
        student_id_last5: studentIdLast5,
        demo_user_id: activeUser,
      });
      window.localStorage.setItem(PROFILE_STORAGE_KEY, savedProfile.profile_id);
      setProfile(savedProfile);
      setActiveUser(savedProfile.demo_user_id);
    } catch (submitError) {
      setProfileError(
        submitError instanceof Error ? submitError.message : "Không lưu được thông tin.",
      );
    } finally {
      setProfileSubmitting(false);
    }
  }

  async function submitMessage(event?: FormEvent, preset?: string) {
    event?.preventDefault();
    const message = (preset ?? input).trim();
    if (!message || sending || !state) return;

    if (activeChannel !== "bot-commands") setActiveChannel("bot-commands");
    optimisticCounter.current += 1;
    const optimistic: AssistantMessage = {
      id: `optimistic-${optimisticCounter.current}`,
      role: "user",
      author_name: profile?.full_name ?? state.user.name,
      content: message,
      citations: [],
      memory_used: [],
      created_at: new Date().toISOString(),
    };
    setState({
      ...state,
      assistant_messages: [...state.assistant_messages, optimistic],
    });
    setInput("");
    setSending(true);
    setError(null);
    setCatchupBrief(null);
    try {
      const normalizedMessage = message
        .normalize("NFC")
        .toLocaleLowerCase("vi-VN");
      if (
        normalizedMessage.includes("bắt kịp")
        && normalizedMessage.includes("24")
      ) {
        const brief = await createCatchup(activeUser, 24);
        setCatchupBrief(brief);
        setCandidate(null);
        return;
      }
      const response = await sendChat(
        activeUser,
        message,
        "bot-commands",
        profile?.profile_id,
      );
      setState((current) =>
        current
          ? {
              ...current,
              provider: response.provider,
              assistant_messages: [
                ...current.assistant_messages.map((item) =>
                  item.id === optimistic.id && response.sensitive_input_consumed
                    ? {
                        ...item,
                        content: "[Email Google Calendar đã cung cấp]",
                      }
                    : item,
                ),
                response.message,
              ],
            }
          : current,
      );
      setCandidate(response.candidate);
    } catch (sendError) {
      setError(sendError instanceof Error ? sendError.message : "Không gửi được câu hỏi.");
      setState((current) =>
        current
          ? {
              ...current,
              assistant_messages: current.assistant_messages.filter(
                (item) => item.id !== optimistic.id,
              ),
            }
          : current,
      );
    } finally {
      setSending(false);
    }
  }

  async function handleConfirm() {
    if (!candidate || !state) return;
    setMemoryBusy(true);
    try {
      const memory = await confirmCandidate(candidate.id, activeUser);
      setState({
        ...state,
        memories: [...state.memories, memory],
        candidates: state.candidates.filter((item) => item.id !== candidate.id),
      });
      setCandidate(null);
    } catch (confirmError) {
      setError(confirmError instanceof Error ? confirmError.message : "Không lưu được memory.");
    } finally {
      setMemoryBusy(false);
    }
  }

  async function handleAddToCalendar() {
    if (!candidate || !state || !candidate.calendar_event) return;
    setMemoryBusy(true);
    setError(null);
    try {
      const result = await addCandidateToGoogleCalendar(candidate.id, activeUser);
      const confirmation: AssistantMessage = {
        id: `calendar-${result.event_id}`,
        role: "assistant",
        author_name: "Trợ lý ZicZord",
        content: `Đã thêm **${result.summary}** vào Google Calendar. [Mở sự kiện](${result.html_link})`,
        citations: [],
        memory_used: [result.memory.id],
        created_at: new Date().toISOString(),
      };
      setState({
        ...state,
        memories: [
          ...state.memories.filter((memory) => memory.id !== result.memory.id),
          result.memory,
        ],
        candidates: state.candidates.filter((item) => item.id !== candidate.id),
        assistant_messages: [...state.assistant_messages, confirmation],
      });
      setCandidate(null);
    } catch (calendarError) {
      setError(
        calendarError instanceof Error
          ? calendarError.message
          : "Không thêm được task vào Google Calendar.",
      );
    } finally {
      setMemoryBusy(false);
    }
  }

  async function handleDismissCandidate() {
    if (!candidate || !state) return;
    setMemoryBusy(true);
    try {
      await dismissCandidate(candidate.id, activeUser);
      setState({
        ...state,
        candidates: state.candidates.filter((item) => item.id !== candidate.id),
      });
      setCandidate(null);
    } catch (dismissError) {
      setError(
        dismissError instanceof Error
          ? dismissError.message
          : "Không bỏ được đề xuất.",
      );
    } finally {
      setMemoryBusy(false);
    }
  }

  async function handleDelete(memoryId: string) {
    if (!state) return;
    try {
      await deleteMemory(memoryId, activeUser);
      setState({
        ...state,
        memories: state.memories.filter((memory) => memory.id !== memoryId),
      });
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Không xóa được memory.");
    }
  }

  async function handleReset() {
    setMemoryBusy(true);
    try {
      await resetDemo();
      setPitchBrief(null);
      setCatchupBrief(null);
      setSyncedTasks({});
      await reload(activeUser);
    } catch (resetError) {
      setError(resetError instanceof Error ? resetError.message : "Không reset được demo.");
    } finally {
      setMemoryBusy(false);
    }
  }

  async function handleRunT004Pitch() {
    if (!state || state.user.team_id !== "T004") {
      setError("Pitch mode chỉ được mở cho thành viên team T004.");
      return;
    }
    setPitchBusy(true);
    setError(null);
    setSyncedTasks({});
    try {
      await loadT004PitchContext(activeUser);
      const [refreshed, brief] = await Promise.all([
        getDiscordState(activeUser),
        createTeamBrief(activeUser),
      ]);
      setState(refreshed);
      setCandidate(refreshed.candidates.at(-1) ?? null);
      setPitchBrief(brief);
      setActiveChannel("bot-commands");
    } catch (pitchError) {
      setError(
        pitchError instanceof Error
          ? pitchError.message
          : "Không chạy được luồng pitch T004.",
      );
    } finally {
      setPitchBusy(false);
    }
  }

  async function handleCreateGoogleTask(item: CatchupItem) {
    if (!pitchBrief) return;
    setTaskBusyItemId(item.id);
    setError(null);
    try {
      const task = await createGoogleTaskFromBrief(
        pitchBrief.id,
        item.id,
        activeUser,
      );
      setSyncedTasks((current) => ({ ...current, [item.id]: task }));
      const modeLabel =
        task.provider === "google-tasks"
          ? "Google Tasks thật"
          : "pitch-mock (chưa ghi ra tài khoản Google)";
      const confirmation: AssistantMessage = {
        id: `google-task-${task.task_id}`,
        role: "assistant",
        author_name: "Trợ lý ZicZord",
        content: `Đã tạo **${task.title}** bằng ${modeLabel}. Scope được khóa ở \`${task.scope_key}\`. [Mở Google Tasks](${task.html_link})`,
        citations: item.citations,
        memory_used: [],
        created_at: new Date().toISOString(),
      };
      setState((current) =>
        current
          ? {
              ...current,
              assistant_messages: [...current.assistant_messages, confirmation],
            }
          : current,
      );
    } catch (taskError) {
      setError(
        taskError instanceof Error
          ? taskError.message
          : "Không tạo được Google Task.",
      );
    } finally {
      setTaskBusyItemId(null);
    }
  }

  function summarizeCurrentChannel() {
    if (!currentChannel) return;
    const contextLabel = {
      team: `team ${currentChannel.scope_id}`,
      group: `group ${currentChannel.scope_id}`,
      lecture: `bài giảng ${currentChannel.name}`,
      lab: `phòng thực hành ${currentChannel.name}`,
      common: "kênh chung",
      qa: "kênh hỏi đáp",
      share: "kênh chia sẻ",
      announcement: "kênh thông báo",
    }[currentChannel.kind];
    submitMessage(undefined, `Tóm tắt ${contextLabel} hôm nay`);
  }

  if (!compact && (profileChecking || !profile)) {
    return (
      <LearnerGate
        checking={profileChecking}
        submitting={profileSubmitting}
        error={profileError}
        onSubmit={submitLearnerProfile}
      />
    );
  }

  return (
    <section className={`chat-shell ${compact ? "chat-shell-compact" : "chat-shell-full"}`}>
      <aside className="discord-sidebar">
        <div className="server-header">
          <div className="min-w-0">
            <p className="truncate text-sm font-bold">AI Thực chiến · K4</p>
            <p className="mt-0.5 truncate text-[11px] text-muted">369 học viên</p>
          </div>
          <CaretDown size={14} />
        </div>
        <div className="channel-scroll">
          {channelGroups.map((category) => (
            <div key={category} className="channel-group">
              <p className="channel-category">{category}</p>
              {state?.channels
                .filter((channel) => channel.category === category)
                .map((channel) => (
                  <button
                    key={channel.id}
                    type="button"
                    className={
                      activeChannel === channel.id
                        ? "channel-button channel-button-active"
                        : "channel-button"
                    }
                    onClick={() => setActiveChannel(channel.id)}
                  >
                    <Hash size={16} weight="bold" />
                    <span className="truncate">{channel.name}</span>
                    {channel.unread_count > 0 && (
                      <span className="unread-count">{channel.unread_count}</span>
                    )}
                  </button>
                ))}
            </div>
          ))}
        </div>
        <div className="discord-profile">
          <span className="avatar avatar-user">
            {profile
              ? initials(profile.full_name)
              : state
                ? initials(state.user.name)
                : "AN"}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-bold">
              {profile?.full_name ?? state?.user.name ?? "Thái Hoài An"}
            </p>
            <p className="truncate text-[10px] text-muted">
              {state?.user.team_id ?? "T004"} · {state?.user.group_id ?? "G10"}
            </p>
          </div>
        </div>
      </aside>

      <div className="discord-main">
        <header className="discord-channel-header">
          <div className="flex min-w-0 items-center gap-2">
            <Hash size={20} className="shrink-0 text-muted" weight="bold" />
            <p className="truncate text-sm font-bold">
              {currentChannel?.name ?? "🤖-gõ-commands"}
            </p>
            <span className="header-divider" />
            <p className="hidden truncate text-xs text-muted sm:block">
              {activeChannel === "bot-commands"
                ? "Hỏi toàn bộ ngữ cảnh bạn được phép xem"
                : "Discord snapshot · chỉ đọc"}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {!compact && (
              <>
                <label className="sr-only" htmlFor="member-select">
                  Chọn thành viên
                </label>
                <select
                  id="member-select"
                  className="member-select"
                  value={activeUser}
                  onChange={(event) => {
                    setLoading(true);
                    setActiveChannel("bot-commands");
                    setPitchBrief(null);
                    setCatchupBrief(null);
                    setSyncedTasks({});
                    setActiveUser(event.target.value);
                  }}
                >
                  {(state?.users ?? []).map((user) => (
                    <option key={user.id} value={user.id}>
                      {user.name}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={handleReset}
                  className="icon-button"
                  disabled={memoryBusy}
                  aria-label="Khôi phục dữ liệu demo"
                  title="Reset demo"
                >
                  <ArrowClockwise size={16} />
                </button>
              </>
            )}
            <MagnifyingGlass size={18} className="text-muted" />
          </div>
        </header>

        <div ref={threadRef} className="discord-thread">
          {loading ? (
            <LoadingState />
          ) : error && !state ? (
            <div className="grid h-full place-items-center p-6 text-center">
              <div>
                <p className="text-sm font-bold">Backend chưa sẵn sàng</p>
                <p className="mt-2 max-w-xs text-sm text-muted">{error}</p>
                <button
                  type="button"
                  onClick={() => reload(activeUser)}
                  className="button-secondary button-small mt-4"
                >
                  Thử lại
                </button>
              </div>
            </div>
          ) : activeChannel === "bot-commands" ? (
            <div className="thread-content">
              <div className="channel-intro">
                <span className="channel-intro-icon">
                  <Sparkle size={23} weight="fill" />
                </span>
                <h2>Trợ lý ZicZord đã vào phòng.</h2>
                <p>
                  ZicZord đọc nguồn Discord đã cấp quyền, sau đó recall memory đúng user và đúng nhóm.
                </p>
              </div>
              {!compact && state?.user.team_id === "T004" && (
                <section className="mx-4 mb-4 flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-accent/60 bg-accent-soft px-4 py-4">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="eyebrow text-accent-strong">Pitch mode</p>
                      <span className="safe-badge">
                        <ShieldCheck size={13} weight="fill" />
                        team:T004 only
                      </span>
                    </div>
                    <p className="mt-1 text-sm font-bold">
                      Context mock → brief có nguồn → Google Task
                    </p>
                    <p className="mt-1 text-xs leading-5 text-muted">
                      Chỉ upsert message trong #t-004; không sửa context chung,
                      group mentor hoặc phòng học.
                    </p>
                  </div>
                  <button
                    type="button"
                    className="button shrink-0"
                    onClick={handleRunT004Pitch}
                    disabled={pitchBusy || taskBusyItemId !== null}
                  >
                    <Sparkle size={15} weight="fill" />
                    {pitchBusy
                      ? "Đang nạp & tạo brief"
                      : pitchBrief
                        ? "Chạy lại brief T004"
                        : "Nạp context & tạo brief"}
                  </button>
                </section>
              )}
              {pitchBrief && (
                <TeamBriefPanel
                  brief={pitchBrief}
                  syncedTasks={syncedTasks}
                  busyItemId={taskBusyItemId}
                  onCreateTask={handleCreateGoogleTask}
                />
              )}
              {state?.assistant_messages.map((message) => (
                <AssistantTurn key={message.id} message={message} />
              ))}
              {catchupBrief && (
                <TeamBriefPanel
                  brief={catchupBrief}
                  syncedTasks={{}}
                  busyItemId={null}
                  mode="catchup"
                />
              )}
              {sending && (
                <div className="discord-turn" role="status">
                  <ZicZordAvatar />
                  <div>
                    <p className="message-author text-accent-strong">Trợ lý ZicZord</p>
                    <div className="mt-2 flex gap-1.5">
                      <span className="thinking-dot" />
                      <span className="thinking-dot" />
                      <span className="thinking-dot" />
                    </div>
                    <span className="sr-only">Trợ lý đang trả lời</span>
                  </div>
                </div>
              )}
              <AnimatePresence>
                {candidate && (
                  <CandidateCard
                    candidate={candidate}
                    onAddToCalendar={handleAddToCalendar}
                    onConfirm={handleConfirm}
                    onDismiss={handleDismissCandidate}
                    busy={memoryBusy}
                  />
                )}
              </AnimatePresence>
            </div>
          ) : (
            <div className="thread-content">
              <div className="channel-intro channel-intro-source">
                <span className="channel-intro-icon">
                  <Hash size={23} weight="bold" />
                </span>
                <h2>#{currentChannel?.name}</h2>
                <p>
                  Nguồn scraped được giữ nguyên tác giả, thời gian và permalink để kiểm chứng.
                </p>
                <button
                  type="button"
                  onClick={summarizeCurrentChannel}
                  className="button-secondary button-small mt-4"
                >
                  <Sparkle size={14} weight="fill" />
                  Nhờ ZicZord tóm tắt kênh này
                </button>
              </div>
              {sourceMessages.length > 0 ? (
                sourceMessages.map((message) => (
                  <SourceMessage key={message.id} message={message} />
                ))
              ) : (
                <div className="empty-channel">
                  Channel này chưa có message trong snapshot demo.
                </div>
              )}
            </div>
          )}
        </div>

        <div className="discord-composer">
          {error && state && <p className="mb-2 text-xs text-danger">{error}</p>}
          {activeChannel === "bot-commands" && !compact && (
            <div className="prompt-row">
              {state?.suggested_prompts.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => submitMessage(undefined, prompt)}
                  className="prompt-chip"
                >
                  {prompt}
                </button>
              ))}
            </div>
          )}
          <form
            onSubmit={submitMessage}
            className="chat-input-wrap"
          >
            <span className="composer-plus">+</span>
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              className="chat-input"
              placeholder={
                activeChannel === "bot-commands"
                  ? "Nhắn @Trợ lý ZicZord..."
                  : `Đang xem #${currentChannel?.name}`
              }
              aria-label="Tin nhắn"
              disabled={activeChannel !== "bot-commands"}
            />
            <button
              type="submit"
              disabled={!input.trim() || sending || activeChannel !== "bot-commands"}
              className="send-button"
              aria-label="Gửi tin nhắn"
              title="Gửi"
            >
              <ArrowUp size={17} weight="bold" />
            </button>
          </form>
          <p className="composer-note">
            <LockKey size={11} />
            Scope được tính ở server · response luôn giữ citation
          </p>
        </div>
      </div>

      <aside className="context-rail">
        <div className="context-header">
          <div>
            <p className="eyebrow">Context access</p>
            <p className="mt-2 text-sm font-bold">{state?.user.name ?? "Thái Hoài An"}</p>
          </div>
          <span className="safe-badge">
            <ShieldCheck size={13} weight="fill" />
            Isolated
          </span>
        </div>
        <div className="context-scroll">
          <div className="context-block">
            <div className="flex items-center justify-between">
              <p className="context-title">Scope được cấp</p>
              <span className="context-count">{state?.scopes.length ?? 6}</span>
            </div>
            <div className="scope-list">
              {state?.scopes.map((scope) => (
                <div key={`${scope.type}-${scope.id}`} className="scope-row">
                  <span className={`scope-node scope-node-${scope.type}`} />
                  <div className="min-w-0">
                    <p className="truncate text-xs font-bold">{scope.label}</p>
                    <p className="truncate text-[10px] text-muted">{scope.relation}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="context-block border-t border-line">
            <div className="flex items-center justify-between">
              <p className="context-title">Memory confirmed</p>
              <span className="context-count">{state?.memories.length ?? 0}</span>
            </div>
            <div className="mt-3 space-y-2.5">
              {state?.memories.slice(0, compact ? 3 : 8).map((memory) => (
                <MemoryCard
                  key={memory.id}
                  memory={memory}
                  onDelete={() => handleDelete(memory.id)}
                  canDelete={memory.scope_type === "user" || memory.scope_type === "team"}
                />
              ))}
            </div>
          </div>
        </div>
        <div className="ingestion-footer">
          <span className="status-dot" />
          <div className="min-w-0">
            <p className="truncate text-[11px] font-bold">
              {state?.ingestion.mode === "apify" ? "Apify dataset" : "Demo snapshot"}
            </p>
            <p className="truncate text-[10px] text-muted">
              {state?.ingestion.imported_count ?? 0} messages · {state?.provider ?? "local-demo"}
            </p>
          </div>
          <UsersThree size={15} className="ml-auto text-muted" />
        </div>
      </aside>
    </section>
  );
}
