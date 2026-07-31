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

export type LearnerProfile = {
  profile_id: string;
  full_name: string;
  student_id_last5: string;
  demo_user_id: string;
  created_at: string;
  updated_at: string;
  last_seen_at: string;
};

export type LearnerProfileInput = {
  full_name: string;
  student_id_last5: string;
  demo_user_id: string;
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
    tool_calls: ContextToolCall[];
};

export type CatchupItem = {
  id: string;
  kind: "decision" | "task" | "blocker" | "announcement";
  title: string;
  detail: string;
  owner: string | null;
  deadline: string | null;
  status: "open" | "resolved" | "unknown";
  citations: Citation[];
};

export type CatchupBrief = {
  id: string;
  user_id: string;
  scope_key: string;
  window_hours: number;
  generated_at: string;
  source_message_count: number;
  channel_count: number;
  summary: string;
  items: CatchupItem[];
  acknowledged: boolean;
  provider: string;
};

export type ContextToolCall = {
  name: string;
  arguments: Record<string, unknown>;
  reason: string;
  result_count: number;
};

export type AdminOverview = {
  context_total: number;
  context_enabled: number;
  context_by_type: Record<string, number>;
  context_by_scope: Record<string, number>;
  memory_total: number;
  memory_by_scope: Record<string, number>;
  rag_reachable: boolean | null;
  rag_indexed_scopes: string[];
  admin_auth_required: boolean;
};

export type AdminContextItem = {
  source_id: string;
  source_type: "message" | "episode" | "painpoint" | "lesson";
  source_kind: string;
  title: string;
  channel_key: string;
  scope_key: string;
  day_code: string | null;
  page_number: number | null;
  created_at: string | null;
  content: string;
  is_enabled: boolean;
};

export type AdminContextList = {
  items: AdminContextItem[];
  total: number;
  limit: number;
  offset: number;
};

export type ContextSource = {
  source_id: string;
  source_type: "message" | "episode" | "painpoint" | "lesson";
  channel_key: string;
  scope_key: string;
  content: string;
  created_at: string | null;
  metadata: Record<string, unknown>;
};

export type ContextPlanResponse = {
  query: string;
  filters: Record<string, unknown>;
  notes: string[];
  tool_calls: ContextToolCall[];
  sources: ContextSource[];
};

export type AdminMemoryInput = {
  scope_type: ScopeType;
  scope_id: string;
  kind: MemoryKind;
  content: string;
  evidence?: string[];
  created_by?: string;
};

export type EvaluationRiskCoverage = {
  id:
    | "missing_evidence"
    | "ambiguous_context"
    | "forbidden_request"
    | "high_consequence";
  label: string;
  description: string;
  count: number;
  minimum: number;
  met: boolean;
};

export type EvaluationCase = {
  id: string;
  title: string;
  risk_types: EvaluationRiskCoverage["id"][];
  critical: boolean;
  input: {
    user_id: string;
    channel_id: string;
    message: string;
  };
  expected_behavior: string;
  origin: {
    observed: boolean;
    kind: string;
    reference: string;
  };
  checks: Record<string, unknown>;
};

export type EvaluationCheckResult = {
  name: string;
  passed: boolean;
  detail: string;
};

export type EvaluationCaseResult = {
  case_id: string;
  title: string;
  risk_types: EvaluationRiskCoverage["id"][];
  critical: boolean;
  observed: boolean;
  input: EvaluationCase["input"];
  expected_behavior: string;
  passed: boolean;
  latency_ms: number;
  answer: string;
  citations: Citation[];
  tool_calls: ContextToolCall[];
  provider: string | null;
  checks: EvaluationCheckResult[];
  error: string | null;
};

export type EvaluationRun = {
  run_id: string;
  suite_id: string;
  suite_version: string;
  started_at: string;
  completed_at: string;
  provider: string;
  model: string;
  summary: {
    passed: number;
    failed: number;
    total: number;
    pass_rate: number;
    critical_failures: string[];
    meets_overall_threshold: boolean;
    meets_zero_tolerance: boolean;
    accepted: boolean;
  };
  results: EvaluationCaseResult[];
};

export type EvaluationRunStatus = {
  state: "idle" | "starting" | "running" | "completed" | "failed";
  run_id: string | null;
  completed_cases: number;
  total_cases: number;
  error: string | null;
};

export type AdminEvaluation = {
  suite_id: string;
  suite_version: string;
  decision_statement: string;
  decision_problem: string;
  provider: string;
  model: string;
  total_cases: number;
  observed_cases: number;
  risk_type_count: number;
  risk_coverage: EvaluationRiskCoverage[];
  acceptance_threshold: {
    overall_percent: number;
    zero_tolerance_rule: string;
    locked: boolean;
    locked_at: string;
  };
  cases: EvaluationCase[];
  baseline_run: EvaluationRun | null;
  latest_run: EvaluationRun | null;
  run_status: EvaluationRunStatus;
};
