import { config } from "./config";

export interface PostSummary {
  post_id: string;
  post_title: string;
  voc_type_code: string;
  visibility_code: string;
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
  affiliations: Affiliation[];
}

export interface Counterparty {
  counterparty_entity_name: string;
  relationship_type_code: string;
  relationship_label?: string;
  verification_status_code: string;
  verification_evidence_url: string | null;
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
  ontology_iri?: string;
  ontology_label?: string;
}

export interface PostRoleResponsibility {
  person_name: string;
  responsibility: string;
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

export interface IssueTicket {
  issue_ticket_id: string;
  post_id: string;
  ticket_status_code: string;
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
    throw new Error(`${path} -> HTTP ${response.status}`);
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

export function fetchPostSummary(accessToken: string, postId: string): Promise<PostAiSummary> {
  return backendFetch(`/api/posts/${postId}/summary`, accessToken);
}

export function fetchPostLineage(accessToken: string, postId: string): Promise<PostLineage> {
  return backendFetch(`/api/posts/${postId}/lineage`, accessToken);
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
