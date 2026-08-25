import { config } from "./config";

export interface PostSummary {
  post_id: string;
  post_title: string;
  voc_type_code: string;
  voc_type_label?: string;
  visibility_code: string;
  visibility_label?: string;
  source_stage_code?: string | null;
  source_detail_state_code?: string | null;
  source_draft_code?: string | null;
  source_deleted_flag?: string | null;
  source_author_code?: string | null;
  source_author_name?: string | null;
  source_company_code?: string | null;
  source_company_name?: string | null;
  source_process_unit_code?: string | null;
  source_process_unit_name?: string | null;
  source_sales_pool_code?: string | null;
  source_sales_pool_name?: string | null;
  source_customer_code?: string | null;
  source_customer_name?: string | null;
  source_project_code?: string | null;
  source_project_name?: string | null;
  source_system_code?: string | null;
  source_record_key?: string | null;
  publication_state_code?: string;
  post_body_excerpt?: string | null;
  post_body_truncated?: boolean;
  project_evidence?: ProjectEvidence[];
  created_at: string;
}

export interface PostPage {
  posts: PostSummary[];
  total_count: number;
  limit: number;
  offset: number;
  voc_type_options?: PostFilterOption[];
  visibility_options?: PostFilterOption[];
}

export interface OperationsDashboardFact {
  fact_type_code: string;
  fact_type_label: string;
  value_text: string;
  evidence_text: string;
}

export interface OperationsDashboardCase {
  post_id: string;
  case_kind_code: string;
  case_kind_label: string;
  project_name: string | null;
  summary_text: string;
  evidence_text: string;
  occurred_at: string;
  facts: OperationsDashboardFact[];
}

export interface OperationsDashboardResponse {
  period_label: string;
  total_post_count: number;
  total_event_count: number;
  external_post_count: number;
  external_percent: number;
  pending_analysis_count: number;
  cases: OperationsDashboardCase[];
}

export function fetchOperationsDashboard(
  accessToken: string,
  periodStart = "",
  periodEnd = "",
): Promise<OperationsDashboardResponse> {
  const query = new URLSearchParams();
  if (periodStart) query.set("period_start", periodStart);
  if (periodEnd) query.set("period_end", periodEnd);
  const suffix = query.size ? `?${query}` : "";
  return backendFetch(`/api/dashboard${suffix}`, accessToken);
}

export interface PostFilterOption {
  code: string;
  label: string;
}

export type PostSortOrder = "newest" | "oldest" | "title";

export interface PostKnownAt {
  post_title: string;
  post_body: string;
  written_at: string;
  as_of: string;
}

export interface PostDetail extends PostSummary {
  post_body: string;
  known_at?: PostKnownAt;
}

export interface PostImageContent {
  unit_index: number;
  mime_type: string;
  status_code: string;
  extracted_text: string | null;
  caption: string | null;
  tags: string[];
  regions?: PostImageRegion[];
}

export interface PostImageRegion {
  region_index: number;
  x_ratio: number;
  y_ratio: number;
  width_ratio: number;
  height_ratio: number;
  status_code: string;
  extracted_text: string | null;
  caption: string | null;
  tags: string[];
}

export interface PostContentResponse {
  status?: "ready" | "processing" | "unavailable";
  units: PostContentUnit[];
  images: PostImageContent[];
}

export interface PostContentUnit {
  unit_index: number;
  unit_kind_code: string;
  unit_label?: string;
  unit_text: string;
  indent_level: number;
  indent_source_code: "explicit" | "llm" | "unresolved";
  indent_confidence: number;
  indent_evidence: string;
}

