"use client";

import {
  ArrowClockwise,
  ArrowSquareOut,
  ArrowUp,
  Brain,
  CaretDown,
  Check,
  Hash,
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

import {
  confirmCandidate,
  deleteMemory,
  getDiscordState,
  resetDemo,
  sendChat,
} from "@/lib/api";
import type {
  AssistantMessage,
  DiscordMessage,
  DiscordState,
  Memory,
  MemoryCandidate,
  ScopeType,
} from "@/lib/types";

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

function initials(name: string) {
  return name
    .split(/[\s-]+/)
    .filter(Boolean)
    .slice(-2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
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

function CandidateCard({
  candidate,
  onConfirm,
  onDismiss,
  busy,
}: {
  candidate: MemoryCandidate;
  onConfirm: () => void;
  onDismiss: () => void;
  busy: boolean;
}) {
  return (
    <motion.aside
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 8 }}
      className="memory-proposal"
    >
      <span className="proposal-icon">
        <Brain size={17} weight="fill" />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="eyebrow text-accent-strong">Đề xuất memory</p>
          <span className="scope-chip scope-chip-team">
            {SCOPE_LABELS[candidate.scope_type]} · {candidate.scope_id}
          </span>
        </div>
        <p className="mt-2 text-sm leading-6">{candidate.content}</p>
        <p className="mt-1 text-xs text-muted">
          Chỉ trở thành memory dài hạn sau khi bạn xác nhận.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onConfirm}
            disabled={busy}
            className="button button-small"
          >
            <Check size={15} weight="bold" />
            {busy ? "Đang lưu" : "Xác nhận đúng scope"}
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
  return (
    <motion.article
      initial={{ opacity: 0, y: 7 }}
      animate={{ opacity: 1, y: 0 }}
      className="discord-turn"
    >
      <span className={assistant ? "avatar avatar-bot" : "avatar avatar-user"}>
        {assistant ? "K" : initials(message.author_name)}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
          <p className={assistant ? "message-author text-accent-strong" : "message-author"}>
            {message.author_name}
          </p>
          {assistant && <span className="bot-badge">APP</span>}
          <time className="message-time">vừa xong</time>
        </div>
        <p className="mt-1 whitespace-pre-line text-sm leading-6 text-ink/88">
          {message.content}
        </p>
        {message.citations.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {message.citations.map((citation) => (
              <a
                key={citation.message_id}
                href={citation.permalink}
                target="_blank"
                rel="noreferrer"
                className="citation-chip"
                title="Mở tin nhắn nguồn trên Discord"
              >
                <Hash size={12} weight="bold" />
                {citation.channel_name}
                <ArrowSquareOut size={11} />
              </a>
            ))}
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

export function ChatShell({ compact = false }: { compact?: boolean }) {
  const [state, setState] = useState<DiscordState | null>(null);
  const [activeUser, setActiveUser] = useState("U01862");
  const [activeChannel, setActiveChannel] = useState("bot-commands");
  const [input, setInput] = useState("");
  const [candidate, setCandidate] = useState<MemoryCandidate | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [memoryBusy, setMemoryBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
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
    if (activeChannel === "bot-commands") {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [state?.assistant_messages, candidate, sending, activeChannel]);

  async function submitMessage(event?: FormEvent, preset?: string) {
    event?.preventDefault();
    const message = (preset ?? input).trim();
    if (!message || sending || !state) return;

    if (activeChannel !== "bot-commands") setActiveChannel("bot-commands");
    optimisticCounter.current += 1;
    const optimistic: AssistantMessage = {
      id: `optimistic-${optimisticCounter.current}`,
      role: "user",
      author_name: state.user.name,
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
    try {
      const response = await sendChat(activeUser, message);
      setState((current) =>
        current
          ? {
              ...current,
              provider: response.provider,
              assistant_messages: [...current.assistant_messages, response.message],
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
      await reload(activeUser);
    } catch (resetError) {
      setError(resetError instanceof Error ? resetError.message : "Không reset được demo.");
    } finally {
      setMemoryBusy(false);
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
          <span className="avatar avatar-user">{state ? initials(state.user.name) : "AN"}</span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-bold">{state?.user.name ?? "Thái Hoài An"}</p>
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

        <div className="discord-thread">
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
                <h2>Trợ lý Kute đã vào phòng.</h2>
                <p>
                  Kute đọc nguồn Discord đã cấp quyền, sau đó recall memory đúng user và đúng nhóm.
                </p>
              </div>
              {state?.assistant_messages.map((message) => (
                <AssistantTurn key={message.id} message={message} />
              ))}
              {sending && (
                <div className="discord-turn" role="status">
                  <span className="avatar avatar-bot">K</span>
                  <div>
                    <p className="message-author text-accent-strong">Trợ lý Kute</p>
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
                    onConfirm={handleConfirm}
                    onDismiss={() => setCandidate(null)}
                    busy={memoryBusy}
                  />
                )}
              </AnimatePresence>
              <div ref={bottomRef} />
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
                  Nhờ Kute tóm tắt kênh này
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
                  ? "Nhắn @Trợ lý Kute..."
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
