import { config } from "./config";

export interface PostSummary {
  post_id: string;
  post_title: string;
  voc_type_code: string;
  voc_type_label?: string;
  visibility_code: string;
  visibility_label?: string;
  created_at: string;
}

export interface PostDetail extends PostSummary {
  post_body: string;
}

export interface Affiliation {
  organization_name: string;
  corporate_entity_id: string | null;
  role_title: string | null;
}

export interface Keyman {
  person_id: string;
  person_name: string;
  person_side_code: string;
  person_side_label?: string;
  mention_context: string | null;
  last_known_job_title: string | null;
  affiliations: Affiliation[];
}

export interface Counterparty {
  counterparty_entity_name: string;
  relationship_type_code: string;
  relationship_label?: string;
  verification_status_code: string;
  verification_evidence_url: string | null;
  corporate_entity_id: string | null;
}

export interface AffiliatePersonRef {
  person_id: string;
  person_name: string;
  person_side_code: string;
  person_side_label?: string;
}

export interface AffiliateNode {
  entity_id: string | null;
  entity_name: string;
  entity_level_code: string | null;
  entity_level_label?: string | null;
  resolved: boolean;
  people: AffiliatePersonRef[];
  children: AffiliateNode[];
}

export interface VocEvidenceCounterparty {
  counterparty_entity_name: string;
  relationship_type_code: string;
  relationship_label: string;
  evidence_excerpt: string | null;
  verification_status_code?: string;
  verification_evidence_url?: string | null;
}

export interface VocEvidence {
  post_id: string;
  voc_type_code: string;
  voc_type_label: string;
  excerpts: string[];
  counterparties: VocEvidenceCounterparty[];
}

export interface RelatedNode {
  node_id: string;
  node_type_code: string;
  relevance: number;
  label?: string;
  person_side_code?: string;
  person_side_label?: string;
  ontology_iri?: string;
  ontology_label?: string;
}

export interface PostRoleResponsibility {
  actor_name: string;
  responsibility: string;
  actor_type_code: string;
  affiliated_organization_name: string | null;
}

export interface PostAiSummary {
  post_id: string;
  korean_summary: string;
  key_events: string[];
  roles_and_responsibilities: PostRoleResponsibility[];
}

export interface LinkedPostRef {
  post_id: string;
  post_title: string;
}

export interface PostLineage {
  post_id: string;
  direct: LinkedPostRef[];
  indirect: LinkedPostRef[];
}

export interface CitedPostRef {
  post_id: string;
  post_title: string;
}

export interface ChatAnswer {
  post_id: string;
  answer_text: string;
  cited_post_ids: string[];
  cited_posts?: CitedPostRef[];
  source_post_ids: string[];
}

export interface ChatExchange {
  question_text: string;
  answer_text: string;
  cited_post_ids: string[];
  cited_posts?: CitedPostRef[];
}

export interface ChatHistory {
  post_id: string;
  exchanges: ChatExchange[];
}

export interface IssueTicket {
  issue_ticket_id: string;
  post_id: string;
  ticket_status_code: string;
  ticket_status_label?: string;
  ticket_title: string;
  assigned_account_id: string | null;
  due_date: string | null;
  commitment_summary: string | null;
  created_at: string;
  updated_at: string;
}

export interface CalendarEntry extends IssueTicket {
  post_title: string;
}

export interface DerivedCommitment {
  post_id: string;
  has_commitment: boolean;
  ticket: IssueTicket | null;
}

export interface ActivityEvent {
  event_id: string;
  event_type: string;
  actor_account_id: string;
  summary: string;
}

export class BackendError extends Error {
  readonly status: number;

  constructor(path: string, status: number, detail?: string) {
    super(detail && detail.trim() ? detail : `${path} -> HTTP ${status}`);
    this.name = "BackendError";
    this.status = status;
  }
}

