import { useEffect, useRef, useState, type ReactNode } from "react";
import { useAuth } from "react-oidc-context";
import {
  askPostChat,
  BackendError,
  createAnalysisRun,
  startAnalysisRun,
  createPostTicket,
  deriveCommitment,
  evaluatePost,
  extractPostKeymen,
  fetchAnalysisRun,
  fetchAnalysisRuns,
  fetchCalendar,
  fetchLineageGraph,
  fetchMe,
  fetchPost,
  fetchPostActivity,
  fetchPostChat,
  fetchPostAffiliateTree,
  fetchPostCounterparties,
  fetchPostEvaluation,
  fetchPostKeymen,
  fetchPostLineage,
  fetchPostSummary,
  fetchPostTickets,
  fetchPostVocEvidence,
  fetchPeriodComparison,
  fetchPeriodReportIndex,
  fetchPeriodReports,
  fetchPosts,
  fetchRelatedEntity,
  fetchRelatedKeymen,
  fetchRelatedTeam,
  rebuildLineage,
  rebuildPeriodReports,
  updateTicketStatus,
  verifyPostRelations,
  type ActivityEvent,
  type AffiliateNode,
  type AnalysisRun,
  type CalendarEntry,
  type ChatAnswer,
  type ChatExchange,
  type Counterparty,
  type EvaluationResponse,
  type IssueTicket,
  type LineageGraph,
  type Keyman,
  type LinkedPostRef,
  type PostAiSummary,
  type PostDetail,
  type PeriodComparison,
  type PeriodReportIndex,
  type PeriodReports,
  type PostLineage,
  type PostSummary,
  type RelatedNode,
  type RelatedNodeType,
  type VocEvidence,
} from "./api";
import { LineageDag } from "./LineageDag";
import { PostBody } from "./PostBody";
import { subgraphForPost } from "./lineageLayout";
import "./App.css";

function orchestratorUnavailableMessage(err: unknown, action: string): string {
  if (err instanceof BackendError && err.status === 503) {
    return `${action} unavailable (LLM orchestrator not configured).`;
  }
  return String(err);
}

function searchUnavailableMessage(err: unknown): string {
  if (err instanceof BackendError && err.status === 503) {
    return "Verification unavailable (search is not configured).";
  }
  return String(err);
}

const CRITERION_SHORT_LABEL: Record<string, string> = {
  general_sentiment_positive: "constructive",
  general_sentiment_negative: "negative",
  sales_lead_specificity: "sales-lead",
};

function criterionShortLabel(itemCode: string): string {
  return CRITERION_SHORT_LABEL[itemCode] ?? itemCode;
}

// This popup's layout follows the textual product brief (Korean summary,
// key events, R&R, Event Lineage, Keyman, in-popup chat with a sliding
// evidence panel) rather than the referenced Figma frame's actual pixel
// layout -- see ADR 0002 for why (the file's own content is the source
// organization's confidential material, and does not yet contain a frame
// for this screen).

function EvidencePanel({
  postId,
  accessToken,
  onClose,
}: {
  postId: string;
  accessToken: string;
  onClose: () => void;
}) {
  const [post, setPost] = useState<PostDetail | null>(null);

  useEffect(() => {
    setPost(null);
    fetchPost(accessToken, postId).then(setPost).catch(() => setPost(null));
  }, [postId, accessToken]);

  return (
    <div className="evidence-panel" role="complementary" aria-label="Evidence">
      <button className="popup-close" onClick={onClose} aria-label="Close evidence panel">
        &times;
      </button>
      <h3>Evidence</h3>
      {!post && <p>Loading source post...</p>}
      {post && (
        <>
          <h4>{post.post_title}</h4>
          <PostBody body={post.post_body} />
        </>
      )}
    </div>
  );
}

function ChatCitations({
  citedPosts,
  citedPostIds,
  onOpenEvidence,
}: {
  citedPosts?: { post_id: string; post_title: string }[];
  citedPostIds: string[];
  onOpenEvidence: (postId: string) => void;
}) {
  if ((citedPosts?.length ?? citedPostIds.length) === 0) return null;
  const chips =
    citedPosts ?? citedPostIds.map((post_id) => ({ post_id, post_title: post_id.slice(0, 8) }));
  return (
    <div className="chat-citations">
      <span>Sources: </span>
      {chips.map((cited) => (
        <button
          key={cited.post_id}
          className="citation-chip"
          aria-label={`Open evidence: ${cited.post_title}`}
          onClick={() => onOpenEvidence(cited.post_id)}
        >
          {cited.post_title}
        </button>
      ))}
    </div>
  );
}

