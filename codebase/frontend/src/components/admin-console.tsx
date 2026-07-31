"use client";

import {
  ArrowClockwise,
  ArrowLeft,
  Books,
  Brain,
  Check,
  Database,
  Eye,
  EyeSlash,
  Flask,
  Funnel,
  MagnifyingGlass,
  Plus,
  ShieldCheck,
  Sparkle,
  Trash,
  Wrench,
  X,
} from "@phosphor-icons/react";
import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";

import {
  createAdminMemory,
  deleteAdminMemory,
  getAdminContext,
  getAdminEvaluation,
  getAdminMemories,
  getAdminOverview,
  inspectContextPlan,
  reindexAdminContext,
  runAdminEvaluation,
  updateAdminContext,
  updateAdminMemory,
} from "@/lib/api";
import type {
  AdminContextItem,
  AdminEvaluation,
  AdminMemoryInput,
  AdminOverview,
  ContextPlanResponse,
  Memory,
  MemoryKind,
  ScopeType,
} from "@/lib/types";

import { Logo } from "./logo";
import { EvaluationDashboard } from "./evaluation-dashboard";
import { ThemeToggle } from "./theme-toggle";

type Panel = "evaluation" | "context" | "memory" | "tools";

const SOURCE_LABELS: Record<AdminContextItem["source_type"], string> = {
  lesson: "Bài học",
  message: "Discord",
  episode: "Episode",
  painpoint: "Pain point",
};

const EMPTY_MEMORY: AdminMemoryInput = {
  scope_type: "cohort",
  scope_id: "K4",
  kind: "learning_note",
  content: "",
  evidence: [],
  created_by: "admin",
};

function compactNumber(value: number) {
  return new Intl.NumberFormat("vi-VN", { notation: "compact" }).format(value);
}

function AdminSkeleton() {
  return (
    <div className="admin-skeleton" role="status">
      <div className="skeleton h-24" />
      <div className="skeleton h-64" />
      <span className="sr-only">Đang tải dữ liệu quản trị</span>
    </div>
  );
}

