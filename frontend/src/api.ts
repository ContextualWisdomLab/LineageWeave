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
  mention_context: string | null;
  affiliations: Affiliation[];
}

export interface Counterparty {
  counterparty_entity_name: string;
  relationship_type_code: string;
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

export interface ChatAnswer {
  post_id: string;
  answer_text: string;
  cited_post_ids: string[];
  source_post_ids: string[];
}

export interface IssueTicket {
  issue_ticket_id: string;
  post_id: string;
  ticket_status_code: string;
  ticket_title: string;
  assigned_account_id: string | null;
  created_at: string;
  updated_at: string;
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
): Promise<IssueTicket> {
  return backendFetch(`/api/posts/${postId}/tickets`, accessToken, {
    method: "POST",
    body: JSON.stringify({ ticket_title: ticketTitle, ticket_status_code: ticketStatusCode }),
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