function ChatPanel({ postId, accessToken }: { postId: string; accessToken: string }) {
  const [question, setQuestion] = useState("");
  const [exchanges, setExchanges] = useState<ChatExchange[]>([]);
  const [answer, setAnswer] = useState<ChatAnswer | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [evidencePostId, setEvidencePostId] = useState<string | null>(null);
  const [seededOnly, setSeededOnly] = useState(false);

  useEffect(() => {
    setExchanges([]);
    setAnswer(null);
    setError(null);
    setSeededOnly(false);
    fetchPostChat(accessToken, postId)
      .then((history) => setExchanges(history.exchanges))
      .catch(() => setExchanges([]));
  }, [postId, accessToken]);

  async function handleAsk(asked = question) {
    if (!asked.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await askPostChat(accessToken, postId, asked);
      setAnswer(result);
      setExchanges((prev) => {
        const next: ChatExchange = {
          question_text: asked.trim(),
          answer_text: result.answer_text,
          cited_post_ids: result.cited_post_ids,
          cited_posts: result.cited_posts,
        };
        return [...prev.filter((row) => row.question_text !== next.question_text), next];
      });
    } catch (err) {
      setError(orchestratorUnavailableMessage(err, "Chat"));
      if (err instanceof BackendError && err.status === 503) {
        setSeededOnly(true);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="popup-section chat-section">
      <h3>Ask about this lineage</h3>
      {!seededOnly && (
        <div className="chat-input-row">
          <input
            type="text"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => event.key === "Enter" && handleAsk()}
            placeholder="What happened between these events?"
          />
          <button onClick={() => handleAsk()} disabled={loading || !question.trim()}>
            {loading ? "Asking..." : "Ask"}
          </button>
        </div>
      )}
      {seededOnly && exchanges.length > 0 && (
        <p className="popup-placeholder">Only seeded questions can be answered without an orchestrator.</p>
      )}
      {exchanges.length > 0 && (
        <div className="chat-suggestions">
          {exchanges.map((exchange) => (
            <button
              key={exchange.question_text}
              className="chat-suggestion-chip"
              aria-label={`Ask seeded question: ${exchange.question_text}`}
              onClick={() => {
                if (seededOnly) return;
                setQuestion(exchange.question_text);
                void handleAsk(exchange.question_text);
              }}
            >
              {exchange.question_text}
            </button>
          ))}
        </div>
      )}
      {error && <p className="error">{error}</p>}
      {exchanges.map((exchange) => (
        <div key={`seeded-${exchange.question_text}`} className="chat-answer">
          <p className="chat-question">{exchange.question_text}</p>
          <p>{exchange.answer_text}</p>
          <ChatCitations
            citedPosts={exchange.cited_posts}
            citedPostIds={exchange.cited_post_ids}
            onOpenEvidence={setEvidencePostId}
          />
        </div>
      ))}
      {answer && !exchanges.some((row) => row.answer_text === answer.answer_text) && (
        <div className="chat-answer">
          <p>{answer.answer_text}</p>
          <ChatCitations
            citedPosts={answer.cited_posts}
            citedPostIds={answer.cited_post_ids}
            onOpenEvidence={setEvidencePostId}
          />
        </div>
      )}
      {evidencePostId && (
        <EvidencePanel
          postId={evidencePostId}
          accessToken={accessToken}
          onClose={() => setEvidencePostId(null)}
        />
      )}
    </section>
  );
}

function EventLineageSection({
  lineage,
  graph,
  postId,
  onSelectPost,
}: {
  lineage: PostLineage | null;
  graph: LineageGraph | null;
  postId: string;
  onSelectPost?: (postId: string) => void;
}) {
  if (!lineage) return <p>Loading lineage...</p>;
  const scoped = graph ? subgraphForPost(graph, postId) : { nodes: [], edges: [] };
  const renderLink = (post: LinkedPostRef, kind: "direct" | "indirect") => (
    <li key={post.post_id} className={`lineage-link lineage-link-${kind}`}>
      <span className="lineage-badge">{kind === "direct" ? "직접" : "간접"}</span>
      {onSelectPost ? (
        <button className="lineage-link-button" onClick={() => onSelectPost(post.post_id)}>
          {post.post_title}
        </button>
      ) : (
        post.post_title
      )}
    </li>
  );
  const hasLinks = lineage.direct.length > 0 || lineage.indirect.length > 0;
  if (scoped.nodes.length === 0 && !hasLinks) {
    return <p className="lineage-empty">No linked posts yet.</p>;
  }
  return (
    <>
      {scoped.nodes.length > 0 && onSelectPost && (
        <LineageDag graph={scoped} onSelectPost={onSelectPost} />
      )}
      {hasLinks && (
        <ul className="lineage-list">
          {lineage.direct.map((post) => renderLink(post, "direct"))}
          {lineage.indirect.map((post) => renderLink(post, "indirect"))}
        </ul>
      )}
    </>
  );
}

function AffiliateTreeNode({
  node,
  onSelectPerson,
  onSelectEntity,
}: {
  node: AffiliateNode;
  onSelectPerson?: (personId: string, personName: string) => void;
  onSelectEntity?: (entityId: string, entityName: string) => void;
}) {
  return (
    <li>
      <span className={node.resolved ? "affiliate-resolved" : "affiliate-unresolved"}>
        {node.resolved && node.entity_id && onSelectEntity ? (
          <button
            className="keyman-select"
            aria-label={`Affiliate org: ${node.entity_name}`}
            onClick={() => {
              if (node.entity_id) onSelectEntity(node.entity_id, node.entity_name);
            }}
          >
            {node.entity_name}
          </button>
        ) : (
          node.entity_name
        )}
      </span>
      {(node.entity_level_label || node.entity_level_code) && (
        <span className="affiliate-level"> ({node.entity_level_label ?? node.entity_level_code})</span>
      )}
      {!node.resolved && <span className="affiliate-unresolved-mark"> unresolved</span>}
      {node.people.length > 0 && (
        <span className="keyman-affiliations">
          {" -- "}
          {node.people.map((person, index) => (
            <span key={person.person_id}>
              {index > 0 ? ", " : null}
              {onSelectPerson ? (
                <button
                  className="keyman-select"
                  aria-label={`Affiliate Keyman: ${person.person_name}`}
                  onClick={() => onSelectPerson(person.person_id, person.person_name)}
                >
                  {person.person_name} ({person.person_side_label ?? person.person_side_code})
                </button>
              ) : (
                `${person.person_name} (${person.person_side_label ?? person.person_side_code})`
              )}
            </span>
          ))}
        </span>
      )}
      {node.children.length > 0 && (
        <ul>
          {node.children.map((child) => (
            <AffiliateTreeNode
              key={child.entity_id ?? child.entity_name}
              node={child}
              onSelectPerson={onSelectPerson}
              onSelectEntity={onSelectEntity}
            />
          ))}
        </ul>
      )}
    </li>
  );
}

function peopleOnAffiliateOrg(
  trees: AffiliateNode[] | null,
  organizationName: string,
): { personId: string; personName: string }[] {
  if (!trees) return [];
  const found: { personId: string; personName: string }[] = [];
  const walk = (nodes: AffiliateNode[]) => {
    for (const node of nodes) {
      if (node.entity_name === organizationName) {
        for (const person of node.people) {
          found.push({ personId: person.person_id, personName: person.person_name });
        }
      }
      walk(node.children);
    }
  };
  walk(trees);
  return found;
}

function VocEvidenceSection({
  evidence,
  affiliateTrees,
  onSelectPerson,
}: {
  evidence: VocEvidence | null;
  affiliateTrees: AffiliateNode[] | null;
  onSelectPerson: (personId: string, personName: string) => void;
}) {
  if (!evidence) return <p>Loading VOC evidence...</p>;
  const assignedExcerpts = new Set(
    evidence.counterparties
      .map((row) => row.evidence_excerpt)
      .filter((excerpt): excerpt is string => Boolean(excerpt)),
  );
  const unassignedExcerpts = evidence.excerpts.filter((excerpt) => !assignedExcerpts.has(excerpt));
  const hasExcerpt = evidence.excerpts.length > 0 || assignedExcerpts.size > 0;
  return (
    <section className="popup-section">
      <h3>VOC evidence</h3>
      <p className="post-meta">
        {evidence.voc_type_label} ({evidence.voc_type_code})
      </p>
      {!hasExcerpt ? (
        <p className="popup-placeholder">No extractive excerpt -- no named organization appears in this post.</p>
      ) : unassignedExcerpts.length > 0 ? (
        <ul className="voc-excerpt-list">
          {unassignedExcerpts.map((excerpt) => (
            <li key={excerpt}>
              <blockquote>{excerpt}</blockquote>
            </li>
          ))}
        </ul>
      ) : null}
      {evidence.counterparties.map((row) => {
        const people = peopleOnAffiliateOrg(affiliateTrees, row.counterparty_entity_name);
        const person = people[0];
        return (
          <div key={row.counterparty_entity_name} className="voc-counterparty">
            <p>
              {person ? (
                <button
                  className="keyman-select"
                  aria-label={`VOC Keyman: ${row.counterparty_entity_name}`}
                  onClick={() => onSelectPerson(person.personId, person.personName)}
                >
                  {row.counterparty_entity_name}
                </button>
              ) : (
                row.counterparty_entity_name
              )}{" "}
              -- {row.relationship_label}
              {" -- "}
              <VerificationBadge
                statusCode={row.verification_status_code ?? "verify_pending"}
                evidenceUrl={row.verification_evidence_url}
                ariaLabel={`VOC verification: ${row.counterparty_entity_name}`}
              />
            </p>
            {row.evidence_excerpt ? (
              <blockquote className="voc-counterparty-excerpt">{row.evidence_excerpt}</blockquote>
            ) : null}
          </div>
        );
      })}
    </section>
  );
}

const NODE_PERSON = "node_person";
const NODE_POST = "node_post";
const NODE_CORPORATE_ENTITY = "node_corporate_entity";
const NODE_TEAM = "node_team";

const KNOWN_RELATED_NODE_TYPES = [NODE_PERSON, NODE_POST, NODE_CORPORATE_ENTITY, NODE_TEAM] as const;

function isKnownRelatedNodeType(code: string): code is RelatedNodeType {
  return (KNOWN_RELATED_NODE_TYPES as readonly string[]).includes(code);
}

function relatedNodeCaption(node: RelatedNode): string {
  const name = node.label ?? node.node_id;
  if (node.node_type_code === NODE_PERSON) {
    const side = node.person_side_label ?? node.person_side_code;
    if (side) {
      return `${name} (${side})`;
    }
  }
  return `${name} (${node.ontology_label ?? node.node_type_code})`;
}

const VERIFICATION_BADGE: Record<string, string> = {
  verify_pending: "Not yet checked",
  verify_corroborated: "Corroborated",
  verify_uncorroborated: "No evidence found",
};

function safeHttpUrl(value: string | null | undefined): string | null {
  if (!value) return null;
  try {
    const parsed = new URL(value);
    if (parsed.protocol === "http:" || parsed.protocol === "https:") {
      return parsed.href;
    }
  } catch {
    return null;
  }
  return null;
}

function VerificationBadge({
  statusCode,
  evidenceUrl,
  ariaLabel,
}: {
  statusCode: string;
  evidenceUrl?: string | null;
  ariaLabel: string;
}) {
  const label = VERIFICATION_BADGE[statusCode] ?? statusCode;
  const className = `verification-badge verification-${statusCode}`;
  const href = safeHttpUrl(evidenceUrl);
  if (href) {
    return (
      <a href={href} target="_blank" rel="noreferrer" className={className} aria-label={ariaLabel}>
        {label}
      </a>
    );
  }
  return (
    <span className={className} aria-label={ariaLabel}>
      {label}
    </span>
  );
}

function KeymanPanel({
  postId,
  accessToken,
  keymen,
  canExtract,
  onExtracted,
  onSelectPost,
  focusPerson,
  focusEntity,
  focusTeam,
}: {
  postId: string;
  accessToken: string;
  keymen: Keyman[] | null;
  canExtract: boolean;
  onExtracted: () => void;
  onSelectPost?: (postId: string) => void;
  focusPerson?: { personId: string; personName: string } | null;
  focusEntity?: { entityId: string; entityName: string } | null;
  focusTeam?: { teamId: string; teamName: string } | null;
}) {
  const [related, setRelated] = useState<RelatedNode[] | null>(null);
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const [extracting, setExtracting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [orchestratorOff, setOrchestratorOff] = useState(false);
  const relatedRequest = useRef(0);

  useEffect(() => {
    setOrchestratorOff(false);
    setError(null);
  }, [postId]);

  async function handleSelect(personId: string, personName: string) {
    const requestId = ++relatedRequest.current;
    setSelectedName(personName);
    setRelated(null);
    try {
      const result = await fetchRelatedKeymen(accessToken, personId);
      if (requestId === relatedRequest.current) setRelated(result.related);
    } catch {
      if (requestId === relatedRequest.current) setRelated([]);
    }
  }

  async function handleSelectEntity(entityId: string, entityName: string) {
    const requestId = ++relatedRequest.current;
    setSelectedName(entityName);
    setRelated(null);
    try {
      const result = await fetchRelatedEntity(accessToken, entityId);
      if (requestId === relatedRequest.current) setRelated(result.related);
    } catch {
      if (requestId === relatedRequest.current) setRelated([]);
    }
  }

  async function handleSelectTeam(teamId: string, teamName: string) {
    const requestId = ++relatedRequest.current;
    setSelectedName(teamName);
    setRelated(null);
    try {
      const result = await fetchRelatedTeam(accessToken, teamId);
      if (requestId === relatedRequest.current) setRelated(result.related);
    } catch {
      if (requestId === relatedRequest.current) setRelated([]);
    }
  }

  useEffect(() => {
    if (!focusPerson) return;
    const requestId = ++relatedRequest.current;
    setSelectedName(focusPerson.personName);
    setRelated(null);
    fetchRelatedKeymen(accessToken, focusPerson.personId)
      .then((result) => {
        if (requestId === relatedRequest.current) setRelated(result.related);
      })
      .catch(() => {
        if (requestId === relatedRequest.current) setRelated([]);
      });
  }, [accessToken, focusPerson]);

  useEffect(() => {
    if (!focusEntity) return;
    const requestId = ++relatedRequest.current;
    setSelectedName(focusEntity.entityName);
    setRelated(null);
    fetchRelatedEntity(accessToken, focusEntity.entityId)
      .then((result) => {
        if (requestId === relatedRequest.current) setRelated(result.related);
      })
      .catch(() => {
        if (requestId === relatedRequest.current) setRelated([]);
      });
  }, [accessToken, focusEntity]);

  useEffect(() => {
    if (!focusTeam) return;
    const requestId = ++relatedRequest.current;
    setSelectedName(focusTeam.teamName);
    setRelated(null);
    fetchRelatedTeam(accessToken, focusTeam.teamId)
      .then((result) => {
        if (requestId === relatedRequest.current) setRelated(result.related);
      })
      .catch(() => {
        if (requestId === relatedRequest.current) setRelated([]);
      });
  }, [accessToken, focusTeam]);

  async function handleExtract() {
    setExtracting(true);
    setError(null);
    try {
      await extractPostKeymen(accessToken, postId);
      onExtracted();
    } catch (err) {
      setError(orchestratorUnavailableMessage(err, "Keyman extraction"));
      if (err instanceof BackendError && err.status === 503) {
        setOrchestratorOff(true);
      }
    } finally {
      setExtracting(false);
    }
  }

  return (
    <section className="popup-section">
      <div className="lineage-home-header">
        <h3>Keyman</h3>
        {canExtract && !orchestratorOff && (
          <button onClick={handleExtract} disabled={extracting}>
            {extracting ? "Extracting..." : "Extract Keymen"}
          </button>
        )}
      </div>
      {error && <p className="error">{error}</p>}
      {keymen && keymen.length > 0 ? (
        <ul className="keyman-list">
          {keymen.map((person) => (
            <li key={person.person_id}>
              <button
                className="keyman-select"
                aria-label={`Related nodes for ${person.person_name}`}
                onClick={() => handleSelect(person.person_id, person.person_name)}
              >
                <strong>{person.person_name}</strong> ({person.person_side_label ?? person.person_side_code})
              </button>
              {person.last_known_job_title && (
                <span className="keyman-role-title"> {person.last_known_job_title}</span>
              )}
              {person.affiliations.length > 0 && (
                <span className="keyman-affiliations">
                  {" -- "}
                  {person.affiliations.map((affiliation, index) => (
                    <span key={`${affiliation.organization_name}:${affiliation.corporate_entity_id ?? index}`}>
                      {index > 0 ? ", " : null}
                      {affiliation.corporate_entity_id ? (
                        <button
                          className="keyman-select"
                          aria-label={`Keyman affiliation: ${affiliation.organization_name}`}
                          onClick={() =>
                            handleSelectEntity(
                              affiliation.corporate_entity_id as string,
                              affiliation.organization_name,
                            )
                          }
                        >
                          {affiliation.organization_name}
                        </button>
                      ) : (
                        affiliation.organization_name
                      )}
                      {affiliation.role_title && (
                        <span className="keyman-role-title"> ({affiliation.role_title})</span>
                      )}
                    </span>
                  ))}
                </span>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className="popup-placeholder">No Keyman extracted yet.</p>
      )}
      {selectedName && (
        <div className="related-keymen">
          <h4>Related to {selectedName}</h4>
          {related === null ? (
            <p>Loading related nodes...</p>
          ) : related.length === 0 ? (
            <p className="popup-placeholder">No related nodes in the visible graph.</p>
          ) : (
            <ul>
              {related.map((node) => {
                const caption = relatedNodeCaption(node);
                const key = `${node.node_type_code}:${node.node_id}`;
                if (!isKnownRelatedNodeType(node.node_type_code)) {
                  return <li key={key}>{caption}</li>;
                }
                switch (node.node_type_code) {
                  case NODE_POST:
                    if (!onSelectPost) {
                      return <li key={key}>{caption}</li>;
                    }
                    return (
                      <li key={key}>
                        <button
                          className="keyman-select"
                          aria-label={`Open related post: ${node.label ?? node.node_id}`}
                          onClick={() => onSelectPost(node.node_id)}
                        >
                          {caption}
                        </button>
                      </li>
                    );
                  case NODE_PERSON:
                    return (
                      <li key={key}>
                        <button
                          className="keyman-select"
                          aria-label={`Related nodes for ${caption}`}
                          onClick={() => handleSelect(node.node_id, node.label ?? node.node_id)}
                        >
                          {caption}
                        </button>
                      </li>
                    );
                  case NODE_CORPORATE_ENTITY:
                    return (
                      <li key={key}>
                        <button
                          className="keyman-select"
                          aria-label={`Related nodes for ${node.label ?? node.node_id}`}
                          onClick={() => handleSelectEntity(node.node_id, node.label ?? node.node_id)}
                        >
                          {caption}
                        </button>
                      </li>
                    );
                  case NODE_TEAM:
                    return (
                      <li key={key}>
                        <button
                          className="keyman-select"
                          aria-label={`Related nodes for ${node.label ?? node.node_id}`}
                          onClick={() => handleSelectTeam(node.node_id, node.label ?? node.node_id)}
                        >
                          {caption}
                        </button>
                      </li>
                    );
                  default: {
                    const _exhaustive: never = node.node_type_code;
                    return <li key={key}>{_exhaustive}</li>;
                  }
                }
              })}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}

function EvaluationPanel({
  postId,
  accessToken,
  responses,
  canExtract,
  onEvaluated,
}: {
  postId: string;
  accessToken: string;
  responses: EvaluationResponse[] | null;
  canExtract: boolean;
  onEvaluated: (rows: EvaluationResponse[]) => void;
}) {
  const [evaluating, setEvaluating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [orchestratorOff, setOrchestratorOff] = useState(false);

  useEffect(() => {
    setOrchestratorOff(false);
    setError(null);
  }, [postId]);

  async function handleEvaluate() {
    setEvaluating(true);
    setError(null);
    try {
      const result = await evaluatePost(accessToken, postId);
      onEvaluated(result.responses);
    } catch (err) {
      setError(orchestratorUnavailableMessage(err, "Evaluation"));
      if (err instanceof BackendError && err.status === 503) {
        setOrchestratorOff(true);
      }
    } finally {
      setEvaluating(false);
    }
  }

  return (
    <section className="popup-section">
      <div className="lineage-home-header">
        <h3>Post quality (IRT)</h3>
        {canExtract && !orchestratorOff && (
          <button onClick={handleEvaluate} disabled={evaluating}>
            {evaluating ? "Evaluating..." : "Evaluate post"}
          </button>
        )}
      </div>
      {error && <p className="error">{error}</p>}
      {responses === null ? (
        <p>Loading evaluation...</p>
      ) : responses.length === 0 ? (
        <p className="popup-placeholder">Not yet evaluated.</p>
      ) : (
        <ul>
          {responses.map((row) => (
            <li key={row.criterion_code}>
              {row.criterion_label ?? row.criterion_code}: {row.response_category}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function CounterpartyPanel({
  postId,
  accessToken,
  counterparties,
  canExtract,
  onVerified,
  onSelectEntity,
}: {
  postId: string;
  accessToken: string;
  counterparties: Counterparty[];
  canExtract: boolean;
  onVerified: () => void;
  onSelectEntity?: (entityId: string, entityName: string) => void;
}) {
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchOff, setSearchOff] = useState(false);
  const hasPending = counterparties.some((c) => c.verification_status_code === "verify_pending");

  useEffect(() => {
    setSearchOff(false);
    setError(null);
  }, [postId]);

  async function handleVerify() {
    setVerifying(true);
    setError(null);
    try {
      await verifyPostRelations(accessToken, postId);
      onVerified();
    } catch (err) {
      setError(searchUnavailableMessage(err));
      if (err instanceof BackendError && err.status === 503) {
        setSearchOff(true);
      }
    } finally {
      setVerifying(false);
    }
  }

  return (
    <section className="popup-section">
      <div className="lineage-home-header">
        <h3>Counterparties</h3>
        {canExtract && hasPending && !searchOff && (
          <button onClick={handleVerify} disabled={verifying}>
            {verifying ? "Verifying..." : "Verify against web search"}
          </button>
        )}
      </div>
      {error && <p className="error">{error}</p>}
      <ul>
        {counterparties.map((c) => (
          <li key={c.counterparty_entity_name}>
            {c.corporate_entity_id && onSelectEntity ? (
              <button
                className="keyman-select"
                aria-label={`Counterparty org: ${c.counterparty_entity_name}`}
                onClick={() => {
                  if (c.corporate_entity_id) onSelectEntity(c.corporate_entity_id, c.counterparty_entity_name);
                }}
              >
                {c.counterparty_entity_name}
              </button>
            ) : (
              c.counterparty_entity_name
            )}{" "}
            -- {c.relationship_label ?? c.relationship_type_code}
            {" -- "}
            <VerificationBadge
              statusCode={c.verification_status_code}
              evidenceUrl={c.verification_evidence_url}
              ariaLabel={`Counterparty verification: ${c.counterparty_entity_name}`}
            />
          </li>
        ))}
      </ul>
    </section>
  );
}

const TICKET_STATUS_OPTIONS = [
  { code: "open", fallback: "Open" },
  { code: "in_progress", fallback: "In progress" },
  { code: "closed", fallback: "Closed" },
] as const;

function ticketStatusLabel(code: string, ticket: IssueTicket): string {
  if (ticket.ticket_status_code === code && ticket.ticket_status_label) {
    return ticket.ticket_status_label;
  }
  return TICKET_STATUS_OPTIONS.find((row) => row.code === code)?.fallback ?? code;
}

function IssueTicketPanel({
  postId,
  accessToken,
  canExtract,
}: {
  postId: string;
  accessToken: string;
  canExtract: boolean;
}) {
  const [tickets, setTickets] = useState<IssueTicket[] | null>(null);
  const [newTitle, setNewTitle] = useState("");
  const [newDueDate, setNewDueDate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [deriving, setDeriving] = useState(false);
  const [orchestratorOff, setOrchestratorOff] = useState(false);

  function reload() {
    fetchPostTickets(accessToken, postId)
      .then((r) => setTickets(r.tickets))
      .catch(() => setTickets([]));
  }

  useEffect(() => {
    setTickets(null);
    setOrchestratorOff(false);
    setError(null);
    fetchPostTickets(accessToken, postId)
      .then((r) => setTickets(r.tickets))
      .catch(() => setTickets([]));
  }, [postId, accessToken]);

  async function handleCreate() {
    if (!newTitle.trim()) return;
    setCreating(true);
    setError(null);
    try {
      await createPostTicket(accessToken, postId, newTitle, "open", newDueDate || undefined);
      setNewTitle("");
      setNewDueDate("");
      reload();
    } catch (err) {
      setError(String(err));
    } finally {
      setCreating(false);
    }
  }

  async function handleStatusChange(ticket: IssueTicket, nextStatus: string) {
    try {
      await updateTicketStatus(accessToken, ticket.issue_ticket_id, nextStatus);
      reload();
    } catch (err) {
      setError(String(err));
    }
  }

  async function handleDeriveCommitment() {
    setDeriving(true);
    setError(null);
    try {
      const result = await deriveCommitment(accessToken, postId);
      if (result.has_commitment) {
        reload();
      } else {
        setError("No customer commitment found in this post.");
      }
    } catch (err) {
      setError(orchestratorUnavailableMessage(err, "Commitment derivation"));
      if (err instanceof BackendError && err.status === 503) {
        setOrchestratorOff(true);
      }
    } finally {
      setDeriving(false);
    }
  }

  return (
    <section className="popup-section">
      <div className="lineage-home-header">
        <h3>이슈 티켓 (Issue tickets)</h3>
        {canExtract && !orchestratorOff && (
          <button onClick={handleDeriveCommitment} disabled={deriving}>
            {deriving ? "Deriving..." : "Derive commitment"}
          </button>
        )}
      </div>
      {error && <p className="error">{error}</p>}
      {tickets === null ? (
        <p>Loading tickets...</p>
      ) : tickets.length === 0 ? (
        <p className="popup-placeholder">No tickets yet.</p>
      ) : (
        <ul className="ticket-list">
          {tickets.map((ticket) => (
            <li key={ticket.issue_ticket_id} className="ticket-list-item">
              <span className="ticket-title">
                {ticket.ticket_title}
                {ticket.due_date && <span className="post-badge"> due {ticket.due_date}</span>}
              </span>
              <select
                value={ticket.ticket_status_code}
                onChange={(event) => handleStatusChange(ticket, event.target.value)}
                aria-label={`Status for ${ticket.ticket_title}`}
              >
                {TICKET_STATUS_OPTIONS.map((row) => (
                  <option key={row.code} value={row.code}>
                    {ticketStatusLabel(row.code, ticket)}
                  </option>
                ))}
              </select>
            </li>
          ))}
        </ul>
      )}
      <div className="ticket-create-row">
        <input
          type="text"
          value={newTitle}
          onChange={(event) => setNewTitle(event.target.value)}
          onKeyDown={(event) => event.key === "Enter" && handleCreate()}
          placeholder="New ticket title"
        />
        <input
          type="date"
          value={newDueDate}
          onChange={(event) => setNewDueDate(event.target.value)}
          aria-label="Due date"
        />
        <button onClick={handleCreate} disabled={creating || !newTitle.trim()}>
          {creating ? "Creating..." : "Create ticket"}
        </button>
      </div>
    </section>
  );
}

const ACTIVITY_TYPE_LABELS: Record<string, string> = {
  ticket_created: "Ticket created",
  ticket_status_changed: "Status changed",
  commitment_derived: "Commitment derived",
};

function activityTypeLabel(eventType: string): string {
  return ACTIVITY_TYPE_LABELS[eventType] ?? eventType;
}

function ActivityPanel({ postId, accessToken }: { postId: string; accessToken: string }) {
  const [events, setEvents] = useState<ActivityEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  function reload() {
    fetchPostActivity(accessToken, postId)
      .then((r) => setEvents(r.events))
      .catch((err) => setError(String(err)));
  }

  useEffect(() => {
    setEvents(null);
    setError(null);
    fetchPostActivity(accessToken, postId)
      .then((r) => setEvents(r.events))
      .catch((err) => setError(String(err)));
  }, [postId, accessToken]);

  return (
    <section className="popup-section">
      <div className="lineage-home-header">
        <h3>Activity</h3>
        <button onClick={reload}>Refresh</button>
      </div>
      {error && <p className="error">{error}</p>}
      {events === null ? (
        <p>Loading activity...</p>
      ) : events.length === 0 ? (
        <p className="popup-placeholder">No activity yet.</p>
      ) : (
        <ul className="ticket-list">
          {events.map((event) => (
            <li key={event.event_id} className="ticket-list-item">
              <span className="ticket-title">{event.summary}</span>
              <span className="post-badge">{activityTypeLabel(event.event_type)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function PostDetailPopup({
  postId,
  accessToken,
  canExtract,
  graph,
  liveBodyWarning,
  onClose,
  onSelectPost,
}: {
  postId: string;
  accessToken: string;
  canExtract: boolean;
  graph: LineageGraph | null;
  liveBodyWarning?: string | null;
  onClose: () => void;
  onSelectPost?: (postId: string) => void;
}) {
  const [post, setPost] = useState<PostDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<PostAiSummary | null>(null);
  const [keymen, setKeymen] = useState<Keyman[] | null>(null);
  const [counterparties, setCounterparties] = useState<Counterparty[] | null>(null);
  const [lineage, setLineage] = useState<PostLineage | null>(null);
  const [affiliateTrees, setAffiliateTrees] = useState<AffiliateNode[] | null>(null);
  const [vocEvidence, setVocEvidence] = useState<VocEvidence | null>(null);
  const [evaluation, setEvaluation] = useState<EvaluationResponse[] | null>(null);
  const [focusPerson, setFocusPerson] = useState<{ personId: string; personName: string } | null>(null);
  const [focusEntity, setFocusEntity] = useState<{ entityId: string; entityName: string } | null>(null);
  const [focusTeam, setFocusTeam] = useState<{ teamId: string; teamName: string } | null>(null);

  function reloadKeymen() {
    fetchPostKeymen(accessToken, postId).then((r) => setKeymen(r.keymen)).catch(() => setKeymen([]));
    fetchPostAffiliateTree(accessToken, postId)
      .then((r) => setAffiliateTrees(r.trees))
      .catch(() => setAffiliateTrees([]));
    fetchPostVocEvidence(accessToken, postId).then(setVocEvidence).catch(() => setVocEvidence(null));
    reloadCounterparties();
  }

  function reloadCounterparties() {
    fetchPostCounterparties(accessToken, postId)
      .then((r) => setCounterparties(r.counterparties))
      .catch(() => setCounterparties([]));
  }

  useEffect(() => {
    setPost(null);
    setError(null);
    setSummary(null);
    setKeymen(null);
    setCounterparties(null);
    setLineage(null);
    setAffiliateTrees(null);
    setVocEvidence(null);
    setEvaluation(null);
    setFocusPerson(null);
    setFocusEntity(null);
    setFocusTeam(null);
    fetchPost(accessToken, postId).then(setPost).catch((err) => setError(String(err)));
    fetchPostEvaluation(accessToken, postId)
      .then((r) => setEvaluation(r.responses))
      .catch(() => setEvaluation([]));
    fetchPostSummary(accessToken, postId).then(setSummary).catch(() => setSummary(null));
    fetchPostKeymen(accessToken, postId).then((r) => setKeymen(r.keymen)).catch(() => setKeymen([]));
    fetchPostCounterparties(accessToken, postId)
      .then((r) => setCounterparties(r.counterparties))
      .catch(() => setCounterparties([]));
    fetchPostLineage(accessToken, postId).then(setLineage).catch(() => setLineage(null));
    fetchPostAffiliateTree(accessToken, postId)
      .then((r) => setAffiliateTrees(r.trees))
      .catch(() => setAffiliateTrees([]));
    fetchPostVocEvidence(accessToken, postId).then(setVocEvidence).catch(() => setVocEvidence(null));
  }, [postId, accessToken]);

  return (
    <div className="popup-backdrop" onClick={onClose}>
      <div className="popup-panel" onClick={(event) => event.stopPropagation()}>
        <button className="popup-close" onClick={onClose} aria-label="Close">
          &times;
        </button>
        {error && <p className="error">{error}</p>}
        {!post && !error && <p>Loading...</p>}
        {post && (
          <>
            <h2>{post.post_title}</h2>
            <p className="post-meta">
              {post.voc_type_label ?? post.voc_type_code} &middot;{" "}
              {post.visibility_label ?? post.visibility_code} &middot;{" "}
              {new Date(post.created_at).toLocaleString()}
            </p>
            {liveBodyWarning ? (
              <p className="popup-live-body-warning" role="status">
                {liveBodyWarning}
              </p>
            ) : null}
            <PostBody body={post.post_body} />

            <section className="popup-section">
              <h3>요약 (Summary)</h3>
              {summary ? (
                <>
                  <p>{summary.korean_summary}</p>
                  {summary.key_events.length > 0 && (
                    <>
                      <h4>주요 이벤트 (Key events)</h4>
                      <ul>
                        {summary.key_events.map((event, i) => (
                          <li key={i}>{event}</li>
                        ))}
                      </ul>
                    </>
                  )}
                  {summary.roles_and_responsibilities.length > 0 && (
                    <>
                      <h4>R&amp;R</h4>
                      <ul>
                        {summary.roles_and_responsibilities.map((rr, i) => {
                          const isPerson = rr.actor_type_code === "prov_person";
                          const actorTypeLabel =
                            rr.actor_type_code === "prov_team"
                              ? "Team"
                              : isPerson
                                ? "Person"
                                : "Organization";
                          const person = isPerson
                            ? keymen?.find((row) => row.person_name === rr.actor_name)
                            : undefined;
                          const catalogId = rr.catalog_node_id;
                          const catalogType = rr.catalog_node_type_code;
                          let actorName: ReactNode = <strong>{rr.actor_name}</strong>;
                          if (person) {
                            actorName = (
                              <button
                                className="keyman-select"
                                aria-label={`R&R Keyman: ${rr.actor_name}`}
                                onClick={() => {
                                  setFocusEntity(null);
                                  setFocusTeam(null);
                                  setFocusPerson({
                                    personId: person.person_id,
                                    personName: person.person_name,
                                  });
                                }}
                              >
                                <strong>{rr.actor_name}</strong>
                              </button>
                            );
                          } else if (catalogType === NODE_TEAM && catalogId) {
                            actorName = (
                              <button
                                className="keyman-select"
                                aria-label={`R&R team: ${rr.actor_name}`}
                                onClick={() => {
                                  setFocusPerson(null);
                                  setFocusEntity(null);
                                  setFocusTeam({ teamId: catalogId, teamName: rr.actor_name });
                                }}
                              >
                                <strong>{rr.actor_name}</strong>
                              </button>
                            );
                          } else if (catalogType === NODE_CORPORATE_ENTITY && catalogId) {
                            actorName = (
                              <button
                                className="keyman-select"
                                aria-label={`R&R organization: ${rr.actor_name}`}
                                onClick={() => {
                                  setFocusPerson(null);
                                  setFocusTeam(null);
                                  setFocusEntity({ entityId: catalogId, entityName: rr.actor_name });
                                }}
                              >
                                <strong>{rr.actor_name}</strong>
                              </button>
                            );
                          }
                          return (
                            <li key={i}>
                              <span className={`actor-type-badge actor-type-${rr.actor_type_code}`}>
                                {actorTypeLabel}
                              </span>{" "}
                              {actorName}
                              {rr.affiliated_organization_name && (
                                <span className="rr-affiliation"> ({rr.affiliated_organization_name})</span>
                              )}
                              : {rr.responsibility}
                            </li>
                          );
                        })}
                      </ul>
                    </>
                  )}
                </>
              ) : (
                <p className="popup-placeholder">Summary unavailable (LLM orchestrator not configured).</p>
              )}
            </section>

            <EvaluationPanel
              postId={postId}
              accessToken={accessToken}
              responses={evaluation}
              canExtract={canExtract}
              onEvaluated={(rows) => setEvaluation(rows)}
            />

            <VocEvidenceSection
              evidence={vocEvidence}
              affiliateTrees={affiliateTrees}
              onSelectPerson={(personId, personName) => {
                setFocusEntity(null);
                setFocusTeam(null);
                setFocusPerson({ personId, personName });
              }}
            />

            <section className="popup-section">
              <h3>Event Lineage</h3>
              <EventLineageSection
                lineage={lineage}
                graph={graph}
                postId={postId}
                onSelectPost={onSelectPost}
              />
            </section>

            <section className="popup-section">
              <h3>Affiliate tree</h3>
              {affiliateTrees === null ? (
                <p>Loading affiliate tree...</p>
              ) : affiliateTrees.length === 0 ? (
                <p className="popup-placeholder">No affiliations on this post yet.</p>
              ) : (
                <ul className="affiliate-tree">
                  {affiliateTrees.map((node) => (
                    <AffiliateTreeNode
                      key={node.entity_id ?? node.entity_name}
                      node={node}
                      onSelectPerson={(personId, personName) => {
                        setFocusEntity(null);
                        setFocusTeam(null);
                        setFocusPerson({ personId, personName });
                      }}
                      onSelectEntity={(entityId, entityName) => {
                        setFocusPerson(null);
                        setFocusTeam(null);
                        setFocusEntity({ entityId, entityName });
                      }}
                    />
                  ))}
                </ul>
              )}
            </section>

            <KeymanPanel
              postId={postId}
              accessToken={accessToken}
              keymen={keymen}
              canExtract={canExtract}
              onExtracted={reloadKeymen}
              onSelectPost={onSelectPost}
              focusPerson={focusPerson}
              focusEntity={focusEntity}
              focusTeam={focusTeam}
            />

            {counterparties && counterparties.length > 0 && (
              <CounterpartyPanel
                postId={postId}
                accessToken={accessToken}
                counterparties={counterparties}
                canExtract={canExtract}
                onVerified={reloadCounterparties}
                onSelectEntity={(entityId, entityName) => {
                  setFocusPerson(null);
                  setFocusTeam(null);
                  setFocusEntity({ entityId, entityName });
                }}
              />
            )}

            <IssueTicketPanel postId={postId} accessToken={accessToken} canExtract={canExtract} />

            <ActivityPanel postId={postId} accessToken={accessToken} />

            <ChatPanel postId={postId} accessToken={accessToken} />
          </>
        )}
      </div>
    </div>
  );
}

function analysisRunCaption(run: AnalysisRun): string {
  return [run.run_kind_label, run.status_label, run.scope_entity_name ?? run.scope_kind_label]
    .filter(Boolean)
    .join(" · ");
}

/**
 * Next action for a failed run on the home list.
 *
 * The machine `failure_code` stays on detail history (ADR 0014). Copy
 * is kind-specific so a failed lineage reconstruction is not mistaken
 * for a missing TEPP transport.
 */
function analysisRunNextAction(run: AnalysisRun): string | null {
  if (run.status_code === "analysis_status_pending") {
    if (run.run_kind_code === "analysis_run_tepp") {
      return "Open this run to confirm which posts it will measure. Measurement has not started yet.";
    }
    return "Open this run, then start reconstruction. Reconstruction has not started yet.";
  }
  if (run.status_code !== "analysis_status_failed") {
    return null;
  }
  switch (run.run_kind_code) {
    case "analysis_run_tepp":
      return "Open this run to see why it failed, then connect the measurement service and re-run.";
    case "analysis_run_lineage":
      return "Open this run to see why it failed, then retry reconstruction from a current snapshot.";
    case "analysis_run_report":
      return "Open this run to see why it failed, then rebuild the period report from a current snapshot.";
    default: {
      const unexpected: never = run.run_kind_code;
      return unexpected;
    }
  }
}

/**
 * Empty-corpus copy that tells the operator what to do next.
 */
function analysisRunEmptyPostsHint(run: AnalysisRun): string {
  switch (run.run_kind_code) {
    case "analysis_run_tepp":
      return (
        "No posts were available at this cutoff for TEPP to measure. " +
        "Open a later run, or ask an administrator to capture a newer snapshot."
      );
    case "analysis_run_lineage":
      return (
        "No posts were available at this cutoff for reconstruction. " +
        "Open a later run, or ask an administrator to capture a newer snapshot."
      );
    case "analysis_run_report":
      return (
        "No posts were available at this cutoff for the period report. " +
        "Open a later run, or ask an administrator to capture a newer snapshot."
      );
    default: {
      const unexpected: never = run.run_kind_code;
      return unexpected;
    }
  }
}

/**
 * Corpus copy for a TEPP run that already has cutoff posts.
 *
 * Those titles are the measurement bag, not a reconstruction result.
 * Pending or running must not claim a calibrated measurement.
 */
function analysisRunCorpusHint(run: AnalysisRun): string | null {
  if (run.run_kind_code !== "analysis_run_tepp") return null;
  switch (run.status_code) {
    case "analysis_status_failed":
      return (
        "These posts are the cutoff corpus TEPP would measure. Connect a TEPP " +
        "transport, then re-run, to replace Failed with a calibrated result."
      );
    case "analysis_status_succeeded":
      return "These posts are the cutoff corpus this TEPP run measured.";
    case "analysis_status_pending":
    case "analysis_status_running":
      return "These posts are the cutoff corpus TEPP will measure once this run finishes.";
    case "analysis_status_cancelled":
      return (
        "These posts are the cutoff corpus this TEPP run would have measured. " +
        "The run was cancelled before a calibrated result."
      );
    case null:
      return "These posts are the cutoff corpus attached to this TEPP run.";
    default: {
      const unexpected: never = run.status_code;
      return unexpected;
    }
  }
}

/** Git-style prefix. The full digest stays on `title` for verification. */
const ANALYSIS_RUN_DIGEST_PREFIX_LENGTH = 12;

function analysisRunDigestPrefix(digest: string): string {
  return digest.slice(0, ANALYSIS_RUN_DIGEST_PREFIX_LENGTH);
}

type SelectPostOptions = {
  liveAfterCutoff?: boolean;
  knowledgeCutoff?: string;
};

/**
 * Next action when a cutoff title opens the live post (ADR 0016).
 *
 * Titles marked `live_after_cutoff` were rewritten after this run;
 * others still match the write clock the run knew. The popup then
 * states that the body is live. Cutoff body versioning stays later
 * work -- we never invent the earlier text.
 */
function analysisRunLivePostWarning(cutoffIso: string): string {
  const cutoffDate = cutoffIso.slice(0, 10);
  return (
    `Opening a title shows the live post. Titles marked updated after cutoff ` +
    `were rewritten after ${cutoffDate}. Compare those bodies with this run ` +
    "before you treat them as reconstructed evidence."
  );
}

/**
 * Popup honesty when a marked cutoff title opens the live body.
 *
 * ADR 0016 does not store a historical snapshot. This copy must not
 * invent the earlier text.
 */
function analysisRunOpenedBodyWarning(cutoffIso?: string | null): string {
  const cutoffDate = cutoffIso?.slice(0, 10);
  const when = cutoffDate ? `the ${cutoffDate} ` : "";
  return (
    `This is the live body, not the version known at ${when}analysis-run cutoff. ` +
    "The earlier text is not stored, so this popup does not invent it."
  );
}

function analysisRunLivePostButtonLabel(post: {
  post_title: string;
  live_after_cutoff?: boolean;
}): string {
  if (post.live_after_cutoff) {
    return `Open live post (updated after cutoff): ${post.post_title}`;
  }
  return `Open live post: ${post.post_title}`;
}

function AnalysisRunReproducibilityDigests({
  codeRevisionSha,
  configurationSha256,
}: {
  codeRevisionSha?: string;
  configurationSha256?: string;
}) {
  if (!codeRevisionSha && !configurationSha256) {
    return null;
  }
  return (
    <div role="group" aria-label="Analysis run reproducibility digests">
      <p className="post-meta">
        <span className="visually-hidden">
          Hover a prefix to read the full digest for verification.{" "}
        </span>
        {codeRevisionSha ? (
          <span title={codeRevisionSha}>{`Code ${analysisRunDigestPrefix(codeRevisionSha)}`}</span>
        ) : null}
        {codeRevisionSha && configurationSha256 ? " · " : null}
        {configurationSha256 ? (
          <span title={configurationSha256}>
            {`Config ${analysisRunDigestPrefix(configurationSha256)}`}
          </span>
        ) : null}
      </p>
    </div>
  );
}

function AnalysisRunsPanel({
  accessToken,
  onSelectPost,
}: {
  accessToken: string;
  onSelectPost: (postId: string, options?: SelectPostOptions) => void;
}) {
  const [runs, setRuns] = useState<AnalysisRun[] | null>(null);
  const [selected, setSelected] = useState<AnalysisRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [requesting, setRequesting] = useState(false);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    fetchAnalysisRuns(accessToken)
      .then((payload) => setRuns(payload.analysis_runs))
      .catch((err) => setError(String(err)));
  }, [accessToken]);

  async function handleRequestLineage() {
    setError(null);
    setRequesting(true);
    try {
      const created = await createAnalysisRun(accessToken, {
        run_kind_code: "analysis_run_lineage",
        idempotency_key: crypto.randomUUID(),
      });
      const listed = await fetchAnalysisRuns(accessToken);
      setRuns(listed.analysis_runs);
      setSelected(created);
    } catch (err) {
      setError(err instanceof BackendError ? err.message : String(err));
    } finally {
      setRequesting(false);
    }
  }

  async function handleStartReconstruction() {
    if (!selected) return;
    setError(null);
    setStarting(true);
    try {
      const started = await startAnalysisRun(accessToken, selected.analysis_run_id);
      const listed = await fetchAnalysisRuns(accessToken);
      setRuns(listed.analysis_runs);
      setSelected(started);
    } catch (err) {
      setError(err instanceof BackendError ? err.message : String(err));
    } finally {
      setStarting(false);
    }
  }

  async function handleOpen(runId: string) {
    setError(null);
    try {
      setSelected(await fetchAnalysisRun(accessToken, runId));
    } catch (err) {
      setSelected(null);
      if (err instanceof BackendError && err.status === 404) {
        setError("This analysis run is not visible.");
        return;
      }
      setError(String(err));
    }
  }

  if (error && runs === null) return <p className="error">{error}</p>;
  if (runs === null) return <p>Loading analysis runs...</p>;

  const corpusHint = selected ? analysisRunCorpusHint(selected) : null;

  return (
    <section className="popup-section lineage-home">
      <div className="lineage-home-header">
        <h2>Analysis runs</h2>
        <button
          className="keyman-select"
          aria-label="Request a lineage reconstruction"
          disabled={requesting}
          onClick={() => void handleRequestLineage()}
        >
          {requesting ? "Recording the run..." : "Request a lineage reconstruction"}
        </button>
      </div>
      {error && <p className="error">{error}</p>}
      {runs.length === 0 ? (
        <p className="popup-placeholder">
          No analysis runs visible to this account yet. Request a lineage
          reconstruction, or ask an administrator to run make seed.
        </p>
      ) : (
        <ul className="ticket-list" aria-label="Analysis runs">
          {runs.map((run) => {
            const documentCount = run.source_counts.find(
              (count) => count.count_type_code === "analysis_count_document",
            );
            const caption = analysisRunCaption(run);
            const nextAction = analysisRunNextAction(run);
            return (
              <li key={run.analysis_run_id} className="ticket-list-item">
                <button
                  className="post-list-item"
                  aria-label={`Open analysis run: ${caption}`}
                  onClick={() => void handleOpen(run.analysis_run_id)}
                >
                  <span className="ticket-title">{caption}</span>
                  {documentCount && (
                    <span className="post-badge">
                      {documentCount.count_value} {documentCount.count_type_label.toLowerCase()}
                    </span>
                  )}
                  {nextAction && <span className="post-meta">{nextAction}</span>}
                </button>
              </li>
            );
          })}
        </ul>
      )}
      {selected && (
        <div className="popup-section">
          <h3>{analysisRunCaption(selected)}</h3>
          <p className="post-meta">
            Cutoff {selected.knowledge_cutoff.slice(0, 10)}
            {" · "}
            Requested {selected.requested_at.slice(0, 10)}
          </p>
          <AnalysisRunReproducibilityDigests
            codeRevisionSha={selected.code_revision_sha}
            configurationSha256={selected.configuration_sha256}
          />
          {selected.status_code === "analysis_status_pending" && (
            <p className="post-meta">{analysisRunNextAction(selected)}</p>
          )}
          {selected.run_kind_code === "analysis_run_lineage" &&
            selected.status_code === "analysis_status_pending" && (
              <button
                className="keyman-select"
                aria-label="Start reconstruction"
                disabled={starting}
                onClick={() => void handleStartReconstruction()}
              >
                {starting ? "Reconstructing the cutoff bag..." : "Start reconstruction"}
              </button>
            )}
          {selected.reconstructed_edges && selected.reconstructed_edges.length > 0 && (
            <ul aria-label="Reconstructed lineage edges">
              {selected.reconstructed_edges.map((edge) => (
                <li key={`${edge.parent_post_id}-${edge.child_post_id}`}>
                  {edge.child_post_title} follows {edge.parent_post_title}
                </li>
              ))}
            </ul>
          )}
          <ul>
            {selected.source_counts.map((count) => (
              <li key={count.count_type_code}>
                {count.count_value} {count.count_type_label.toLowerCase()}
              </li>
            ))}
          </ul>
          {selected.status_history && selected.status_history.length > 0 && (
            <ol aria-label="Analysis run status history">
              {selected.status_history.map((event) => (
                <li key={event.status_ordinal}>
                  {event.status_label} {event.occurred_at.slice(0, 16).replace("T", " ")}
                  {event.failure_code ? ` · ${event.failure_code}` : ""}
                </li>
              ))}
            </ol>
          )}
          {selected.visible_posts && selected.visible_posts.length > 0 ? (
            <>
              {corpusHint && <p className="post-meta">{corpusHint}</p>}
              <p className="post-meta">{analysisRunLivePostWarning(selected.knowledge_cutoff)}</p>
              <ul aria-label="Posts known at this run cutoff">
                {selected.visible_posts.map((post) => (
                  <li key={post.post_id}>
                    <button
                      className="keyman-select"
                      aria-label={analysisRunLivePostButtonLabel(post)}
                      onClick={() =>
                        onSelectPost(post.post_id, {
                          liveAfterCutoff: Boolean(post.live_after_cutoff),
                          knowledgeCutoff: selected.knowledge_cutoff,
                        })
                      }
                    >
                      {post.post_title}
                    </button>
                    {post.live_after_cutoff && (
                      <span className="post-badge">Updated after cutoff</span>
                    )}
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p className="popup-placeholder">{analysisRunEmptyPostsHint(selected)}</p>
          )}
        </div>
      )}
    </section>
  );
}

function CalendarPanel({
  accessToken,
  onSelectPost,
}: {
  accessToken: string;
  onSelectPost: (postId: string) => void;
}) {
  const [commitments, setCommitments] = useState<CalendarEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCalendar(accessToken)
      .then((r) => setCommitments(r.commitments))
      .catch((err) => setError(String(err)));
  }, [accessToken]);

  if (error) return <p className="error">{error}</p>;
  if (commitments === null) return <p>Loading calendar...</p>;

  return (
    <section className="popup-section lineage-home">
      <h2>Calendar</h2>
      {commitments.length === 0 ? (
        <p className="popup-placeholder">
          No upcoming commitments. Derive one from a post, or create a ticket with a due date.
        </p>
      ) : (
        <ul className="ticket-list">
          {commitments.map((entry) => (
            <li key={entry.issue_ticket_id} className="ticket-list-item">
              <button
                className="post-list-item"
                aria-label={`Open commitment for: ${entry.post_title}`}
                onClick={() => onSelectPost(entry.post_id)}
              >
                <span className="ticket-title">{entry.commitment_summary ?? entry.ticket_title}</span>
                <span className="post-badge">{entry.post_title}</span>
                <span className="post-badge">
                  {entry.ticket_status_label ?? entry.ticket_status_code}
                </span>
                <span className="post-badge">due {entry.due_date}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function ReportsPanel({
  accessToken,
  canRebuild,
  onSelectPost,
}: {
  accessToken: string;
  canRebuild: boolean;
  onSelectPost: (postId: string) => void;
}) {
  const [grouping, setGrouping] = useState("process_unit");
  const [period, setPeriod] = useState("2026-W02");
  const [payload, setPayload] = useState<PeriodReports | null>(null);
  const [index, setIndex] = useState<PeriodReportIndex | null>(null);
  const [comparison, setComparison] = useState<PeriodComparison | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rebuilding, setRebuilding] = useState(false);

  const groupingLabels: Record<string, string> = {
    process_unit: "Process unit",
    corporate_entity: "Corporate entity",
    thread_group: "Thread group",
  };

  useEffect(() => {
    setError(null);
    Promise.all([
      fetchPeriodReports(accessToken, grouping, period),
      fetchPeriodReportIndex(accessToken, grouping),
      fetchPeriodComparison(accessToken, period),
    ])
      .then(([reports, periods, compared]) => {
        setPayload(reports);
        setIndex(periods);
        setComparison(compared);
      })
      .catch((err) => setError(String(err)));
  }, [accessToken, grouping, period]);

  async function handleRebuild() {
    setRebuilding(true);
    setError(null);
    try {
      await rebuildPeriodReports(accessToken, grouping, period);
      const [reports, periods, compared] = await Promise.all([
        fetchPeriodReports(accessToken, grouping, period),
        fetchPeriodReportIndex(accessToken, grouping),
        fetchPeriodComparison(accessToken, period),
      ]);
      setPayload(reports);
      setIndex(periods);
      setComparison(compared);
    } catch (err) {
      setError(String(err));
    } finally {
      setRebuilding(false);
    }
  }

  return (
    <section className="popup-section lineage-home">
      <div className="lineage-home-header">
        <h2>Period reports</h2>
        {canRebuild && (
          <button onClick={handleRebuild} disabled={rebuilding}>
            {rebuilding ? "Calibrating..." : "Rebuild report"}
          </button>
        )}
      </div>
      <div className="chat-input-row">
        <label>
          Grouping
          <select aria-label="Report grouping" value={grouping} onChange={(event) => setGrouping(event.target.value)}>
            <option value="process_unit">Process unit</option>
            <option value="corporate_entity">Corporate entity</option>
            <option value="thread_group">Thread group</option>
          </select>
        </label>
        <label>
          Period
          <input
            aria-label="Report period"
            value={period}
            onChange={(event) => setPeriod(event.target.value)}
          />
        </label>
      </div>
      {comparison && comparison.groupings.length > 0 && (
        <ul className="ticket-list" aria-label="Grouping comparison">
          {comparison.groupings.map((row) => (
            <li key={`${row.grouping_kind}:${row.grouping_key}`} className="ticket-list-item">
              <button
                className="post-list-item"
                aria-label={`Compare ${row.grouping_kind}: ${row.grouping_label}`}
                onClick={() => setGrouping(row.grouping_kind)}
              >
                <span className="ticket-title">
                  {groupingLabels[row.grouping_kind] ?? row.grouping_kind}: {row.grouping_label}
                </span>
                <span className="post-badge">mean θ {row.mean_theta.toFixed(2)}</span>
                <span className="post-badge">{row.post_count} posts</span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {index && index.periods.length > 0 && (
        <ul className="ticket-list">
          {index.periods.map((row) => (
            <li key={`${row.period_code}:${row.grouping_key}`} className="ticket-list-item">
              <button
                className="post-list-item"
                aria-label={`Open report period ${row.period_code}`}
                onClick={() => setPeriod(row.period_code)}
              >
                <span className="ticket-title">
                  {row.period_code}: mean θ {row.mean_theta.toFixed(2)}
                </span>
                <span className="post-badge">
                  {row.link_method === "fipc" && row.anchor_period_code && row.delta_mean_theta != null
                    ? `vs ${row.anchor_period_code}: ${row.delta_mean_theta >= 0 ? "+" : ""}${row.delta_mean_theta.toFixed(2)}`
                    : row.link_method === "fipc"
                      ? "shared metric"
                      : "reference"}
                </span>
                {row.selected_item_code && row.selected_item_information != null && (
                  <span className="post-badge">
                    CAT: {criterionShortLabel(row.selected_item_code)} I=
                    {row.selected_item_information.toFixed(2)}
                  </span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
      {error && <p className="error">{error}</p>}
      {payload === null && !error && <p>Loading reports...</p>}
      {payload && payload.reports.length === 0 && (
        <p className="popup-placeholder">
          No calibrated report for this grouping and period. Evaluate posts, then rebuild.
        </p>
      )}
      {payload && payload.reports.length > 0 && (
        <ul className="ticket-list">
          {payload.reports.map((report) => (
            <li key={report.grouping_key} className="ticket-list-item">
              <span className="ticket-title">
                {report.grouping_key}: mean θ {report.mean_theta.toFixed(2)} ({report.selected_model}
                {report.fit_converged ? ", converged" : ", not converged"})
              </span>
              <span className="post-badge">{report.post_count} posts</span>
              {report.link_method === "fipc" && report.anchor_period_code && report.delta_mean_theta != null && (
                <span className="post-badge">
                  vs {report.anchor_period_code}: {report.delta_mean_theta >= 0 ? "+" : ""}
                  {report.delta_mean_theta.toFixed(2)}
                </span>
              )}
              {report.link_method === "fipc" && report.delta_mean_theta == null && (
                <span className="post-badge">shared metric</span>
              )}
              {report.selected_items?.[0] && (
                <span className="post-badge">
                  CAT: {criterionShortLabel(report.selected_items[0].item_code)} I=
                  {report.selected_items[0].information.toFixed(2)}
                </span>
              )}
              {report.members.length > 0 && (
                <ul className="ticket-list">
                  {report.members.map((member) => (
                    <li key={member.post_id} className="ticket-list-item">
                      <button
                        className="post-list-item"
                        aria-label={`Open report post: ${member.post_title}`}
                        onClick={() => onSelectPost(member.post_id)}
                      >
                        <span className="ticket-title">{member.post_title}</span>
                        <span className="post-badge">θ {member.theta_eap.toFixed(2)}</span>
                        {member.ticket_title && (
                          <span className="post-badge">{member.ticket_title}</span>
                        )}
                        {(member.ticket_status_label ?? member.ticket_status_code) && (
                          <span className="post-badge">
                            {member.ticket_status_label ?? member.ticket_status_code}
                          </span>
                        )}
                        {member.ticket_due_date && (
                          <span className="post-badge">due {member.ticket_due_date}</span>
                        )}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function PostList({ accessToken }: { accessToken: string }) {
  const [posts, setPosts] = useState<PostSummary[] | null>(null);
  const [graph, setGraph] = useState<LineageGraph | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedPostId, setSelectedPostId] = useState<string | null>(null);
  const [openedAfterCutoff, setOpenedAfterCutoff] = useState(false);
  const [openedCutoffIso, setOpenedCutoffIso] = useState<string | null>(null);
  const [canRebuild, setCanRebuild] = useState(false);
  const [rebuilding, setRebuilding] = useState(false);
  const [rebuildError, setRebuildError] = useState<string | null>(null);

  function selectPost(postId: string, options?: SelectPostOptions) {
    setSelectedPostId(postId);
    setOpenedAfterCutoff(Boolean(options?.liveAfterCutoff));
    setOpenedCutoffIso(options?.knowledgeCutoff ?? null);
  }

  function closeSelectedPost() {
    setSelectedPostId(null);
    setOpenedAfterCutoff(false);
    setOpenedCutoffIso(null);
  }

  useEffect(() => {
    fetchPosts(accessToken).then(setPosts).catch((err) => setError(String(err)));
    fetchLineageGraph(accessToken).then(setGraph).catch(() => setGraph({ nodes: [], edges: [] }));
    fetchMe(accessToken)
      .then((me) => setCanRebuild(me.permission_codes.includes("post_admin")))
      .catch(() => setCanRebuild(false));
  }, [accessToken]);

  async function handleRebuild() {
    setRebuilding(true);
    setRebuildError(null);
    try {
      await rebuildLineage(accessToken);
      setGraph(await fetchLineageGraph(accessToken));
    } catch (err) {
      setRebuildError(String(err));
    } finally {
      setRebuilding(false);
    }
  }

  if (error) return <p className="error">{error}</p>;
  if (!posts) return <p>Loading posts...</p>;
  if (posts.length === 0) return <p>No posts visible to this account yet -- try `make seed`.</p>;

  return (
    <>
      <CalendarPanel accessToken={accessToken} onSelectPost={selectPost} />
      <AnalysisRunsPanel accessToken={accessToken} onSelectPost={selectPost} />
      <ReportsPanel accessToken={accessToken} canRebuild={canRebuild} onSelectPost={selectPost} />
      <section className="popup-section lineage-home">
        <div className="lineage-home-header">
          <h2>Event Lineage</h2>
          {canRebuild && (
            <button onClick={handleRebuild} disabled={rebuilding}>
              {rebuilding ? "Rebuilding..." : "Rebuild lineage"}
            </button>
          )}
        </div>
        {rebuildError && <p className="error">{rebuildError}</p>}
        {!graph && <p>Loading lineage graph...</p>}
        {graph && <LineageDag graph={graph} onSelectPost={selectPost} />}
      </section>
      <ul className="post-list">
        {posts.map((post) => (
          <li key={post.post_id}>
            <button
              className="post-list-item"
              aria-label={`View post: ${post.post_title}`}
              onClick={() => selectPost(post.post_id)}
            >
              <span className="post-title">{post.post_title}</span>
              <span className="post-badge">{post.voc_type_label ?? post.voc_type_code}</span>
              <span className="post-badge">{post.visibility_label ?? post.visibility_code}</span>
            </button>
          </li>
        ))}
      </ul>
      {selectedPostId && (
        <PostDetailPopup
          postId={selectedPostId}
          accessToken={accessToken}
          canExtract={canRebuild}
          graph={graph}
          liveBodyWarning={
            openedAfterCutoff ? analysisRunOpenedBodyWarning(openedCutoffIso) : null
          }
          onClose={closeSelectedPost}
          onSelectPost={selectPost}
        />
      )}
    </>
  );
}

export default function App() {
  const auth = useAuth();

  if (auth.isLoading) {
    return <p>Loading authentication state...</p>;
  }

  if (auth.error) {
    return <p className="error">Authentication error: {auth.error.message}</p>;
  }

  if (!auth.isAuthenticated) {
    return (
      <main className="centered">
        <h1>LineageWeave</h1>
        <button onClick={() => auth.signinRedirect()}>Log in</button>
      </main>
    );
  }

  const accessToken = auth.user?.access_token;
  if (!accessToken) {
    return <p className="error">Authenticated, but no access token was returned.</p>;
  }

  return (
    <main>
      <header className="app-header">
        <h1>LineageWeave</h1>
        <div>
          <span>{auth.user?.profile.preferred_username}</span>
          <button onClick={() => auth.signoutRedirect()}>Log out</button>
        </div>
      </header>
      <PostList accessToken={accessToken} />
    </main>
  );
}
