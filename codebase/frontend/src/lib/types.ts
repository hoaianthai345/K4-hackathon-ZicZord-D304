export type ScopeType = "user" | "team" | "group" | "room" | "cohort";
export type MemoryKind =
  | "decision"
  | "task"
  | "blocker"
  | "preference"
  | "learning_note";

export type CommunityUser = {
  id: string;
  discord_user_id: string;
  name: string;
  member_label: string;
  role: "student" | "mentor";
  cohort_id: string;
  team_id: string | null;
  group_id: string;
  lecture_room_id: string | null;
  lab_room_id: string | null;
};

export type ScopeDescriptor = {
  type: ScopeType;
  id: string;
  label: string;
  relation: string;
};

export type DiscordChannel = {
  id: string;
  discord_channel_id: string;
  name: string;
  category: string;
  kind:
    | "common"
    | "qa"
    | "share"
    | "announcement"
    | "team"
    | "group"
    | "lecture"
    | "lab";
  scope_type: ScopeType;
  scope_id: string;
  unread_count: number;
};

export type DiscordMessage = {
  id: string;
  source_message_id: string;
  channel_id: string;
  author_id: string;
  author_name: string;
  content: string;
  created_at: string;
  permalink: string;
  source: "demo" | "apify";
};

export type Citation = {
  message_id: string;
  channel_id: string;
  channel_name: string;
  label: string;
  permalink: string;
};

export type Memory = {
  id: string;
  scope_type: ScopeType;
  scope_id: string;
  kind: MemoryKind;
  content: string;
  evidence: string[];
  created_by: string;
  status: "confirmed";
  created_at: string;
  updated_at: string;
};

export type MemoryCandidate = {
  id: string;
  scope_type: ScopeType;
  scope_id: string;
  kind: MemoryKind;
  content: string;
  evidence: string[];
  created_by: string;
  status: "proposed";
  created_at: string;
};

export type AssistantMessage = {
  id: string;
  role: "user" | "assistant";
  author_name: string;
  content: string;
  citations: Citation[];
  memory_used: string[];
  created_at: string;
};

export type IngestionStatus = {
  mode: "demo-snapshot" | "apify";
  dataset_id: string | null;
  last_synced_at: string | null;
  imported_count: number;
  skipped_count: number;
};

export type DiscordState = {
  user: CommunityUser;
  users: CommunityUser[];
  scopes: ScopeDescriptor[];
  channels: DiscordChannel[];
  discord_messages: DiscordMessage[];
  memories: Memory[];
  candidates: MemoryCandidate[];
  assistant_messages: AssistantMessage[];
  suggested_prompts: string[];
  provider: string;
  ingestion: IngestionStatus;
};

export type ChatResponse = {
  message: AssistantMessage;
  candidate: MemoryCandidate | null;
  provider: string;
};