export interface Affiliation {
  organization_name: string;
  corporate_entity_id: string | null;
  role_title: string | null;
  organization_alias?: string;
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
  verification_evidence_post_id: string | null;
  corporate_entity_id: string | null;
  organization_alias?: string;
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
  organization_alias?: string;
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

export type RelatedNodeType =
  | "node_person"
  | "node_post"
  | "node_corporate_entity"
  | "node_team";

export interface RelatedNode {
  node_id: string;
  node_type_code: RelatedNodeType | string;
  relevance: number;
  label?: string;
  organization_alias?: string;
  post_body_excerpt?: string | null;
  post_body_truncated?: boolean;
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
  catalog_node_id?: string | null;
  catalog_node_type_code?: string | null;
}

export interface PostMajorEventAction {
  action_text: string;
  requester_actor_name: string | null;
  processor_actor_name: string | null;
  evidence_text: string;
  project_name?: string | null;
}

export interface PostProjectMention {
  project_key: string;
  project_name: string;
  evidence: string;
  confidence: number;
  ontology_iri: string;
  ontology_label?: string;
  extraction_method: string;
}

export interface ProjectEvidence {
  project_key: string;
  project_name: string;
  evidence: string;
  confidence: number | null;
  ontology_iri: string;
  ontology_label?: string;
  extraction_method: string;
  resolution_status: string;
  provenance: string;
}

export interface PostAiSummary {
  post_id: string;
  korean_summary: string;
  summary_status?: "current" | "stale";
  summary_contract_version?: number | null;
  key_events: string[];
  key_event_details?: PostKeyEvent[];
  roles_and_responsibilities: PostRoleResponsibility[];
  major_event_actions?: PostMajorEventAction[];
  project_mentions?: PostProjectMention[];
}

export interface PostKeyEvent {
  event_text: string;
  project_name?: string | null;
}

export interface FiveW1HValue {
  text: string;
  source: string;
  evidence_text?: string;
  ontology_codes: string[];
  ontology_annotations: Record<string, string>;
}

export interface FiveW1HSlot {
  slot_code: "who" | "what" | "when" | "where" | "why" | "how";
  values: FiveW1HValue[];
  empty_next_action_code: string;
}

export interface PostFiveW1H {
  post_id: string;
  slots: FiveW1HSlot[];
}

export interface LinkedPostRef {
  post_id: string;
  post_title: string;
  post_body_excerpt?: string | null;
  post_body_truncated?: boolean;
  interval_relation_code?: string;
  interval_relation_label?: string;
  interval_is_parent?: boolean;
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

export interface CitedPostEvidenceFact {
  kind: string;
  text: string;
}

export interface CitedPostEvidence {
  post_id: string;
  facts: CitedPostEvidenceFact[];
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

export interface CitedPostImage {
  post_id: string;
  unit_index: number;
  mime_type: string;
  status_code: string;
  extracted_text: string | null;
  caption: string | null;
  tags: string[];
}

export interface AskAgentResponse {
  answer_text: string;
  cited_post_ids: string[];
  cited_posts?: CitedPostRef[];
  cited_post_evidence?: CitedPostEvidence[];
  cited_post_images?: CitedPostImage[];
  source_post_ids: string[];
  next_action?: string;
  lineage_graph?: LineageGraph;
  delivery?: {
    contract_version: string;
    report: {
      media_type: string;
      body: string;
      source_documents: Array<{
        post_id: string;
        title: string;
        api_path: string;
        resource_uri: string;
        evidence_facts: CitedPostEvidenceFact[];
      }>;
    };
    alert: {
      trigger_code: string;
      delivery_status_code: string;
      eligible: boolean;
      watched_resource_uris: string[];
    };
  };
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

export interface NaruonCalendarEvent {
  occurrence_reference: string;
  event_reference: string;
  source_reference: string;
  display_text: string;
  starts_at: string;
  ends_at: string;
  all_day: boolean;
  time_zone: string;
  status_code: string;
  disclosure_code: string;
  truth_status_code: string;
  observed_at: string;
  provider_revision: string;
}

export interface CalendarResponse {
  events: NaruonCalendarEvent[];
  commitments: CalendarEntry[];
  calendar_sources: {
    naruon_available: boolean;
    naruon_next_action: string | null;
  };
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
    const message =
      status === 0
        ? "The service is unreachable. Try again later."
        : status >= 500
          ? "The service could not complete this request. Try again later."
          : detail && detail.trim()
            ? detail
            : `${path} -> HTTP ${status}`;
    super(message);
    this.name = "BackendError";
    this.status = status;
  }
}

async function backendFetch<T>(
  path: string,
  accessToken: string,
  init?: RequestInit,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${config.backendBaseUrl}${path}`, {
      ...init,
      headers: {
        Authorization: `Bearer ${accessToken}`,
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...init?.headers,
      },
    });
  } catch {
    throw new BackendError(path, 0);
  }
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
  interval_relation_code?: string;
  interval_relation_label?: string;
}

export interface LineageGraph {
  nodes: LineageGraphNode[];
  edges: LineageGraphEdge[];
  truncated?: boolean;
  isolation_reason?: "comparison_candidates_available" | "no_comparison_group" | null;
}

export function fetchLineageGraph(accessToken: string, postId?: string): Promise<LineageGraph> {
  const query = postId ? `?post_id=${encodeURIComponent(postId)}` : "";
  return backendFetch<LineageGraph>(`/api/lineage${query}`, accessToken);
}

export interface CorporateEntityRef {
  corporate_entity_id: string;
  entity_name: string;
}

export interface CustomerMasterEntity extends CorporateEntityRef {
  corporate_entity_code: string;
  entity_level_code: string;
  entity_level_label: string;
  parent_entity_id: string | null;
}

export interface CustomerMasterKeymanAffiliation {
  organization_name: string;
  corporate_entity_id: string | null;
  entity_name: string | null;
  role_title: string | null;
}

export interface CustomerMasterKeyman {
  person_id: string;
  person_name: string;
  person_side_code: string;
  person_side_label: string;
  last_known_job_title: string | null;
  affiliations: CustomerMasterKeymanAffiliation[];
}

export interface SourceCustomerHint {
  customer_code: string | null;
  customer_name: string | null;
  post_count: number;
  related_posts: LinkedPostRef[];
  resolution_status: string;
  hint_trust: string;
  provenance: string;
}

export interface SourceAuthorAffiliation {
  corporate_entity_id: string;
  entity_name: string;
  process_unit_code: string | null;
  process_unit_name: string | null;
}

export interface SourceAuthorContext {
  author_account_id: string;
  account_display_name: string;
  source_author_code: string | null;
  source_author_name: string | null;
  account_affiliations: SourceAuthorAffiliation[];
  resolution_status: string;
  provenance: string;
}

export interface SourceAuthorKeymanHint {
  person_id: string;
  person_name: string;
  person_side_code: string;
  last_known_job_title: string | null;
  mention_count: number;
  provenance: string;
}

export interface SourceAuthorHint {
  author_code: string;
  author_name: string | null;
  author_account_id: string;
  account_display_name: string;
  account_affiliations: SourceAuthorAffiliation[];
  post_count: number;
  keyman_hints: SourceAuthorKeymanHint[];
  related_posts: LinkedPostRef[];
  resolution_status: string;
  provenance: string;
}

export interface CounterpartyRelationshipRole {
  relationship_type_code: string;
  relationship_label: string;
  post_count: number;
}

export interface RelationshipNetworkEntry {
  counterparty_entity_name: string;
  corporate_entity_id: string | null;
  total_post_count: number;
  relationships: CounterpartyRelationshipRole[];
  multi_role: boolean;
}

export interface CustomerMasterResponse {
  corporate_entities: CustomerMasterEntity[];
  keymen: CustomerMasterKeyman[];
  source_customer_hints: SourceCustomerHint[];
  source_author_hints: SourceAuthorHint[];
  relationship_network: RelationshipNetworkEntry[];
}

export interface CurrentUser {
  user_account_id: string;
  display_name: string;
  permission_codes: string[];
  corporate_entities?: CorporateEntityRef[];
  preferred_locale?: string | null;
}

export function fetchMe(accessToken: string): Promise<CurrentUser> {
  return backendFetch<CurrentUser>("/api/me", accessToken);
}

export function setPreferredLocale(
  accessToken: string,
  preferredLocale: string,
): Promise<{ preferred_locale: string }> {
  return backendFetch<{ preferred_locale: string }>("/api/me/preferences", accessToken, {
    method: "PATCH",
    body: JSON.stringify({ preferred_locale: preferredLocale }),
  });
}

export function fetchCustomerMaster(accessToken: string): Promise<CustomerMasterResponse> {
  return backendFetch<CustomerMasterResponse>("/api/customer-master", accessToken);
}

export interface CustomerHintResolution {
  corporate_entity_id: string;
  entity_name: string;
  linked_post_count: number;
  verification_evidence_url: string | null;
}

export function resolveCustomerHint(
  accessToken: string,
  hintCode: string,
): Promise<CustomerHintResolution> {
  return backendFetch<CustomerHintResolution>("/api/customer-master/resolve-hint", accessToken, {
    method: "POST",
    body: JSON.stringify({ hint_code: hintCode }),
  });
}

export function rebuildLineage(accessToken: string): Promise<{ edge_count: number }> {
  return backendFetch("/api/lineage/rebuild", accessToken, { method: "POST" });
}

export function fetchPosts(
  accessToken: string,
  limit?: number,
  offset?: number,
  search?: string,
  vocTypes?: string[],
  visibility?: string,
  sort?: PostSortOrder,
): Promise<PostPage> {
  const params = new URLSearchParams();
  if (limit !== undefined) {
    params.set("limit", String(limit));
    params.set("offset", String(offset ?? 0));
  }
  if (search?.trim()) {
    params.set("search", search.trim());
  }
  for (const vocType of vocTypes ?? []) {
    params.append("voc_type", vocType);
  }
  if (visibility) {
    params.set("visibility", visibility);
  }
  if (sort) {
    params.set("sort", sort);
  }
  const query = params.toString();
  return backendFetch<PostPage | PostSummary[]>(`/api/posts${query ? `?${query}` : ""}`, accessToken).then(
    (payload) =>
      Array.isArray(payload)
        ? { posts: payload, total_count: payload.length, limit: limit ?? payload.length, offset: offset ?? 0 }
        : payload,
  );
}

export function fetchPost(
  accessToken: string,
  postId: string,
  asOf?: string,
): Promise<PostDetail> {
  const query = asOf ? `?as_of=${encodeURIComponent(asOf)}` : "";
  return backendFetch<PostDetail>(`/api/posts/${postId}${query}`, accessToken);
}

export function fetchPostContent(accessToken: string, postId: string): Promise<PostContentResponse> {
  return backendFetch<PostContentResponse>(`/api/posts/${postId}/content`, accessToken);
}

export interface PostBookmark {
  post_id: string;
  bookmarked: boolean;
}

export function fetchPostBookmark(accessToken: string, postId: string): Promise<PostBookmark> {
  return backendFetch(`/api/posts/${postId}/bookmark`, accessToken);
}

export function setPostBookmark(
  accessToken: string,
  postId: string,
  bookmarked: boolean,
): Promise<PostBookmark> {
  return backendFetch(`/api/posts/${postId}/bookmark`, accessToken, {
    method: "POST",
    body: JSON.stringify({ bookmarked }),
  });
}

export function fetchPostKeymen(
  accessToken: string,
  postId: string,
): Promise<{ keymen: Keyman[]; source_author_context?: SourceAuthorContext | null }> {
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

export interface SimilarVocItem {
  post_id: string;
  post_title: string;
  issue_summary: string;
  focal_evidence_text: string;
  candidate_evidence_text: string;
  customer_cohort_text: string | null;
  action_history: string[];
  occurred_at: string;
}

export function fetchSimilarVoc(
  accessToken: string,
  postId: string,
  offset = 0,
): Promise<{ items: SimilarVocItem[]; next_offset: number | null }> {
  const query = offset ? `?offset=${offset}` : "";
  return backendFetch(`/api/posts/${postId}/similar-voc${query}`, accessToken);
}

export interface PersonRoleHistoryEntry {
  post_id: string;
  post_title: string;
  created_at: string;
  responsibility: string;
  affiliated_organization_name: string | null;
}

export function fetchRelatedKeymen(
  accessToken: string,
  personId: string,
): Promise<{
  person_id: string;
  person_name: string;
  person_side_code: string;
  related: RelatedNode[];
  role_history?: PersonRoleHistoryEntry[];
}> {
  return backendFetch(`/api/keymen/${personId}/related`, accessToken);
}

export function fetchRelatedEntity(
  accessToken: string,
  entityId: string,
): Promise<{ corporate_entity_id: string; entity_name: string; related: RelatedNode[] }> {
  return backendFetch(`/api/corporate-entities/${entityId}/related`, accessToken);
}

export function fetchRelatedTeam(
  accessToken: string,
  teamId: string,
): Promise<{ team_id: string; team_name: string; related: RelatedNode[] }> {
  return backendFetch(`/api/teams/${teamId}/related`, accessToken);
}

export interface OntologyGraphNodePayload {
  node_id: string;
  node_type_code: string;
  ontology_class_iri: string;
  display_label: string;
  truth_status_code: string | null;
  valid_from: string | null;
  valid_to: string | null;
  recorded_at: string | null;
  evidence_count: number;
  shape_code: string;
}

export interface OntologyGraphEdgePayload {
  edge_id: string;
  source_node_type_code: string;
  source_node_id: string;
  target_node_type_code: string;
  target_node_id: string;
  property_code: string;
  ontology_property_iri: string;
  property_label: string;
  truth_status_code: string;
  valid_from: string | null;
  valid_to: string | null;
  recorded_at: string;
  provenance_reference: string | null;
  evidence_references: string[];
}

export interface OntologyExactValueRow {
  edge_id: string;
  source_node_id: string;
  source_label: string;
  source_type_code: string;
  property_code: string;
  property_label: string;
  ontology_property_iri: string;
  target_node_id: string;
  target_label: string;
  target_type_code: string;
  truth_status_code: string;
  recorded_at: string;
  valid_from: string;
  valid_to: string;
  evidence_count: string;
}

export interface OntologyNeighborhoodPayload {
  focus_node_id: string;
  focus_node_type_code: string;
  truncated: boolean;
  next_cursor: string | null;
  limitation_code: string | null;
  nodes: OntologyGraphNodePayload[];
  edges: OntologyGraphEdgePayload[];
  exact_value_rows: OntologyExactValueRow[];
  jsonld: Record<string, unknown>;
}

export interface OntologyNeighborhoodQuery {
  focusNodeType: string;
  focusNodeId: string;
  maximumDepth?: number;
  maximumNodes?: number;
  maximumEdges?: number;
  allowedPropertyCodes?: string[];
  knowledgeCutoff?: string;
  cursor?: string;
}

export function fetchOntologyNeighborhood(
  accessToken: string,
  query: OntologyNeighborhoodQuery,
): Promise<OntologyNeighborhoodPayload> {
  const params = new URLSearchParams({
    focus_node_type: query.focusNodeType,
    focus_node_id: query.focusNodeId,
  });
  if (query.maximumDepth != null) params.set("maximum_depth", String(query.maximumDepth));
  if (query.maximumNodes != null) params.set("maximum_nodes", String(query.maximumNodes));
  if (query.maximumEdges != null) params.set("maximum_edges", String(query.maximumEdges));
  if (query.knowledgeCutoff) params.set("knowledge_cutoff", query.knowledgeCutoff);
  if (query.cursor) params.set("cursor", query.cursor);
  for (const code of query.allowedPropertyCodes ?? []) {
    params.append("allowed_property_codes", code);
  }
  return backendFetch(`/api/ontology/neighborhood?${params.toString()}`, accessToken);
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
  verification_evidence_post_id: string | null;
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

export interface LeftoverPair {
  pair_kind: "closest" | "farthest" | string;
  post_id: string;
  post_title: string;
  criterion_code: string;
  leftover_distance: number;
  leftover_residual: number;
  observed_response?: number | null;
  expected_response?: number | null;
  leftover_map_rank?: number | null;
  leftover_map_unexplained?: number | null;
  leftover_map_cross_share?: number | null;
  leftover_map_reconstruction?: number | null;
}

export interface LeftoverMapAxis {
  axis_index: number;
  leftover_singular_value: number;
  leftover_share: number;
}

export interface LeftoverMapCoverage {
  map_post_count: number;
  scored_post_count: number;
  map_item_count: number;
  scored_item_count: number;
  incomplete_post_count: number;
  incomplete_item_count: number;
}

export interface PeriodGroupReport {
  grouping_key: string;
  grouping_label?: string;
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
  leftover_pairs: LeftoverPair[];
  leftover_map_axes?: LeftoverMapAxis[];
  leftover_map_coverage?: LeftoverMapCoverage | null;
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
  leftover_pairs?: LeftoverPair[];
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

export function fetchPostFiveW1H(accessToken: string, postId: string): Promise<PostFiveW1H> {
  return backendFetch(`/api/posts/${postId}/five-w1h`, accessToken);
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

/** How often the queued Ask job is polled, and for how long overall.
 * A live orchestrator answer can take minutes under shared-gateway load,
 * so the ceiling is generous; the poll interval keeps the reader's
 * "Thinking..." state honest without hammering the backend. */
const ASK_POLL_INTERVAL_MS = 2000;
// Must exceed the backend's whole pipeline for one job — queue wait plus
// the 600 s job deadline — and the e2e suite's own answer deadline, so a
// stored answer is never abandoned by the client that asked for it.
const ASK_POLL_CEILING_MS = 15 * 60 * 1000;

interface AskJobStatus {
  ask_job_id: string;
  job_status_code: "queued" | "running" | "succeeded" | "failed";
  answer?: AskAgentResponse;
  failure_detail?: string | null;
}

/** Submit the question as an asynchronous job and poll it to completion.
 * The signature and resolved value are unchanged from the old synchronous
 * call, so callers (AskAgentPanel) keep their existing pending/complete
 * states without modification. */
export async function askAgent(accessToken: string, question: string): Promise<AskAgentResponse> {
  const submitted = await backendFetch<AskJobStatus>("/api/ask", accessToken, {
    method: "POST",
    body: JSON.stringify({ question }),
  });
  const deadline = Date.now() + ASK_POLL_CEILING_MS;
  for (;;) {
    const job = await backendFetch<AskJobStatus>(
      `/api/ask/jobs/${submitted.ask_job_id}`,
      accessToken,
    );
    if (job.job_status_code === "succeeded" && job.answer) {
      return job.answer;
    }
    if (job.job_status_code === "failed") {
      throw new Error(job.failure_detail || "Ask Agent could not answer this question.");
    }
    if (Date.now() > deadline) {
      throw new Error("Ask Agent timed out waiting for an answer. Try again.");
    }
    await new Promise((resolve) => setTimeout(resolve, ASK_POLL_INTERVAL_MS));
  }
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

export function fetchCalendar(accessToken: string): Promise<CalendarResponse> {
  return backendFetch("/api/calendar", accessToken);
}

export interface AnalysisRunCount {
  count_type_code: string;
  count_type_label: string;
  count_value: number;
}

/** Registry kinds from `analysis_run.run_kind_code` (migration 0018, extended 0131). */
export type AnalysisRunKindCode =
  | "analysis_run_lineage"
  | "analysis_run_report"
  | "analysis_run_tepp"
  | "analysis_run_topic_lineage";

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

export interface AnalysisRunOutboxDelivery {
  delivery_ordinal: number;
  delivery_status_code: string;
  delivery_status_label: string;
  occurred_at: string;
}

export interface AnalysisRunReconstructedEdge {
  parent_post_id: string;
  parent_post_title: string;
  child_post_id: string;
  child_post_title: string;
  fused_score: number;
}

export interface AnalysisRunVisiblePost {
  post_id: string;
  post_title: string;
  updated_at?: string;
  live_after_cutoff?: boolean;
}

export interface AnalysisRun {
  analysis_run_id: string;
  run_kind_code: AnalysisRunKindCode;
  run_kind_label: string;
  scope_kind_code: string;
  scope_kind_label: string;
  scope_entity_name?: string;
  scope_key?: string;
  scope_grouping_key?: string;
  status_code: AnalysisRunStatusCode | null;
  status_label: string | null;
  failure_code?: string;
  knowledge_cutoff: string;
  requested_at: string;
  source_counts: AnalysisRunCount[];
  status_history?: AnalysisRunStatusEvent[];
  outbox_deliveries?: AnalysisRunOutboxDelivery[];
  visible_posts?: AnalysisRunVisiblePost[];
  reconstructed_edges?: AnalysisRunReconstructedEdge[];
  reconstruction_result_sha256?: string;
  topic_lineage_result?: Record<string, unknown>;
  topic_lineage_result_sha256?: string;
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
  run_kind_code?: string;
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

export function startAnalysisRun(
  accessToken: string,
  analysisRunId: string,
): Promise<AnalysisRun> {
  return backendFetch(`/api/analysis-runs/${analysisRunId}/start`, accessToken, {
    method: "POST",
  });
}

export interface RankingChannelEvidence {
  signal_code: string;
  signal_label: string;
  channel_rank: number;
  weight: number;
  contribution: number;
  rank: number;
}

export interface RankedPost {
  post_id: string;
  post_title: string;
  fused_rank: number;
  channel_evidence?: RankingChannelEvidence[];
}

export interface RankingList {
  port: string;
  status: "accepted" | "unavailable";
  status_reason: string | null;
  rankings: RankedPost[];
}

export function fetchRankings(accessToken: string): Promise<RankingList> {
  return backendFetch("/api/rankings", accessToken);
}

export function fetchTenantConfig(accessToken: string): Promise<{ brandName: string }> {
  return backendFetch("/api/settings", accessToken);
}

export function updateTenantConfig(
  accessToken: string,
  brandName: string,
): Promise<{ brandName: string }> {
  return backendFetch("/api/settings", accessToken, {
    method: "PATCH",
    body: JSON.stringify({ brandName }),
  });
}