async function backendFetch<T>(
  path: string,
  accessToken: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${config.backendBaseUrl}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${accessToken}`,
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    let detail: string | undefined;
    try {
      const body: unknown = await response.json();
      if (body && typeof body === "object" && "detail" in body && typeof body.detail === "string") {
        detail = body.detail;
      }
    } catch {
      detail = undefined;
    }
    throw new BackendError(path, response.status, detail);
  }
  return response.json() as Promise<T>;
}

export interface LineageGraphNode {
  id: string;
  group: string;
  label: string;
  occurred_at: string;
  is_root: boolean;
  is_branch_point: boolean;
}

export interface LineageGraphEdge {
  source: string;
  target: string;
  fused_score: number;
}

export interface LineageGraph {
  nodes: LineageGraphNode[];
  edges: LineageGraphEdge[];
}

export function fetchLineageGraph(accessToken: string): Promise<LineageGraph> {
  return backendFetch<LineageGraph>("/api/lineage", accessToken);
}

export interface CurrentUser {
  user_account_id: string;
  display_name: string;
  permission_codes: string[];
}

export function fetchMe(accessToken: string): Promise<CurrentUser> {
  return backendFetch<CurrentUser>("/api/me", accessToken);
}

export function rebuildLineage(accessToken: string): Promise<{ edge_count: number }> {
  return backendFetch("/api/lineage/rebuild", accessToken, { method: "POST" });
}

export function fetchPosts(accessToken: string): Promise<PostSummary[]> {
  return backendFetch<PostSummary[]>("/api/posts", accessToken);
}

export function fetchPost(accessToken: string, postId: string): Promise<PostDetail> {
  return backendFetch<PostDetail>(`/api/posts/${postId}`, accessToken);
}

export function fetchPostKeymen(accessToken: string, postId: string): Promise<{ keymen: Keyman[] }> {
  return backendFetch(`/api/posts/${postId}/keymen`, accessToken);
}

export function fetchPostCounterparties(
  accessToken: string,
  postId: string,
): Promise<{ counterparties: Counterparty[] }> {
  return backendFetch(`/api/posts/${postId}/counterparties`, accessToken);
}

export function fetchPostAffiliateTree(
  accessToken: string,
  postId: string,
): Promise<{ trees: AffiliateNode[] }> {
  return backendFetch(`/api/posts/${postId}/affiliate-tree`, accessToken);
}

export function fetchPostVocEvidence(accessToken: string, postId: string): Promise<VocEvidence> {
  return backendFetch(`/api/posts/${postId}/voc-evidence`, accessToken);
}

export function fetchRelatedKeymen(
  accessToken: string,
  personId: string,
): Promise<{ person_id: string; person_name: string; person_side_code: string; related: RelatedNode[] }> {
  return backendFetch(`/api/keymen/${personId}/related`, accessToken);
}

export function fetchRelatedEntity(
  accessToken: string,
  entityId: string,
): Promise<{ corporate_entity_id: string; entity_name: string; related: RelatedNode[] }> {
  return backendFetch(`/api/corporate-entities/${entityId}/related`, accessToken);
}

export function extractPostKeymen(
  accessToken: string,
  postId: string,
): Promise<{ extracted_count: number }> {
  return backendFetch(`/api/posts/${postId}/extract-keymen`, accessToken, { method: "POST" });
}

export interface VerifiedRelation {
  counterparty_entity_name: string;
  verification_status_code: string;
  verification_evidence_url: string | null;
}

export function verifyPostRelations(
  accessToken: string,
  postId: string,
): Promise<{ verified: VerifiedRelation[] }> {
  return backendFetch(`/api/posts/${postId}/verify-relations`, accessToken, { method: "POST" });
}

export interface EvaluationResponse {
  criterion_code: string;
  criterion_label: string | null;
  response_category: number;
  rubric_version: string;
}

export interface PostEvaluation {
  post_id: string;
  rubric_version: string;
  responses: EvaluationResponse[];
}

export function fetchPostEvaluation(accessToken: string, postId: string): Promise<PostEvaluation> {
  return backendFetch(`/api/posts/${postId}/evaluation`, accessToken);
}

export function evaluatePost(accessToken: string, postId: string): Promise<PostEvaluation> {
  return backendFetch(`/api/posts/${postId}/evaluate`, accessToken, { method: "POST" });
}

export interface ReportMember {
  post_id: string;
  post_title: string;
  theta_eap: number;
  theta_sd: number;
  ticket_due_date?: string | null;
  ticket_title?: string | null;
  ticket_status_code?: string | null;
  ticket_status_label?: string | null;
}

export interface SelectedReportItem {
  item_code: string;
  rank: number;
  information: number;
}

export interface PeriodGroupReport {
  grouping_key: string;
  selected_model: string;
  mean_theta: number;
  mean_theta_sd: number;
  post_count: number;
  item_count: number;
  fit_converged: boolean;
  link_method: string;
  anchor_period_code: string | null;
  delta_mean_theta: number | null;
  members: ReportMember[];
  selected_items: SelectedReportItem[];
}

export interface PeriodReports {
  grouping_kind: string;
  period_code: string;
  reports: PeriodGroupReport[];
}

export interface PeriodReportSummary {
  grouping_key: string;
  period_code: string;
  selected_model: string;
  mean_theta: number;
  post_count: number;
  link_method: string;
  anchor_period_code: string | null;
  delta_mean_theta: number | null;
  selected_item_code: string | null;
  selected_item_information: number | null;
}

export interface PeriodReportIndex {
  grouping_kind: string;
  periods: PeriodReportSummary[];
}

export interface GroupingComparisonRow {
  grouping_kind: string;
  grouping_key: string;
  grouping_label: string;
  mean_theta: number;
  post_count: number;
  link_method: string;
}

export interface PeriodComparison {
  period_code: string;
  groupings: GroupingComparisonRow[];
}

export function fetchPeriodComparison(
  accessToken: string,
  periodCode: string,
): Promise<PeriodComparison> {
  return backendFetch(`/api/reports/compare/${periodCode}`, accessToken);
}

export function fetchPeriodReportIndex(
  accessToken: string,
  groupingKind: string,
): Promise<PeriodReportIndex> {
  return backendFetch(`/api/reports/${groupingKind}`, accessToken);
}

export function fetchPeriodReports(
  accessToken: string,
  groupingKind: string,
  periodCode: string,
): Promise<PeriodReports> {
  return backendFetch(`/api/reports/${groupingKind}/${periodCode}`, accessToken);
}

export function rebuildPeriodReports(
  accessToken: string,
  groupingKind: string,
  periodCode: string,
): Promise<{ group_count: number }> {
  return backendFetch(`/api/reports/${groupingKind}/${periodCode}/rebuild`, accessToken, {
    method: "POST",
  });
}

export function fetchPostSummary(accessToken: string, postId: string): Promise<PostAiSummary> {
  return backendFetch(`/api/posts/${postId}/summary`, accessToken);
}

export function fetchPostLineage(accessToken: string, postId: string): Promise<PostLineage> {
  return backendFetch(`/api/posts/${postId}/lineage`, accessToken);
}

export function fetchPostChat(accessToken: string, postId: string): Promise<ChatHistory> {
  return backendFetch(`/api/posts/${postId}/chat`, accessToken);
}

export function askPostChat(accessToken: string, postId: string, question: string): Promise<ChatAnswer> {
  return backendFetch(`/api/posts/${postId}/chat`, accessToken, {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}

export function fetchPostTickets(accessToken: string, postId: string): Promise<{ tickets: IssueTicket[] }> {
  return backendFetch(`/api/posts/${postId}/tickets`, accessToken);
}

export function createPostTicket(
  accessToken: string,
  postId: string,
  ticketTitle: string,
  ticketStatusCode: string,
  dueDate?: string,
): Promise<IssueTicket> {
  return backendFetch(`/api/posts/${postId}/tickets`, accessToken, {
    method: "POST",
    body: JSON.stringify({
      ticket_title: ticketTitle,
      ticket_status_code: ticketStatusCode,
      ...(dueDate ? { due_date: dueDate } : {}),
    }),
  });
}

export function updateTicketStatus(
  accessToken: string,
  issueTicketId: string,
  ticketStatusCode: string,
): Promise<IssueTicket> {
  return backendFetch(`/api/tickets/${issueTicketId}`, accessToken, {
    method: "PATCH",
    body: JSON.stringify({ ticket_status_code: ticketStatusCode }),
  });
}

export function fetchPostActivity(
  accessToken: string,
  postId: string,
): Promise<{ events: ActivityEvent[] }> {
  return backendFetch(`/api/posts/${postId}/activity`, accessToken);
}

export function deriveCommitment(accessToken: string, postId: string): Promise<DerivedCommitment> {
  return backendFetch(`/api/posts/${postId}/derive-commitment`, accessToken, { method: "POST" });
}

export function fetchCalendar(accessToken: string): Promise<{ commitments: CalendarEntry[] }> {
  return backendFetch("/api/calendar", accessToken);
}

export interface AnalysisRunCount {
  count_type_code: string;
  count_type_label: string;
  count_value: number;
}

/** Registry kinds from `analysis_run.run_kind_code` (migration 0018). */
export type AnalysisRunKindCode =
  | "analysis_run_lineage"
  | "analysis_run_report"
  | "analysis_run_tepp";

/** Kinds `POST /api/analysis-runs` accepts (ADR 0017). Report is display-only. */
export type AnalysisRunCreateKindCode = "analysis_run_lineage" | "analysis_run_tepp";

/** Registry statuses from `analysis_run_status_event.status_code`. */
export type AnalysisRunStatusCode =
  | "analysis_status_pending"
  | "analysis_status_running"
  | "analysis_status_succeeded"
  | "analysis_status_failed"
  | "analysis_status_cancelled";

export interface AnalysisRunStatusEvent {
  status_ordinal: number;
  status_code: AnalysisRunStatusCode;
  status_label: string;
  occurred_at: string;
  failure_code?: string;
}

export interface AnalysisRun {
  analysis_run_id: string;
  run_kind_code: AnalysisRunKindCode;
  run_kind_label: string;
  scope_kind_code: string;
  scope_kind_label: string;
  scope_entity_name?: string;
  status_code: AnalysisRunStatusCode | null;
  status_label: string | null;
  knowledge_cutoff: string;
  requested_at: string;
  source_counts: AnalysisRunCount[];
  status_history?: AnalysisRunStatusEvent[];
  visible_posts?: { post_id: string; post_title: string }[];
  code_revision_sha?: string;
  configuration_sha256?: string;
}

export function fetchAnalysisRuns(accessToken: string): Promise<{ analysis_runs: AnalysisRun[] }> {
  return backendFetch("/api/analysis-runs", accessToken);
}

export function fetchAnalysisRun(accessToken: string, analysisRunId: string): Promise<AnalysisRun> {
  return backendFetch(`/api/analysis-runs/${analysisRunId}`, accessToken);
}

export interface CreateAnalysisRunRequest {
  run_kind_code?: AnalysisRunCreateKindCode;
  scope_kind_code?: string;
  corporate_entity_id?: string;
  knowledge_cutoff?: string;
  idempotency_key: string;
}

export function createAnalysisRun(
  accessToken: string,
  request: CreateAnalysisRunRequest,
): Promise<AnalysisRun> {
  return backendFetch("/api/analysis-runs", accessToken, {
    method: "POST",
    body: JSON.stringify(request),
  });
}
