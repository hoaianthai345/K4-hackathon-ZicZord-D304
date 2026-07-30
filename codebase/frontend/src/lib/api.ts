import type { ChatResponse, DiscordState, Memory } from "./types";

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
    throw new Error(detail ?? "Không thể kết nối Trợ lý Kute.");
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function getDiscordState(userId: string): Promise<DiscordState> {
  return apiFetch(`/api/discord-state?user_id=${encodeURIComponent(userId)}`);
}

export function sendChat(
  userId: string,
  message: string,
  channelId = "bot-commands",
): Promise<ChatResponse> {
  return apiFetch("/api/chat", {
    method: "POST",
    body: JSON.stringify({
      user_id: userId,
      message,
      channel_id: channelId,
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

export function deleteMemory(memoryId: string, userId: string): Promise<void> {
  return apiFetch(
    `/api/memories/${memoryId}?user_id=${encodeURIComponent(userId)}`,
    { method: "DELETE" },
  );
}

export function resetDemo(): Promise<void> {
  return apiFetch("/api/reset", { method: "POST" });
}