export function AdminConsole() {
  const [panel, setPanel] = useState<Panel>("evaluation");
  const [adminKey, setAdminKey] = useState("");
  const [keyReady, setKeyReady] = useState(false);
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [evaluation, setEvaluation] = useState<AdminEvaluation | null>(null);
  const [contexts, setContexts] = useState<AdminContextItem[]>([]);
  const [contextTotal, setContextTotal] = useState(0);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [search, setSearch] = useState("");
  const [sourceType, setSourceType] = useState("");
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [needsKey, setNeedsKey] = useState(false);
  const [memoryDraft, setMemoryDraft] = useState<AdminMemoryInput>(EMPTY_MEMORY);
  const [editingMemory, setEditingMemory] = useState<string | null>(null);
  const [editingContent, setEditingContent] = useState("");
  const [toolQuery, setToolQuery] = useState(
    "Giảng viên giải thích Transformer và attention như thế nào?",
  );
  const [toolPlan, setToolPlan] = useState<ContextPlanResponse | null>(null);

  const lessonCount = overview?.context_by_type.lesson ?? 0;
  const disabledCount = overview
    ? overview.context_total - overview.context_enabled
    : 0;

  const scopeOptions = useMemo(
    () => Object.keys(overview?.context_by_scope ?? {}),
    [overview],
  );

  async function loadAll(key = adminKey) {
    setLoading(true);
    setError(null);
    try {
      const [nextOverview, nextEvaluation, nextContext, nextMemories] = await Promise.all([
        getAdminOverview(key),
        getAdminEvaluation(key),
        getAdminContext(key, { search, sourceType, limit: 50 }),
        getAdminMemories(key),
      ]);
      setOverview(nextOverview);
      setEvaluation(nextEvaluation);
      setContexts(nextContext.items);
      setContextTotal(nextContext.total);
      setMemories(nextMemories);
      setNeedsKey(false);
    } catch (loadError) {
      const message =
        loadError instanceof Error ? loadError.message : "Không tải được admin data.";
      setError(message);
      setNeedsKey(message.toLocaleLowerCase("vi").includes("admin key"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      const savedKey = sessionStorage.getItem("kute-admin-key") ?? "";
      setAdminKey(savedKey);
      setKeyReady(true);
      loadAll(savedKey);
    }, 0);
    return () => window.clearTimeout(timeout);
    // Session storage is read once on mount. Search is applied explicitly.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const runState = evaluation?.run_status.state;
    if (runState !== "starting" && runState !== "running") return;
    const interval = window.setInterval(() => {
      getAdminEvaluation(adminKey)
        .then((nextEvaluation) => {
          setEvaluation(nextEvaluation);
          if (nextEvaluation.run_status.error) {
            setError(nextEvaluation.run_status.error);
          }
        })
        .catch((pollError) => {
          setError(
            pollError instanceof Error
              ? pollError.message
              : "Không cập nhật được tiến độ eval.",
          );
        });
    }, 2000);
    return () => window.clearInterval(interval);
  }, [adminKey, evaluation?.run_status.state]);

  function saveKey(event: FormEvent) {
    event.preventDefault();
    sessionStorage.setItem("kute-admin-key", adminKey);
    loadAll(adminKey);
  }

  async function applyContextFilter(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    try {
      const result = await getAdminContext(adminKey, {
        search,
        sourceType,
        limit: 50,
      });
      setContexts(result.items);
      setContextTotal(result.total);
      setError(null);
    } catch (filterError) {
      setError(
        filterError instanceof Error ? filterError.message : "Không lọc được context.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function toggleContext(item: AdminContextItem) {
    setBusyId(item.source_id);
    try {
      await updateAdminContext(
        adminKey,
        item.source_type,
        item.source_id,
        !item.is_enabled,
      );
      setContexts((current) =>
        current.map((value) =>
          value.source_id === item.source_id
            ? { ...value, is_enabled: !value.is_enabled }
            : value,
        ),
      );
      const nextOverview = await getAdminOverview(adminKey);
      setOverview(nextOverview);
    } catch (toggleError) {
      setError(
        toggleError instanceof Error ? toggleError.message : "Không cập nhật được context.",
      );
    } finally {
      setBusyId(null);
    }
  }

  async function createMemory(event: FormEvent) {
    event.preventDefault();
    if (!memoryDraft.content.trim()) return;
    setBusyId("create-memory");
    try {
      const memory = await createAdminMemory(adminKey, memoryDraft);
      setMemories((current) => [memory, ...current]);
      setMemoryDraft(EMPTY_MEMORY);
      setOverview((current) =>
        current ? { ...current, memory_total: current.memory_total + 1 } : current,
      );
      setError(null);
    } catch (createError) {
      setError(
        createError instanceof Error ? createError.message : "Không tạo được memory.",
      );
    } finally {
      setBusyId(null);
    }
  }

  async function saveMemory(memoryId: string) {
    if (!editingContent.trim()) return;
    setBusyId(memoryId);
    try {
      const updated = await updateAdminMemory(adminKey, memoryId, {
        content: editingContent,
      });
      setMemories((current) =>
        current.map((memory) => (memory.id === memoryId ? updated : memory)),
      );
      setEditingMemory(null);
      setEditingContent("");
    } catch (updateError) {
      setError(
        updateError instanceof Error ? updateError.message : "Không cập nhật được memory.",
      );
    } finally {
      setBusyId(null);
    }
  }

  async function removeMemory(memoryId: string) {
    setBusyId(memoryId);
    try {
      await deleteAdminMemory(adminKey, memoryId);
      setMemories((current) => current.filter((memory) => memory.id !== memoryId));
      setOverview((current) =>
        current
          ? { ...current, memory_total: Math.max(0, current.memory_total - 1) }
          : current,
      );
    } catch (deleteError) {
      setError(
        deleteError instanceof Error ? deleteError.message : "Không xóa được memory.",
      );
    } finally {
      setBusyId(null);
    }
  }

  async function inspectTools(event: FormEvent) {
    event.preventDefault();
    if (!toolQuery.trim()) return;
    setBusyId("tool-plan");
    try {
      setToolPlan(await inspectContextPlan(adminKey, toolQuery));
      setError(null);
    } catch (toolError) {
      setError(
        toolError instanceof Error ? toolError.message : "Không phân tích được retrieval.",
      );
    } finally {
      setBusyId(null);
    }
  }

  async function reindex() {
    setBusyId("reindex");
    try {
      await reindexAdminContext(adminKey);
      await loadAll(adminKey);
    } catch (reindexError) {
      setError(
        reindexError instanceof Error ? reindexError.message : "Không chạy được re-index.",
      );
    } finally {
      setBusyId(null);
    }
  }

  async function runEvaluation() {
    setBusyId("run-evaluation");
    try {
      const runStatus = await runAdminEvaluation(adminKey);
      setEvaluation((current) =>
        current ? { ...current, run_status: runStatus } : current,
      );
      setError(null);
    } catch (runError) {
      setError(
        runError instanceof Error ? runError.message : "Không khởi chạy được eval.",
      );
    } finally {
      setBusyId(null);
    }
  }

  if (!keyReady || (loading && !overview && !needsKey)) {
    return (
      <main className="admin-root">
        <AdminSkeleton />
      </main>
    );
  }

  if (needsKey && !overview) {
    return (
      <main className="admin-auth-root">
        <form className="admin-auth-card" onSubmit={saveKey}>
          <span className="admin-auth-icon">
            <ShieldCheck size={24} weight="fill" />
          </span>
          <h1>Nhập admin key</h1>
          <p>Key chỉ được giữ trong sessionStorage của tab hiện tại.</p>
          <label htmlFor="admin-key">Admin key</label>
          <input
            id="admin-key"
            type="password"
            value={adminKey}
            onChange={(event) => setAdminKey(event.target.value)}
            autoComplete="current-password"
          />
          {error && <p className="admin-inline-error">{error}</p>}
          <button className="button" type="submit">
            Mở console
          </button>
          <Link href="/chat" className="button-secondary">
            Quay lại chat
          </Link>
        </form>
      </main>
    );
  }

  return (
    <main className="admin-root">
      <aside className="admin-sidebar">
        <div className="admin-brand">
          <Logo />
          <p>Context Admin</p>
        </div>
        <nav aria-label="Admin">
          <button
            className={panel === "evaluation" ? "admin-nav-active" : ""}
            onClick={() => setPanel("evaluation")}
            type="button"
          >
            <Flask size={17} />
            Evaluation
          </button>
          <button
            className={panel === "context" ? "admin-nav-active" : ""}
            onClick={() => setPanel("context")}
            type="button"
          >
            <Database size={17} />
            Context library
          </button>
          <button
            className={panel === "memory" ? "admin-nav-active" : ""}
            onClick={() => setPanel("memory")}
            type="button"
          >
            <Brain size={17} />
            Memory
          </button>
          <button
            className={panel === "tools" ? "admin-nav-active" : ""}
            onClick={() => setPanel("tools")}
            type="button"
          >
            <Wrench size={17} />
            Tool inspector
          </button>
        </nav>
        <div className="admin-sidebar-footer">
          <Link href="/chat">
            <ArrowLeft size={15} />
            Về chat
          </Link>
          <ThemeToggle />
        </div>
      </aside>

      <section className="admin-workspace">
        <header className="admin-topbar">
          <div>
            <p className="admin-page-label">Kute operations</p>
            <h1>
              {panel === "evaluation"
                ? "AI evaluation"
                : panel === "context"
                  ? "Context library"
                : panel === "memory"
                  ? "Confirmed memory"
                  : "Retrieval tool inspector"}
            </h1>
          </div>
          <div className="admin-topbar-actions">
            <span className="admin-health">
              <Check size={13} weight="bold" />
              {overview?.rag_reachable ? "RAG healthy" : "RAG unavailable"}
            </span>
            <button
              className="button-secondary button-small"
              type="button"
              onClick={() => loadAll(adminKey)}
              disabled={loading}
            >
              <ArrowClockwise size={14} />
              Làm mới
            </button>
          </div>
        </header>

        {error && (
          <div className="admin-error" role="alert">
            <X size={15} weight="bold" />
            <span>{error}</span>
            <button type="button" onClick={() => setError(null)}>
              Đóng
            </button>
          </div>
        )}

        {panel !== "evaluation" && (
          <section className="admin-metrics" aria-label="Tổng quan">
            <article>
              <p>Context đang bật</p>
              <strong>{compactNumber(overview?.context_enabled ?? 0)}</strong>
              <span>{disabledCount} record đang tắt</span>
            </article>
            <article>
              <p>Nguồn bài học</p>
              <strong>{compactNumber(lessonCount)}</strong>
              <span>Transcript, slide và tutor Q&amp;A</span>
            </article>
            <article>
              <p>Confirmed memory</p>
              <strong>{overview?.memory_total ?? 0}</strong>
              <span>{Object.keys(overview?.memory_by_scope ?? {}).length} scope có dữ liệu</span>
            </article>
            <article>
              <p>RAG scopes</p>
              <strong>{overview?.rag_indexed_scopes.length ?? 0}</strong>
              <span>{overview?.rag_indexed_scopes.join(", ") || "Chưa index"}</span>
            </article>
          </section>
        )}

        {panel === "evaluation" && evaluation && (
          <EvaluationDashboard report={evaluation} onRun={runEvaluation} />
        )}

        {panel === "context" && (
          <section className="admin-panel">
            <div className="admin-panel-head">
              <div>
                <h2>Nguồn context</h2>
                <p>{contextTotal.toLocaleString("vi-VN")} record phù hợp bộ lọc</p>
              </div>
              <button
                className="button-secondary button-small"
                type="button"
                onClick={reindex}
                disabled={busyId === "reindex"}
              >
                <Sparkle size={14} weight="fill" />
                Re-index Discord RAG
              </button>
            </div>

            <form className="admin-filterbar" onSubmit={applyContextFilter}>
              <label className="admin-search">
                <MagnifyingGlass size={16} />
                <span className="sr-only">Tìm context</span>
                <input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Tìm title hoặc nội dung"
                />
              </label>
              <label>
                <span className="sr-only">Loại nguồn</span>
                <select
                  value={sourceType}
                  onChange={(event) => setSourceType(event.target.value)}
                >
                  <option value="">Mọi loại nguồn</option>
                  <option value="lesson">Bài học</option>
                  <option value="message">Discord message</option>
                  <option value="episode">Issue episode</option>
                  <option value="painpoint">Pain point</option>
                </select>
              </label>
              <button className="button-secondary button-small" type="submit">
                <Funnel size={14} />
                Lọc
              </button>
            </form>

            <div className="admin-context-list">
              {loading ? (
                <AdminSkeleton />
              ) : contexts.length === 0 ? (
                <div className="admin-empty">
                  <Books size={24} />
                  <h3>Chưa có context phù hợp</h3>
                  <p>Đổi từ khóa hoặc chạy learning-loader để nạp bài học.</p>
                </div>
              ) : (
                contexts.map((item) => (
                  <article className="admin-context-row" key={item.source_id}>
                    <div className="admin-context-main">
                      <div className="admin-context-meta">
                        <span className={`admin-source admin-source-${item.source_type}`}>
                          {SOURCE_LABELS[item.source_type]}
                        </span>
                        <span>{item.source_kind}</span>
                        <span>{item.scope_key}</span>
                        {item.day_code && <span>{item.day_code}</span>}
                        {item.page_number && <span>Trang {item.page_number}</span>}
                      </div>
                      <h3>{item.title}</h3>
                      <p>{item.content}</p>
                      <code>{item.source_id}</code>
                    </div>
                    <button
                      type="button"
                      className={
                        item.is_enabled
                          ? "admin-toggle admin-toggle-on"
                          : "admin-toggle"
                      }
                      onClick={() => toggleContext(item)}
                      disabled={busyId === item.source_id}
                      aria-label={
                        item.is_enabled
                          ? `Tắt context ${item.title}`
                          : `Bật context ${item.title}`
                      }
                    >
                      {item.is_enabled ? <Eye size={15} /> : <EyeSlash size={15} />}
                      {item.is_enabled ? "Đang dùng" : "Đã tắt"}
                    </button>
                  </article>
                ))
              )}
            </div>
          </section>
        )}

        {panel === "memory" && (
          <div className="admin-memory-layout">
            <form className="admin-memory-form" onSubmit={createMemory}>
              <div>
                <h2>Tạo confirmed memory</h2>
                <p>Memory mới có hiệu lực ngay trong scope được chọn.</p>
              </div>
              <label>
                Scope type
                <select
                  value={memoryDraft.scope_type}
                  onChange={(event) =>
                    setMemoryDraft((current) => ({
                      ...current,
                      scope_type: event.target.value as ScopeType,
                    }))
                  }
                >
                  <option value="user">User</option>
                  <option value="team">Team</option>
                  <option value="group">Group</option>
                  <option value="room">Room</option>
                  <option value="cohort">Cohort</option>
                </select>
              </label>
              <label>
                Scope ID
                <input
                  value={memoryDraft.scope_id}
                  onChange={(event) =>
                    setMemoryDraft((current) => ({
                      ...current,
                      scope_id: event.target.value,
                    }))
                  }
                  list="scope-options"
                />
                <datalist id="scope-options">
                  {scopeOptions.map((scope) => (
                    <option key={scope} value={scope.split(":")[1]} />
                  ))}
                </datalist>
              </label>
              <label>
                Memory kind
                <select
                  value={memoryDraft.kind}
                  onChange={(event) =>
                    setMemoryDraft((current) => ({
                      ...current,
                      kind: event.target.value as MemoryKind,
                    }))
                  }
                >
                  <option value="decision">Decision</option>
                  <option value="task">Task</option>
                  <option value="blocker">Blocker</option>
                  <option value="preference">Preference</option>
                  <option value="learning_note">Learning note</option>
                </select>
              </label>
              <label>
                Nội dung
                <textarea
                  value={memoryDraft.content}
                  onChange={(event) =>
                    setMemoryDraft((current) => ({
                      ...current,
                      content: event.target.value,
                    }))
                  }
                  rows={5}
                  placeholder="Ví dụ: Team T004 chốt dùng FastAPI cho ingest service."
                />
              </label>
              <button
                className="button"
                type="submit"
                disabled={!memoryDraft.content.trim() || busyId === "create-memory"}
              >
                <Plus size={15} weight="bold" />
                Tạo memory
              </button>
            </form>

            <section className="admin-memory-list">
              <div className="admin-panel-head">
                <div>
                  <h2>Memory hiện có</h2>
                  <p>{memories.length} confirmed memory</p>
                </div>
              </div>
              {memories.map((memory) => (
                <article className="admin-memory-row" key={memory.id}>
                  <div className="admin-memory-meta">
                    <span>{memory.scope_type}:{memory.scope_id}</span>
                    <span>{memory.kind}</span>
                  </div>
                  {editingMemory === memory.id ? (
                    <div className="admin-memory-editor">
                      <textarea
                        value={editingContent}
                        onChange={(event) => setEditingContent(event.target.value)}
                        rows={3}
                        aria-label={`Sửa memory ${memory.id}`}
                      />
                      <div>
                        <button
                          className="button button-small"
                          type="button"
                          onClick={() => saveMemory(memory.id)}
                          disabled={busyId === memory.id}
                        >
                          Lưu
                        </button>
                        <button
                          className="button-secondary button-small"
                          type="button"
                          onClick={() => setEditingMemory(null)}
                        >
                          Hủy
                        </button>
                      </div>
                    </div>
                  ) : (
                    <p>{memory.content}</p>
                  )}
                  <div className="admin-memory-actions">
                    <button
                      type="button"
                      onClick={() => {
                        setEditingMemory(memory.id);
                        setEditingContent(memory.content);
                      }}
                    >
                      Sửa
                    </button>
                    <button
                      type="button"
                      onClick={() => removeMemory(memory.id)}
                      disabled={busyId === memory.id}
                    >
                      <Trash size={13} />
                      Xóa
                    </button>
                  </div>
                </article>
              ))}
            </section>
          </div>
        )}

        {panel === "tools" && (
          <section className="admin-tool-layout">
            <form className="admin-tool-query" onSubmit={inspectTools}>
              <div>
                <h2>Kiểm tra retrieval plan</h2>
                <p>
                  Xem hệ thống chọn time window, channel và nguồn nào trước khi gọi model.
                </p>
              </div>
              <label htmlFor="tool-query">Câu hỏi thử nghiệm</label>
              <textarea
                id="tool-query"
                value={toolQuery}
                onChange={(event) => setToolQuery(event.target.value)}
                rows={4}
              />
              <button
                className="button"
                type="submit"
                disabled={!toolQuery.trim() || busyId === "tool-plan"}
              >
                <Wrench size={15} />
                Phân tích tool calls
              </button>
            </form>

            <section className="admin-tool-result">
              {!toolPlan ? (
                <div className="admin-empty">
                  <Wrench size={24} />
                  <h3>Chưa có retrieval trace</h3>
                  <p>Nhập câu hỏi để xem planner chọn tool và bộ lọc.</p>
                </div>
              ) : (
                <>
                  <div className="admin-filter-summary">
                    <h2>Bộ lọc đã suy ra</h2>
                    <pre>{JSON.stringify(toolPlan.filters, null, 2)}</pre>
                    {toolPlan.notes.map((note) => (
                      <p key={note}>{note}</p>
                    ))}
                  </div>
                  <div className="admin-tool-calls">
                    {toolPlan.tool_calls.map((call) => (
                      <article key={`${call.name}-${call.reason}`}>
                        <div>
                          <code>{call.name}</code>
                          <strong>{call.result_count} kết quả</strong>
                        </div>
                        <p>{call.reason}</p>
                        <pre>{JSON.stringify(call.arguments, null, 2)}</pre>
                      </article>
                    ))}
                  </div>
                  <div className="admin-tool-sources">
                    <h2>Context preview</h2>
                    {toolPlan.sources.slice(0, 4).map((source) => (
                      <article key={source.source_id}>
                        <span>{source.source_type}</span>
                        <p>{source.content}</p>
                        <code>{source.source_id}</code>
                      </article>
                    ))}
                  </div>
                </>
              )}
            </section>
          </section>
        )}
      </section>
    </main>
  );
}
