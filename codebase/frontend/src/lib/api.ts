import type {
  AdminContextList,
  AdminEvaluation,
  AdminMemoryInput,
  AdminOverview,
  CatchupBrief,
  CalendarTaskResponse,
  ChatResponse,
  ContextPlanResponse,
  DiscordState,
  GoogleTaskResponse,
  LearnerProfile,
  LearnerProfileInput,
  Memory,
  PitchContextResponse,
} from "./types";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const detail = await response
      .json()
      .then((body) => body.detail)
      .catch(() => null);
    throw new Error(detail ?? "Không thể kết nối Trợ lý ZicZord.");
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

function adminFetch<T>(
  path: string,
  adminKey: string,
  init?: RequestInit,
): Promise<T> {
  return apiFetch(path, {
    ...init,
    headers: {
      ...(adminKey ? { "X-Admin-Key": adminKey } : {}),
      ...init?.headers,
    },
  });
}

export function getDiscordState(userId: string): Promise<DiscordState> {
  return apiFetch(`/api/discord-state?user_id=${encodeURIComponent(userId)}`);
}

export function getLearnerProfile(profileId: string): Promise<LearnerProfile> {
  return apiFetch(`/api/learner-profiles/${encodeURIComponent(profileId)}`);
}

export function createLearnerProfile(
  input: LearnerProfileInput,
): Promise<LearnerProfile> {
  return apiFetch("/api/learner-profiles", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function sendChat(
  userId: string,
  message: string,
  channelId = "bot-commands",
  profileId?: string,
): Promise<ChatResponse> {
  return apiFetch("/api/chat", {
    method: "POST",
    body: JSON.stringify({
      user_id: userId,
      message,
      channel_id: channelId,
      profile_id: profileId,
    }),
  });
}

export function confirmCandidate(
  candidateId: string,
  userId: string,
): Promise<Memory> {
  return apiFetch(
    `/api/memory-candidates/${candidateId}/confirm?user_id=${encodeURIComponent(userId)}`,
    { method: "POST" },
  );
}

export function dismissCandidate(
  candidateId: string,
  userId: string,
): Promise<void> {
  return apiFetch(
    `/api/memory-candidates/${encodeURIComponent(candidateId)}?user_id=${encodeURIComponent(userId)}`,
    { method: "DELETE" },
  );
}

export function addCandidateToGoogleCalendar(
  candidateId: string,
  userId: string,
): Promise<CalendarTaskResponse> {
  return apiFetch(
    `/api/memory-candidates/${encodeURIComponent(candidateId)}/google-calendar?user_id=${encodeURIComponent(userId)}`,
    { method: "POST" },
  );
}

export function loadT004PitchContext(
  userId: string,
): Promise<PitchContextResponse> {
  return apiFetch(
    `/api/pitch/t004/context?user_id=${encodeURIComponent(userId)}`,
    { method: "POST" },
  );
}

export function createTeamBrief(
  userId: string,
): Promise<CatchupBrief> {
  return apiFetch(
    `/api/pitch/t004/brief?user_id=${encodeURIComponent(userId)}`,
    { method: "POST" },
  );
}

export function createCatchup(
  userId: string,
  windowHours = 24,
): Promise<CatchupBrief> {
  return apiFetch("/api/catch-up", {
    method: "POST",
    body: JSON.stringify({
      user_id: userId,
      window_hours: windowHours,
      scope: "all_allowed",
    }),
  });
}

export function createGoogleTaskFromBrief(
  briefId: string,
  itemId: string,
  userId: string,
): Promise<GoogleTaskResponse> {
  return apiFetch(
    `/api/catch-up/${encodeURIComponent(briefId)}/items/${encodeURIComponent(itemId)}/google-task?user_id=${encodeURIComponent(userId)}`,
    { method: "POST" },
  );
}

export function deleteMemory(memoryId: string, userId: string): Promise<void> {
  return apiFetch(
    `/api/memories/${memoryId}?user_id=${encodeURIComponent(userId)}`,
    { method: "DELETE" },
  );
}

export function resetDemo(): Promise<void> {
  return apiFetch("/api/reset", { method: "POST" });
}

export function getAdminOverview(adminKey: string): Promise<AdminOverview> {
  return adminFetch("/api/admin/overview", adminKey);
}

export function getAdminEvaluation(adminKey: string): Promise<AdminEvaluation> {
  return adminFetch("/api/admin/evaluation", adminKey);
}

export function runAdminEvaluation(
  adminKey: string,
): Promise<AdminEvaluation["run_status"]> {
  return adminFetch("/api/admin/evaluation/run", adminKey, { method: "POST" });
}

export function getAdminContext(
  adminKey: string,
  filters: {
    search?: string;
    sourceType?: string;
    enabled?: boolean;
    limit?: number;
    offset?: number;
  } = {},
): Promise<AdminContextList> {
  const params = new URLSearchParams();
  if (filters.search) params.set("search", filters.search);
  if (filters.sourceType) params.set("source_type", filters.sourceType);
  if (filters.enabled !== undefined) params.set("enabled", String(filters.enabled));
  params.set("limit", String(filters.limit ?? 50));
  params.set("offset", String(filters.offset ?? 0));
  return adminFetch(`/api/admin/context?${params}`, adminKey);
}

export function updateAdminContext(
  adminKey: string,
  sourceType: string,
  sourceId: string,
  isEnabled: boolean,
): Promise<void> {
  return adminFetch(
    `/api/admin/context/${encodeURIComponent(sourceType)}/${encodeURIComponent(sourceId)}`,
    adminKey,
    {
      method: "PATCH",
      body: JSON.stringify({ is_enabled: isEnabled }),
    },
  );
}

export function inspectContextPlan(
  adminKey: string,
  query: string,
  userId = "U01862",
  channelId = "bot-commands",
): Promise<ContextPlanResponse> {
  return adminFetch("/api/admin/context/plan", adminKey, {
    method: "POST",
    body: JSON.stringify({
      user_id: userId,
      query,
      channel_id: channelId,
    }),
  });
}

export function reindexAdminContext(adminKey: string): Promise<Record<string, unknown>> {
  return adminFetch("/api/admin/context/reindex", adminKey, { method: "POST" });
}

export function getAdminMemories(adminKey: string): Promise<Memory[]> {
  return adminFetch("/api/admin/memories", adminKey);
}

export function createAdminMemory(
  adminKey: string,
  memory: AdminMemoryInput,
): Promise<Memory> {
  return adminFetch("/api/admin/memories", adminKey, {
    method: "POST",
    body: JSON.stringify(memory),
  });
}

export function updateAdminMemory(
  adminKey: string,
  memoryId: string,
  changes: Partial<AdminMemoryInput>,
): Promise<Memory> {
  return adminFetch(
    `/api/admin/memories/${encodeURIComponent(memoryId)}`,
    adminKey,
    {
      method: "PATCH",
      body: JSON.stringify(changes),
    },
  );
}

export function deleteAdminMemory(
  adminKey: string,
  memoryId: string,
): Promise<void> {
  return adminFetch(
    `/api/admin/memories/${encodeURIComponent(memoryId)}`,
    adminKey,
    { method: "DELETE" },
  );
}
