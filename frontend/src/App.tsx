import { AdminPanel } from "./components/AdminPanel";
import { LeftoverPairList } from "./components/LeftoverPairList";
import { WorkspaceCalendar } from "./components/WorkspaceCalendar";
import { focusedGraphMustReset } from "./focusedGraphSelection";

import { useCallback, useEffect, useEffectEvent, useRef, useState, type ReactNode } from "react";
import { useAuth } from "react-oidc-context";
import {
  askPostChat,
  askAgent,
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
  fetchCustomerMaster,
  resolveCustomerHint,
  fetchLineageGraph,
  fetchMe,
  fetchPost,
  fetchPostContent,
  fetchPostActivity,
  fetchPostBookmark,
  fetchPostChat,
  fetchPostAffiliateTree,
  fetchPostCounterparties,
  fetchPostEvaluation,
  fetchPostKeymen,
  fetchPostLineage,
  fetchPostFiveW1H,
  fetchPostSummary,
  fetchPostTickets,
  fetchPostVocEvidence,
  fetchSimilarVoc,
  fetchPeriodComparison,
  fetchPeriodReportIndex,
  fetchPeriodReports,
  fetchPosts,
  fetchRankings,
  fetchRelatedEntity,
  fetchRelatedKeymen,
  fetchRelatedTeam,
  rebuildLineage,
  rebuildPeriodReports,
  setPostBookmark,
  setPreferredLocale,
  updateTicketStatus,
  verifyPostRelations,
  type ActivityEvent,
  type AskAgentResponse,
  type AffiliateNode,
  type AnalysisRun,
  type CalendarResponse,
  type ChatAnswer,
  type ChatExchange,
  type CorporateEntityRef,
  type CustomerMasterEntity,
  type CustomerMasterResponse,
  type Counterparty,
  type EvaluationResponse,
  type IssueTicket,
  type LineageGraph,
  type Keyman,
  type SourceAuthorContext,
  type PostAiSummary,
  type PostFiveW1H,
  type PostDetail,
  type PostContentUnit,
  type PostImageContent,
  type PostFilterOption,
  type PeriodComparison,
  type PeriodReportIndex,
  type PeriodReports,
  type PostLineage,
  type PostSummary,
  type PostSortOrder,
  type RankingList,
  type PersonRoleHistoryEntry,
  type RelatedNode,
  type RelatedNodeType,
  type VocEvidence,
  type SimilarVocItem,
  fetchTenantConfig,
} from "./api";
import { CitationChip } from "./components/CitationChip";
import { OrganizationAliasChip } from "./components/OrganizationAliasChip";
import { organizationAliasCaption } from "./components/organizationAliasCaption";
import { CutoffKnownBody } from "./components/CutoffKnownBody";
import { LineageEntityPicker } from "./components/LineageEntityPicker";
import { OntologyExplorer } from "./components/OntologyExplorer";
import { AskEvidenceLayerPopup } from "./components/AskEvidenceLayerPopup";
import { PopupCloseButton } from "./components/PopupCloseButton";
import { SimilarVocPanel } from "./components/SimilarVocPanel";
import { chatEvidenceKindLabel } from "./evidenceKindLabels";
import { WorkspaceNav, type WorkspaceDestination } from "./components/WorkspaceNav";
import { OperationsDashboard } from "./components/OperationsDashboard";
import { initialWorkspaceDestination } from "./gnbChrome";
import { LineageDag } from "./LineageDag";
import { PostBody } from "./PostBody";
import { decodeHtmlEntities } from "./postBodyDisplay";
import { FiveW1H } from "./components/FiveW1H";
import { isFocusableVisible } from "./focusVisibility";
import { subgraphForPost } from "./lineageLayout";
import {
  rememberOidcReturnUrl,
  returnUrlFromLocation,
  stripOidcCallbackParams,
} from "./oidcReturnUrl";
import {
  isSupportedLocale,
  LOCALE_LABELS,
  SUPPORTED_LOCALES,
  setLocale,
  t,
  tf,
  useLocale,
} from "./i18n";
import "./App.css";

function orchestratorUnavailableMessage(err: unknown, action: string): string {
  if (err instanceof BackendError && err.status === 503) {
    return `${action} ${t("is temporarily unavailable.")} ${t("Saved evidence is still available.")}`;
  }
  return String(err);
}

function LanguageSwitcher({ accessToken }: { accessToken?: string }) {
  const locale = useLocale();
  return (
    <label className="language-switcher">
      <span className="visually-hidden">{t("Language")}</span>
      <select
        aria-label={t("Language")}
        value={locale}
        onChange={(event) => {
          const nextLocale = event.target.value;
          if (!isSupportedLocale(nextLocale)) return;
          setLocale(nextLocale);
          if (accessToken) void setPreferredLocale(accessToken, nextLocale).catch(() => undefined);
        }}
      >
        {SUPPORTED_LOCALES.map((option) => (
          <option key={option} value={option}>
            {LOCALE_LABELS[option]}
          </option>
        ))}
      </select>
    </label>
  );
}

function searchUnavailableMessage(err: unknown): string {
  if (err instanceof BackendError && err.status === 503) {
    return t("Verification unavailable (search is not configured).");
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
  onClose?: () => void;
}) {
  const [post, setPost] = useState<PostDetail | null>(null);
  const [postError, setPostError] = useState(false);

  useEffect(() => {
    let current = true;
    setPost(null);
    setPostError(false);
    fetchPost(accessToken, postId)
      .then((result) => {
        if (current) setPost(result);
      })
      .catch(() => {
        if (current) setPostError(true);
      });
    return () => {
      current = false;
    };
  }, [postId, accessToken]);

  return (
    <div className="evidence-panel" role="complementary" aria-label={t("Evidence")}>
      {onClose ? <PopupCloseButton onClose={onClose} label={t("Close evidence panel")} /> : null}
      <h3>{t("Evidence")}</h3>
      {!post && !postError && <p role="status">{t("Loading source post...")}</p>}
      {postError && (
        <p className="error" role="alert">
          {t("Source evidence is unavailable. Continue with the saved answer.")}
        </p>
      )}
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
  currentPostId,
}: {
  citedPosts?: { post_id: string; post_title: string }[];
  citedPostIds: string[];
  onOpenEvidence: (postId: string) => void;
  currentPostId?: string;
}) {
  if ((citedPosts?.length ?? citedPostIds.length) === 0) return null;
  const chips =
    citedPosts ?? citedPostIds.map((post_id) => ({ post_id, post_title: post_id.slice(0, 8) }));
  return (
    <div className="chat-citations">
      <span>{t("Sources:")} </span>
      {chips.map((cited) => (
        <CitationChip
          key={cited.post_id}
          postId={cited.post_id}
          postTitle={cited.post_title}
          onOpenEvidence={onOpenEvidence}
          current={cited.post_id === currentPostId}
        />
      ))}
    </div>
  );
}

function ChatPanel({
  postId,
  accessToken,
  nameFirstAsk,
}: {
  postId: string;
  accessToken: string;
  nameFirstAsk?: boolean;
}) {
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
    setEvidencePostId(null);
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

  const firstCitedPostId =
    exchanges[0]?.cited_posts?.[0]?.post_id ?? exchanges[0]?.cited_post_ids[0] ?? null;
  const firstCitedTitle =
    exchanges[0]?.cited_posts?.[0]?.post_title ??
    (firstCitedPostId ? firstCitedPostId.slice(0, 8) : null);
  const landedEvidencePostId = nameFirstAsk ? (evidencePostId ?? firstCitedPostId) : null;

  return (
    <section className="popup-section chat-section">
      <h3 id="post-ask" tabIndex={-1}>
        {t("Ask about this lineage")}
      </h3>
      {nameFirstAsk && exchanges[0] ? (
        <p className="post-meta" role="status" aria-label={t("Ask seed next action")}>
          {firstAskNextAction(exchanges[0].question_text)}
        </p>
      ) : null}
      {nameFirstAsk && exchanges[0] ? (
        <div key={`seeded-${exchanges[0].question_text}`} className="chat-answer">
          <p className="chat-question">{exchanges[0].question_text}</p>
          <p>{exchanges[0].answer_text}</p>
          <ChatCitations
            citedPosts={exchanges[0].cited_posts}
            citedPostIds={exchanges[0].cited_post_ids}
            onOpenEvidence={setEvidencePostId}
            currentPostId={
              exchanges[0].cited_posts?.[0]?.post_id ?? exchanges[0].cited_post_ids[0]
            }
          />
        </div>
      ) : null}
      {nameFirstAsk && firstCitedTitle ? (
        <p className="post-meta" role="status" aria-label={t("Ask citation next action")}>
          {firstCitedNextAction(firstCitedTitle)}
        </p>
      ) : null}
      {nameFirstAsk && landedEvidencePostId ? (
        <EvidencePanel
          postId={landedEvidencePostId}
          accessToken={accessToken}
          onClose={
            evidencePostId && evidencePostId !== firstCitedPostId
              ? () => setEvidencePostId(null)
              : undefined
          }
        />
      ) : null}
      {nameFirstAsk && firstCitedTitle && landedEvidencePostId ? (
        <p className="post-meta" role="status" aria-label={t("Evidence next action")}>
          {landedEvidenceNextAction(firstCitedTitle)}
        </p>
      ) : null}
      {!seededOnly && (
        <div className="chat-input-row">
          <input
            type="text"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => event.key === "Enter" && handleAsk()}
            placeholder={t("What happened between these events?")}
          />
          <button onClick={() => handleAsk()} disabled={loading || !question.trim()}>
            {loading ? t("Asking...") : t("Ask")}
          </button>
        </div>
      )}
      {seededOnly && exchanges.length > 0 && (
        <p className="popup-placeholder">
          {t("Interactive questions are unavailable right now; saved evidence remains available.")}
        </p>
      )}
      {exchanges.length > 0 && (
        <div className="chat-suggestions">
          {exchanges.map((exchange) => (
            <button
              key={exchange.question_text}
              className="chat-suggestion-chip"
              aria-label={tf("Ask seeded question: {question}", { question: exchange.question_text })}
              aria-current={
                nameFirstAsk && exchanges[0]?.question_text === exchange.question_text
                  ? "true"
                  : undefined
              }
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
      {exchanges
        .filter(
          (exchange) =>
            !(nameFirstAsk && exchange.question_text === exchanges[0]?.question_text),
        )
        .map((exchange) => (
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
      {!nameFirstAsk && evidencePostId ? (
        <EvidencePanel
          postId={evidencePostId}
          accessToken={accessToken}
          onClose={() => setEvidencePostId(null)}
        />
      ) : null}
    </section>
  );
}

function eventLineageCurrentNextAction(postTitle: string): string {
  return tf("{post} is current in Event Lineage. Read Keyman and evaluation next.", {
    post: postTitle,
  });
}

function firstKeymanNextAction(personName: string): string {
  return tf("{person} is the first Keyman. Read that person next.", { person: personName });
}

function firstRelatedNextAction(nodeLabel: string): string {
  return tf("{node} is the first related node. Read that person next.", { node: nodeLabel });
}

function relatedNodesCurrentNextAction(personName: string): string {
  return tf("Related nodes for {person} are current. Ask about this lineage next.", {
    person: personName,
  });
}

function firstAskNextAction(questionText: string): string {
  return tf("{question} is the first Ask. Read that answer next.", { question: questionText });
}

function firstCitedNextAction(postTitle: string): string {
  return tf("{post} is the first cited source. Open that evidence next.", { post: postTitle });
}

function landedEvidenceNextAction(postTitle: string): string {
  return tf("{post} evidence is current. Read Event Lineage on that post next.", {
    post: postTitle,
  });
}

function EventLineageSection({
  lineage,
  graph,
  postId,
  onSelectPost,
  currentNextAction,
}: {
  lineage: PostLineage | null;
  graph: LineageGraph | null;
  postId: string;
  onSelectPost?: (postId: string) => void;
  currentNextAction?: string | null;
}) {
  if (!lineage) return <p role="status">{t("Loading lineage...")}</p>;
  if (!graph) return <p role="status">{t("Loading lineage...")}</p>;
  const scoped = graph ? subgraphForPost(graph, postId) : { nodes: [], edges: [] };
  const hasLinks = lineage.direct.length > 0 || lineage.indirect.length > 0;
  if (scoped.nodes.length === 0) {
    const isolationMessage =
      graph.isolation_reason === "comparison_candidates_available"
        ? t("Other visible posts share this comparison group, but no Event Lineage link is available. Read Keyman and evaluation next.")
        : graph.isolation_reason === "no_comparison_group"
          ? t("No other visible posts share this comparison group yet. Request reconstruction after more posts arrive, or read Keyman and evaluation.")
          : t("No linked posts yet.");
    return (
      <p className="lineage-empty">
        {hasLinks
          ? t("The linked records are listed above. The graph is not available for this view.")
          : isolationMessage}
      </p>
    );
  }
  return (
    <>
      {scoped.nodes.length > 0 && onSelectPost && (
        <LineageDag graph={scoped} onSelectPost={onSelectPost} currentPostId={postId} />
      )}
      {scoped.nodes.length > 0 && currentNextAction ? (
        <p className="post-meta" role="status" aria-label={t("Event Lineage next action")}>
          {currentNextAction}
        </p>
      ) : null}
    </>
  );
}

function summaryFetchError(err: unknown): string {
  return err instanceof BackendError ? err.message : String(err);
}

function RelatedPostsSection({
  lineage,
  onSelectPost,
}: {
  lineage: PostLineage | null;
  onSelectPost?: (postId: string) => void;
}) {
  if (!lineage) {
    return (
      <section className="popup-section related-posts-section" aria-labelledby="related-posts-heading">
        <div className="related-posts-header">
          <div>
            <p className="section-eyebrow">{t("Evidence trail")}</p>
            <h3 id="related-posts-heading">{t("Related posts")}</h3>
          </div>
        </div>
        <p role="status">{t("Loading related posts...")}</p>
      </section>
    );
  }

  const related = [
    ...lineage.direct.map((post) => ({ post, kind: "Direct relation" })),
    ...lineage.indirect.map((post) => ({ post, kind: "Indirect relation" })),
  ];

  return (
    <section className="popup-section related-posts-section" aria-labelledby="related-posts-heading">
      <div className="related-posts-header">
        <div>
          <p className="section-eyebrow">{t("Evidence trail")}</p>
          <h3 id="related-posts-heading">{t("Related posts")}</h3>
        </div>
        {related.length > 0 && <span className="related-post-count">{related.length} {t("linked")}</span>}
      </div>
      {related.length === 0 ? (
        <p className="popup-placeholder">{t("No linked posts have been established for this record.")}</p>
      ) : (
        <ul className="related-post-list" aria-label={t("Related posts")}>
          {related.map(({ post, kind }) => (
            <li key={`${kind}:${post.post_id}`}>
              {(() => {
                const cardContent = (
                  <>
                    <span className="related-post-kind">{t(kind)}</span>
                    {kind === "Direct relation" && post.interval_relation_label ? (
                      <span className="related-post-interval">{t(post.interval_relation_label)}</span>
                    ) : null}
                    <span className="related-post-content">
                      <strong>{post.post_title}</strong>
                      <span className="post-body-excerpt" aria-label={t("Post body preview")}>
                        {post.post_body_excerpt || t("No post body.")}
                        {post.post_body_truncated ? " ..." : ""}
                      </span>
                    </span>
                  </>
                );
                return onSelectPost ? (
                  <button
                    type="button"
                    className="related-post-card"
                    aria-label={tf("Open related post: {label}", { label: post.post_title })}
                    onClick={() => onSelectPost(post.post_id)}
                  >
                    {cardContent}
                    <span className="related-post-cta">{t("Open record")}</span>
                  </button>
                ) : (
                  <div className="related-post-card related-post-card-static">
                    {cardContent}
                  </div>
                );
              })()}
            </li>
          ))}
        </ul>
      )}
    </section>
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
          <OrganizationAliasChip
            displayName={node.entity_name}
            organizationAlias={node.organization_alias}
            ariaLabel={tf("Affiliate org: {name}", {
              name: organizationAliasCaption(node.entity_name, node.organization_alias),
            })}
            onSelect={() => {
              if (node.entity_id) onSelectEntity(node.entity_id, node.entity_name);
            }}
          />
        ) : (
          organizationAliasCaption(node.entity_name, node.organization_alias)
        )}
      </span>
      {(node.entity_level_label || node.entity_level_code) && (
        <span className="affiliate-level"> ({node.entity_level_label ?? node.entity_level_code})</span>
      )}
      {!node.resolved && <span className="affiliate-unresolved-mark"> {t("unresolved")}</span>}
      {node.people.length > 0 && (
        <span className="keyman-affiliations">
          {" -- "}
          {node.people.map((person, index) => (
            <span key={person.person_id}>
              {index > 0 ? ", " : null}
              {onSelectPerson ? (
                <button
                  className="keyman-select"
                  aria-label={tf("Affiliate Keyman: {name}", { name: person.person_name })}
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
  if (!evidence) return <p role="status">{t("Loading VOC evidence...")}</p>;
  const assignedExcerpts = new Set(
    evidence.counterparties
      .map((row) => row.evidence_excerpt)
      .filter((excerpt): excerpt is string => Boolean(excerpt)),
  );
  const unassignedExcerpts = evidence.excerpts.filter((excerpt) => !assignedExcerpts.has(excerpt));
  const hasExcerpt = evidence.excerpts.length > 0 || assignedExcerpts.size > 0;
  return (
    <section className="popup-section">
      <h3>{t("VOC evidence")}</h3>
      <p className="post-meta">
        {evidence.voc_type_label} ({evidence.voc_type_code})
      </p>
      {!hasExcerpt ? (
        <p className="popup-placeholder">{t("No extractive excerpt -- no named organization appears in this post.")}</p>
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
                  aria-label={tf("VOC Keyman: {name}", { name: row.counterparty_entity_name })}
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
                  ariaLabel={tf("VOC verification: {name}", { name: row.counterparty_entity_name })}
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
  if (node.node_type_code === NODE_CORPORATE_ENTITY) {
    const aliased = organizationAliasCaption(name, node.organization_alias);
    if (aliased !== name) {
      return aliased;
    }
  }
  return `${name} (${node.ontology_label ?? node.node_type_code})`;
}

const PROJECT_EXTRACTION_LABELS: Record<string, string> = {
  source_field_hint: "Explicit source field",
  contextual_orchestrator_semantic: "Semantic extraction",
};

const PROJECT_PROVENANCE_LABELS: Record<string, string> = {
  "source_post.source_project_code": "Source project code",
  "source_post.source_project_name": "Source project name",
  "post_project_mention.evidence_text": "Stored semantic evidence",
};

function projectExtractionLabel(method: string): string {
  return t(PROJECT_EXTRACTION_LABELS[method] ?? "Recorded extraction");
}

function projectProvenanceLabel(provenance: string): string {
  return t(PROJECT_PROVENANCE_LABELS[provenance] ?? "Recorded evidence");
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
  const label = t(VERIFICATION_BADGE[statusCode] ?? statusCode);
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
  sourceAuthorContext,
  canExtract,
  onExtracted,
  onSelectPost,
  focusPerson,
  focusEntity,
  focusTeam,
  landFirstKeyman,
  landFirstRelated,
  afterList,
}: {
  postId: string;
  accessToken: string;
  keymen: Keyman[] | null;
  sourceAuthorContext?: SourceAuthorContext | null;
  canExtract: boolean;
  onExtracted: () => void;
  onSelectPost?: (postId: string) => void;
  focusPerson?: { personId: string; personName: string } | null;
  focusEntity?: { entityId: string; entityName: string } | null;
  focusTeam?: { teamId: string; teamName: string } | null;
  landFirstKeyman?: boolean;
  landFirstRelated?: boolean;
  afterList?: ReactNode;
}) {
  const [related, setRelated] = useState<RelatedNode[] | null>(null);
  const [roleHistory, setRoleHistory] = useState<PersonRoleHistoryEntry[]>([]);
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const [selectedFocus, setSelectedFocus] = useState<{
    nodeTypeCode: string;
    nodeId: string;
    label: string;
  } | null>(null);
  const [ontologyOpen, setOntologyOpen] = useState(false);
  const [landedRelated, setLandedRelated] = useState<RelatedNode[] | null>(null);
  const [landedRelatedName, setLandedRelatedName] = useState<string | null>(null);
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
    setSelectedFocus({ nodeTypeCode: NODE_PERSON, nodeId: personId, label: personName });
    setRelated(null);
    setRoleHistory([]);
    try {
      const result = await fetchRelatedKeymen(accessToken, personId);
      if (requestId === relatedRequest.current) {
        setRelated(result.related);
        setRoleHistory(result.role_history ?? []);
      }
    } catch {
      if (requestId === relatedRequest.current) setRelated([]);
    }
  }

  async function handleSelectEntity(entityId: string, entityName: string) {
    const requestId = ++relatedRequest.current;
    setSelectedName(entityName);
    setSelectedFocus({ nodeTypeCode: NODE_CORPORATE_ENTITY, nodeId: entityId, label: entityName });
    setRelated(null);
    setRoleHistory([]);
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
    setSelectedFocus({ nodeTypeCode: NODE_TEAM, nodeId: teamId, label: teamName });
    setRelated(null);
    setRoleHistory([]);
    try {
      const result = await fetchRelatedTeam(accessToken, teamId);
      if (requestId === relatedRequest.current) setRelated(result.related);
    } catch {
      if (requestId === relatedRequest.current) setRelated([]);
    }
  }

  useEffect(() => {
    if (!landFirstKeyman || selectedName || !keymen?.[0]) {
      return;
    }
    const first = keymen[0];
    const requestId = ++relatedRequest.current;
    setSelectedName(first.person_name);
    setSelectedFocus({
      nodeTypeCode: NODE_PERSON,
      nodeId: first.person_id,
      label: first.person_name,
    });
    setRelated(null);
    setRoleHistory([]);
    fetchRelatedKeymen(accessToken, first.person_id)
      .then((result) => {
        if (requestId === relatedRequest.current) {
          setRelated(result.related);
          setRoleHistory(result.role_history ?? []);
        }
      })
      .catch(() => {
        if (requestId === relatedRequest.current) setRelated([]);
      });
  }, [accessToken, landFirstKeyman, keymen, selectedName]);

  useEffect(() => {
    if (!landFirstRelated) {
      setLandedRelatedName(null);
      setLandedRelated(null);
      return;
    }
    const first = related?.[0];
    if (!first || first.node_type_code !== NODE_PERSON) {
      return;
    }
    const name = first.label ?? first.node_id;
    let cancelled = false;
    setLandedRelatedName(name);
    setLandedRelated(null);
    fetchRelatedKeymen(accessToken, first.node_id)
      .then((result) => {
        if (!cancelled) setLandedRelated(result.related);
      })
      .catch(() => {
        if (!cancelled) setLandedRelated([]);
      });
    return () => {
      cancelled = true;
    };
  }, [accessToken, landFirstRelated, related]);

  useEffect(() => {
    if (!landFirstRelated || !landedRelatedName || landedRelated === null) {
      return;
    }
    const heading = document.getElementById("post-ask");
    heading?.focus();
    heading?.scrollIntoView?.({ block: "nearest" });
  }, [landFirstRelated, landedRelatedName, landedRelated]);

  useEffect(() => {
    if (!focusPerson) return;
    const requestId = ++relatedRequest.current;
    setSelectedName(focusPerson.personName);
    setSelectedFocus({
      nodeTypeCode: NODE_PERSON,
      nodeId: focusPerson.personId,
      label: focusPerson.personName,
    });
    setRelated(null);
    setRoleHistory([]);
    fetchRelatedKeymen(accessToken, focusPerson.personId)
      .then((result) => {
        if (requestId === relatedRequest.current) {
          setRelated(result.related);
          setRoleHistory(result.role_history ?? []);
        }
      })
      .catch(() => {
        if (requestId === relatedRequest.current) setRelated([]);
      });
  }, [accessToken, focusPerson]);

  useEffect(() => {
    if (!focusEntity) return;
    const requestId = ++relatedRequest.current;
    setSelectedName(focusEntity.entityName);
    setSelectedFocus({
      nodeTypeCode: NODE_CORPORATE_ENTITY,
      nodeId: focusEntity.entityId,
      label: focusEntity.entityName,
    });
    setRelated(null);
    setRoleHistory([]);
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
    setSelectedFocus({
      nodeTypeCode: NODE_TEAM,
      nodeId: focusTeam.teamId,
      label: focusTeam.teamName,
    });
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
      setError(orchestratorUnavailableMessage(err, "Keymen extraction"));
      if (err instanceof BackendError && err.status === 503) {
        setOrchestratorOff(true);
      }
    } finally {
      setExtracting(false);
    }
  }

  const relatedPosts = related?.filter((node) => node.node_type_code === NODE_POST) ?? [];
  const relatedBlock = selectedName ? (
    <div className="related-keymen">
      <h4>{t("Related to")} {selectedName}</h4>
      {roleHistory.length > 0 ? (
        <div className="role-history">
          <p className="section-eyebrow">{t("Role history")}</p>
          <ol aria-label={`${t("Role history")}: ${selectedName}`}>
            {roleHistory.map((entry) => (
              <li key={entry.post_id}>
                <span className="post-badge">{entry.created_at.slice(0, 10)}</span>
                <span>
                  {entry.affiliated_organization_name
                    ? tf("{responsibility} at {organization}", {
                        responsibility: entry.responsibility,
                        organization: entry.affiliated_organization_name,
                      })
                    : entry.responsibility}
                </span>
              </li>
            ))}
          </ol>
        </div>
      ) : null}
      {related === null ? (
        <p role="status">{t("Loading related nodes...")}</p>
      ) : related.length === 0 ? (
        <p className="popup-placeholder">{t("No related nodes in the visible graph.")}</p>
      ) : (
        <>
          {relatedPosts.length > 0 && onSelectPost ? (
            <div className="related-posts-context">
              <p className="section-eyebrow">{t("Evidence trail")}</p>
              <h5>{t("Related posts")}</h5>
              <ul className="related-post-list" aria-label={`${t("Related posts")}: ${selectedName}`}>
                {relatedPosts.map((node) => (
                  <li key={`context-post:${node.node_id}`}>
                    <button
                      type="button"
                      className="related-post-card"
                      aria-label={tf("Open related post: {label}", { label: node.label ?? node.node_id })}
                      onClick={() => onSelectPost(node.node_id)}
                    >
                      <span className="related-post-kind">{t("Graph relation")}</span>
                      <strong>{node.label ?? node.node_id}</strong>
                      <span className="related-post-cta">{t("Open record")}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          <ul>
          {related.map((node) => {
            const caption = relatedNodeCaption(node);
            const key = `${node.node_type_code}:${node.node_id}`;
            if (!isKnownRelatedNodeType(node.node_type_code)) {
              return <li key={key}>{caption}</li>;
            }
            switch (node.node_type_code) {
              case NODE_POST:
                return null;
              case NODE_PERSON:
                return (
                  <li key={key}>
                    <button
                      className="keyman-select"
                      aria-label={tf("Related nodes for {name}", { name: caption })}
                      aria-current={
                        landFirstRelated && related[0]?.node_id === node.node_id
                          ? "true"
                          : undefined
                      }
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
                      aria-label={tf("Related nodes for {name}", { name: caption })}
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
                      aria-label={tf("Related nodes for {name}", { name: caption })}
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
        </>
      )}
    </div>
  ) : null;

  return (
    <>
    <section className="popup-section">
      <div className="lineage-home-header">
        <h3>{t("Keymen")}</h3>
        <button
          type="button"
          className="keyman-select"
          onClick={() => setOntologyOpen((open) => !open)}
          aria-expanded={ontologyOpen}
        >
          {t("Inspect ontology neighborhood")}
        </button>
        {canExtract && !orchestratorOff && (
          <details className="operator-action-tools">
            <summary>{t("Evidence operations")}</summary>
            <button onClick={handleExtract} disabled={extracting}>
              {extracting ? t("Extracting...") : t("Extract Keymen")}
            </button>
          </details>
        )}
      </div>
      {error && <p className="error">{error}</p>}
      {sourceAuthorContext ? (
        <details className="keyman-source-context">
          <summary>{t("Source author evidence")} · {t("Hint only")}</summary>
          <p>
            <strong>
              {sourceAuthorContext.source_author_name || sourceAuthorContext.source_author_code || t("Unknown")}
            </strong>
          </p>
          <p>
            {t("Authorization context")}: {sourceAuthorContext.account_display_name}
            {sourceAuthorContext.account_affiliations.length > 0 ? (
              <span className="keyman-affiliations">
                {" -- "}
                {sourceAuthorContext.account_affiliations.map((affiliation, index) => (
                  <span key={`${affiliation.corporate_entity_id}:${affiliation.process_unit_code ?? index}`}>
                    {index > 0 ? ", " : null}
                    {affiliation.entity_name}
                    {affiliation.process_unit_name
                      ? ` (${affiliation.process_unit_name})`
                      : affiliation.process_unit_code
                        ? ` (${affiliation.process_unit_code})`
                        : null}
                  </span>
                ))}
              </span>
            ) : null}
          </p>
        </details>
      ) : null}
      {keymen && keymen.length > 0 ? (
        <ul className="keyman-list">
          {keymen.map((person) => (
            <li key={person.person_id}>
              <button
                className="keyman-select"
                aria-label={tf("Related nodes for {name}", { name: person.person_name })}
                aria-current={
                  landFirstKeyman && selectedName === person.person_name ? "true" : undefined
                }
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
                        <OrganizationAliasChip
                          displayName={affiliation.organization_name}
                          organizationAlias={affiliation.organization_alias}
                          ariaLabel={tf("Keyman affiliation: {name}", {
                            name: organizationAliasCaption(
                              affiliation.organization_name,
                              affiliation.organization_alias,
                            ),
                          })}
                          onSelect={() =>
                            handleSelectEntity(
                              affiliation.corporate_entity_id as string,
                              affiliation.organization_name,
                            )
                          }
                        />
                      ) : (
                        organizationAliasCaption(
                          affiliation.organization_name,
                          affiliation.organization_alias,
                        )
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
        <p className="popup-placeholder">{t("No Keymen extracted yet.")}</p>
      )}
      {!afterList && relatedBlock}
    </section>
      {afterList}
      {afterList && relatedBlock}
      {afterList && related?.[0] ? (
        <p className="post-meta" role="status" aria-label={t("Related next action")}>
          {firstRelatedNextAction(related[0].label ?? related[0].node_id)}
        </p>
      ) : null}
      {afterList && landFirstRelated && landedRelatedName ? (
        <div className="related-keymen">
          <h4>{t("Related to")} {landedRelatedName}</h4>
          {landedRelated === null ? (
            <p role="status">{t("Loading related nodes...")}</p>
          ) : landedRelated.length === 0 ? (
            <p className="popup-placeholder">{t("No related nodes in the visible graph.")}</p>
          ) : (
            <ul>
              {landedRelated.map((node) => (
                <li key={`${node.node_type_code}:${node.node_id}`}>
                  {relatedNodeCaption(node)}
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
      {afterList && landFirstRelated && landedRelatedName && landedRelated !== null ? (
          <p className="post-meta" role="status" aria-label={t("Ask next action")}>
          {relatedNodesCurrentNextAction(landedRelatedName)}
        </p>
      ) : null}
      {afterList && landFirstRelated && landedRelatedName && landedRelated !== null ? (
        <ChatPanel postId={postId} accessToken={accessToken} nameFirstAsk />
      ) : null}
      {ontologyOpen ? (
        <OntologyExplorer
          accessToken={accessToken}
          focusNodeType={selectedFocus?.nodeTypeCode ?? NODE_POST}
          focusNodeId={selectedFocus?.nodeId ?? postId}
          onSelectPost={onSelectPost}
          onOpenEvidence={onSelectPost}
        />
      ) : null}
    </>
  );
}

function leftoverCriterionNextAction(
  criterion: string,
  pairKind: "closest" | "farthest",
): string {
  if (pairKind === "farthest") {
    return tf(
      "{criterion} is the leftover criterion this post sat farthest from after main effects. Read that Post quality score next.",
      { criterion },
    );
  }
  return tf(
    "{criterion} is the leftover criterion this post sat closest to after main effects. Read that Post quality score next.",
    { criterion },
  );
}

function EvaluationPanel({
  postId,
  accessToken,
  responses,
  canExtract,
  onEvaluated,
  leftoverFocus,
}: {
  postId: string;
  accessToken: string;
  responses: EvaluationResponse[] | null;
  canExtract: boolean;
  onEvaluated: (rows: EvaluationResponse[]) => void;
  leftoverFocus?: { pairKind: "closest" | "farthest"; criterionCode: string } | null;
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
        <h3 id="post-quality" tabIndex={-1}>
          {t("Post quality (IRT)")}
        </h3>
        {canExtract && !orchestratorOff && (
          <details className="operator-action-tools">
            <summary>{t("Evidence operations")}</summary>
            <button onClick={handleEvaluate} disabled={evaluating}>
              {evaluating ? t("Evaluating...") : t("Evaluate post")}
            </button>
          </details>
        )}
      </div>
      {leftoverFocus ? (
        <p className="post-meta" role="status" aria-label={t("Leftover criterion next action")}>
          {leftoverCriterionNextAction(
            criterionShortLabel(leftoverFocus.criterionCode),
            leftoverFocus.pairKind,
          )}
        </p>
      ) : null}
      {error && <p className="error">{error}</p>}
      {responses === null ? (
        <p role="status">{t("Loading evaluation...")}</p>
      ) : responses.length === 0 ? (
        <p className="popup-placeholder">{t("Not yet evaluated.")}</p>
      ) : (
        <ul>
          {responses.map((row) => (
            <li
              key={row.criterion_code}
              className="evaluation-criterion"
              aria-current={
                leftoverFocus?.criterionCode === row.criterion_code ? "true" : undefined
              }
            >
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
  onSelectPost,
}: {
  postId: string;
  accessToken: string;
  counterparties: Counterparty[];
  canExtract: boolean;
  onVerified: () => void;
  onSelectEntity?: (entityId: string, entityName: string) => void;
  onSelectPost?: (postId: string) => void;
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
        <h3>{t("Counterparties")}</h3>
        {canExtract && hasPending && !searchOff && (
          <details className="operator-action-tools">
            <summary>{t("Evidence operations")}</summary>
            <button onClick={handleVerify} disabled={verifying}>
              {verifying ? t("Verifying...") : t("Verify against web search")}
            </button>
          </details>
        )}
      </div>
      {error && <p className="error">{error}</p>}
      <ul>
        {counterparties.map((c) => (
          <li key={c.counterparty_entity_name}>
            {c.corporate_entity_id && onSelectEntity ? (
              <OrganizationAliasChip
                displayName={c.counterparty_entity_name}
                organizationAlias={c.organization_alias}
                ariaLabel={tf("Counterparty org: {name}", {
                  name: organizationAliasCaption(c.counterparty_entity_name, c.organization_alias),
                })}
                onSelect={() => {
                  if (c.corporate_entity_id) onSelectEntity(c.corporate_entity_id, c.counterparty_entity_name);
                }}
              />
            ) : (
              organizationAliasCaption(c.counterparty_entity_name, c.organization_alias)
            )}{" "}
            -- {c.relationship_label ?? c.relationship_type_code}
            {" -- "}
            <VerificationBadge
              statusCode={c.verification_status_code}
              evidenceUrl={c.verification_evidence_url}
              ariaLabel={tf("Counterparty verification: {name}", { name: c.counterparty_entity_name })}
            />
            {c.verification_evidence_post_id && onSelectPost ? (
              <button
                type="button"
                className="keyman-select"
                onClick={() => onSelectPost(c.verification_evidence_post_id!)}
              >
                View internal evidence
              </button>
            ) : null}
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
  return t(TICKET_STATUS_OPTIONS.find((row) => row.code === code)?.fallback ?? code);
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
        setError(t("No customer commitment found in this post."));
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
        <h3>{t("Issue tickets")}</h3>
        {canExtract && !orchestratorOff && (
          <details className="operator-action-tools">
            <summary>{t("Evidence operations")}</summary>
            <button onClick={handleDeriveCommitment} disabled={deriving}>
              {deriving ? t("Deriving...") : t("Derive commitment")}
            </button>
          </details>
        )}
      </div>
      {error && <p className="error">{error}</p>}
      {tickets === null ? (
        <p role="status">{t("Loading tickets...")}</p>
      ) : tickets.length === 0 ? (
        <p className="popup-placeholder">{t("No tickets yet.")}</p>
      ) : (
        <ul className="ticket-list">
          {tickets.map((ticket) => (
            <li key={ticket.issue_ticket_id} className="ticket-list-item">
              <span className="ticket-title">
                {ticket.ticket_title}
                {ticket.due_date && <span className="post-badge"> {t("due")} {ticket.due_date}</span>}
              </span>
              <select
                value={ticket.ticket_status_code}
                onChange={(event) => handleStatusChange(ticket, event.target.value)}
                aria-label={tf("Status for {title}", { title: ticket.ticket_title })}
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
          placeholder={t("New ticket title")}
        />
        <input
          type="date"
          value={newDueDate}
          onChange={(event) => setNewDueDate(event.target.value)}
          aria-label={t("Due date")}
        />
        <button onClick={handleCreate} disabled={creating || !newTitle.trim()}>
          {creating ? t("Creating...") : t("Create ticket")}
        </button>
      </div>
    </section>
  );
}

const ACTIVITY_TYPE_LABELS: Record<string, string> = {
  ticket_created: "Ticket created",
  ticket_status_changed: "Status changed",
  commitment_derived: "Commitment derived",
  keymen_extracted: "Keymen extracted",
  relations_verified: "Relations verified",
  post_evaluated: "Post evaluated",
  chat_answered: "Chat answered",
};

function activityTypeLabel(eventType: string): string {
  return t(ACTIVITY_TYPE_LABELS[eventType] ?? eventType);
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
        <h3>{t("Activity")}</h3>
        <button onClick={reload}>{t("Refresh")}</button>
      </div>
      {error && <p className="error">{error}</p>}
      {events === null ? (
        <p role="status">{t("Loading activity...")}</p>
      ) : events.length === 0 ? (
        <p className="popup-placeholder">{t("No activity yet.")}</p>
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
  knowledgeCutoff,
  focusEventLineage,
  leftoverFocus,
  onClose,
  onSelectPost,
  onSearch,
}: {
  postId: string;
  accessToken: string;
  canExtract: boolean;
  graph: LineageGraph | null;
  liveBodyWarning?: string | null;
  knowledgeCutoff?: string | null;
  focusEventLineage?: boolean;
  leftoverFocus?: { pairKind: "closest" | "farthest"; criterionCode: string } | null;
  onClose: () => void;
  onSelectPost?: (postId: string) => void;
  onSearch?: (query: string) => void;
}) {
  const [post, setPost] = useState<PostDetail | null>(null);
  const [imageContent, setImageContent] = useState<PostImageContent[]>([]);
  const [structureUnits, setStructureUnits] = useState<PostContentUnit[]>([]);
  const [bookmarked, setBookmarked] = useState<boolean | null>(null);
  const [bookmarkSaving, setBookmarkSaving] = useState(false);
  const [postActionStatus, setPostActionStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<PostAiSummary | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [summaryRetry, setSummaryRetry] = useState(0);
  const [fiveW1H, setFiveW1H] = useState<PostFiveW1H | null>(null);
  const [keymen, setKeymen] = useState<Keyman[] | null>(null);
  const [sourceAuthorContext, setSourceAuthorContext] = useState<SourceAuthorContext | null>(null);
  const [counterparties, setCounterparties] = useState<Counterparty[] | null>(null);
  const [lineage, setLineage] = useState<PostLineage | null>(null);
  const [affiliateTrees, setAffiliateTrees] = useState<AffiliateNode[] | null>(null);
  const [vocEvidence, setVocEvidence] = useState<VocEvidence | null>(null);
  const [similarVoc, setSimilarVoc] = useState<SimilarVocItem[] | null>(null);
  const [similarVocError, setSimilarVocError] = useState<string | null>(null);
  const [similarVocNextOffset, setSimilarVocNextOffset] = useState<number | null>(null);
  const [similarVocLoadingMore, setSimilarVocLoadingMore] = useState(false);
  const similarVocLoadingMoreRef = useRef(false);
  const similarVocScopeRef = useRef({ postId });
  if (similarVocScopeRef.current.postId !== postId) similarVocScopeRef.current = { postId };
  const [evaluation, setEvaluation] = useState<EvaluationResponse[] | null>(null);
  const [focusPerson, setFocusPerson] = useState<{ personId: string; personName: string } | null>(null);
  const [focusEntity, setFocusEntity] = useState<{ entityId: string; entityName: string } | null>(null);
  const [focusTeam, setFocusTeam] = useState<{ teamId: string; teamName: string } | null>(null);
  const contentReloadRef = useRef<() => void>(() => undefined);
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    return () => {
      if (previouslyFocused?.isConnected) previouslyFocused.focus();
    };
  }, []);

  useEffect(() => {
    dialogRef.current?.focus();
  }, [postId]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab") return;

      const dialog = dialogRef.current;
      if (!dialog) return;
      const focusable = Array.from(
        dialog.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), summary, input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      ).filter(isFocusableVisible);
      if (focusable.length === 0) {
        event.preventDefault();
        dialog.focus();
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;
      if (active === dialog || !dialog.contains(active)) {
        event.preventDefault();
        (event.shiftKey ? last : first).focus();
      } else if (event.shiftKey && active === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  function reloadKeymen() {
    fetchPostKeymen(accessToken, postId)
      .then((r) => {
        setKeymen(r.keymen);
        setSourceAuthorContext(r.source_author_context ?? null);
      })
      .catch(() => {
        setKeymen([]);
        setSourceAuthorContext(null);
      });
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
    setStructureUnits([]);
    setBookmarked(null);
    setBookmarkSaving(false);
    setPostActionStatus(null);
    setError(null);
    setSummary(null);
    setSummaryError(null);
    setFiveW1H(null);
    setKeymen(null);
    setSourceAuthorContext(null);
    setCounterparties(null);
    setLineage(null);
    setAffiliateTrees(null);
    setVocEvidence(null);
    setSimilarVoc(null);
    setSimilarVocError(null);
    setSimilarVocNextOffset(null);
    setSimilarVocLoadingMore(false);
    similarVocLoadingMoreRef.current = false;
    setEvaluation(null);
    setFocusPerson(null);
    setFocusEntity(null);
    setFocusTeam(null);
    let disposed = false;
    let contentPollTimer: number | undefined;
    const asOf = liveBodyWarning && knowledgeCutoff ? knowledgeCutoff : undefined;
    fetchPost(accessToken, postId, asOf).then(setPost).catch((err) => setError(String(err)));
    const reloadContent = () =>
      fetchPostContent(accessToken, postId)
        .then((content) => {
          if (disposed) return;
          setImageContent(content.images);
          setStructureUnits(content.units);
          if (content.status === "processing" && contentPollTimer === undefined) {
            contentPollTimer = window.setTimeout(() => {
              contentPollTimer = undefined;
              reloadContent();
            }, 2000);
          }
        })
        .catch(() => {
          if (disposed) return;
          setImageContent([]);
          setStructureUnits([]);
        });
    contentReloadRef.current = reloadContent;
    reloadContent();
    fetchPostBookmark(accessToken, postId)
      .then((r) => setBookmarked(r.bookmarked))
      .catch(() => {
        setBookmarked(null);
      });
    fetchPostEvaluation(accessToken, postId)
      .then((r) => setEvaluation(r.responses))
      .catch(() => setEvaluation([]));
    fetchPostFiveW1H(accessToken, postId)
      .then(setFiveW1H)
      .catch(() => setFiveW1H(null));
    fetchPostKeymen(accessToken, postId)
      .then((r) => {
        setKeymen(r.keymen);
        setSourceAuthorContext(r.source_author_context ?? null);
      })
      .catch(() => {
        setKeymen([]);
        setSourceAuthorContext(null);
      });
    fetchPostCounterparties(accessToken, postId)
      .then((r) => setCounterparties(r.counterparties))
      .catch(() => setCounterparties([]));
    fetchPostLineage(accessToken, postId).then(setLineage).catch(() => setLineage(null));
    fetchPostAffiliateTree(accessToken, postId)
      .then((r) => setAffiliateTrees(r.trees))
      .catch(() => setAffiliateTrees([]));
    fetchPostVocEvidence(accessToken, postId).then(setVocEvidence).catch(() => setVocEvidence(null));
    fetchSimilarVoc(accessToken, postId)
      .then((result) => {
        if (disposed) return;
        setSimilarVoc(result.items);
        setSimilarVocNextOffset(result.next_offset);
      })
      .catch(() => {
        if (disposed) return;
        setSimilarVoc([]);
        setSimilarVocError("유사 VOC 판정을 사용할 수 없습니다. 잠시 후 다시 확인하세요.");
      });
    return () => {
      disposed = true;
      if (contentPollTimer !== undefined) window.clearTimeout(contentPollTimer);
      if (contentReloadRef.current === reloadContent) {
        contentReloadRef.current = () => undefined;
      }
    };
  }, [postId, accessToken, liveBodyWarning, knowledgeCutoff]);

  useEffect(() => {
    let disposed = false;
    setSummary(null);
    setSummaryError(null);
    fetchPostSummary(accessToken, postId)
      .then((value) => {
        if (!disposed) {
          setSummary(value);
          contentReloadRef.current();
        }
      })
      .catch((err) => {
        if (disposed) return;
        setSummary(null);
        setSummaryError(summaryFetchError(err));
      });
    return () => {
      disposed = true;
    };
  }, [postId, accessToken, summaryRetry]);

  const permanentLink = (() => {
    const url = new URL(window.location.href);
    stripOidcCallbackParams(url);
    url.searchParams.set("post", postId);
    url.hash = "";
    return url.toString();
  })();

  async function sharePost() {
    try {
      if (typeof navigator.share === "function") {
        await navigator.share({ title: post?.post_title, url: permanentLink });
        return;
      }
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(permanentLink);
        setPostActionStatus(t("Permanent link copied."));
        return;
      }
      setPostActionStatus(t("Share unavailable."));
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setPostActionStatus(t("Share unavailable."));
    }
  }

  async function toggleBookmark() {
    if (bookmarked === null || bookmarkSaving) return;
    setBookmarkSaving(true);
    try {
      const next = await setPostBookmark(accessToken, postId, !bookmarked);
      setBookmarked(next.bookmarked);
    } catch {
      setPostActionStatus(t("Bookmark unavailable."));
    } finally {
      setBookmarkSaving(false);
    }
  }

  useEffect(() => {
    if (!focusEventLineage || !post) {
      return;
    }
    const heading = document.getElementById("post-event-lineage");
    heading?.focus();
    heading?.scrollIntoView?.({ block: "nearest" });
  }, [focusEventLineage, post]);

  useEffect(() => {
    if (!leftoverFocus || !post) {
      return;
    }
    const heading = document.getElementById("post-quality");
    heading?.focus();
    heading?.scrollIntoView?.({ block: "nearest" });
  }, [leftoverFocus, post]);

  return (
    <div className="popup-backdrop" onClick={onClose}>
      <div
        ref={dialogRef}
        className="popup-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby={post ? "post-detail-title" : undefined}
        aria-label={post ? undefined : t("Post details")}
        tabIndex={-1}
        onClick={(event) => event.stopPropagation()}
      >
        <PopupCloseButton onClose={onClose} label={t("Close")} />
        {error && <p className="error">{error}</p>}
        {!post && !error && <p role="status">{t("Loading...")}</p>}
        {post && (
          <>
            <h2 id="post-detail-title">{post.post_title}</h2>
            <p className="post-meta">
              {post.voc_type_label ?? post.voc_type_code} &middot;{" "}
              {post.visibility_label ?? post.visibility_code} &middot;{" "}
              {new Date(post.created_at).toLocaleString()}
            </p>
            <div className="post-actions" role="group" aria-label={t("Post actions")}>
              <button type="button" onClick={() => void sharePost()}>
                {t("Share")}
              </button>
              <button type="button" onClick={() => window.print()}>
                {t("Print")}
              </button>
              <button
                type="button"
                aria-pressed={bookmarked === true}
                disabled={bookmarked === null || bookmarkSaving}
                onClick={() => void toggleBookmark()}
              >
                {bookmarked ? t("Bookmarked") : t("Bookmark")}
              </button>
            </div>
            {postActionStatus && (
              <p className="post-action-status" role="status">
                {postActionStatus}
              </p>
            )}
            {post.known_at ? (
              <CutoffKnownBody
                title={post.known_at.post_title}
                body={post.known_at.post_body}
                writtenAt={post.known_at.written_at}
                cutoff={post.known_at.as_of}
              />
            ) : null}
            {liveBodyWarning ? (
              <p className="popup-live-body-warning" role="status" aria-label={t("Live body warning")}>
                {liveBodyWarning}
              </p>
            ) : null}
            <section className="popup-section post-source-body" aria-label={t("Post body")}>
              <h3>{t("Post body")}</h3>
              {post.post_body.trim() ? (
                <PostBody body={post.post_body} imageContent={imageContent} structureUnits={structureUnits} />
              ) : (
                <p className="popup-placeholder" role="status">
                  {t("Source body was not imported; summary and semantic extraction are unavailable.")}
                </p>
              )}
            </section>
            {(post.source_stage_code ||
              post.source_detail_state_code ||
              post.source_draft_code ||
              post.source_deleted_flag ||
              post.source_author_code ||
              post.source_author_name ||
              post.source_company_code ||
              post.source_company_name ||
              post.source_process_unit_code ||
              post.source_process_unit_name ||
              post.source_sales_pool_code ||
              post.source_sales_pool_name ||
              post.source_customer_code ||
              post.source_customer_name ||
              post.source_project_code ||
              post.source_project_name ||
              post.source_system_code ||
              post.source_record_key) && (
              <section className="popup-section" aria-label={t("Original source state")}>
                <h3>{t("Original source state")}</h3>
                <dl>
                  {post.source_stage_code ? (
                    <>
                      <dt>{t("Source stage")}</dt>
                      <dd>{post.source_stage_code}</dd>
                    </>
                  ) : null}
                  {post.source_detail_state_code ? (
                    <>
                      <dt>{t("Source detail state")}</dt>
                      <dd>{post.source_detail_state_code}</dd>
                    </>
                  ) : null}
                  {post.source_draft_code ? (
                    <>
                      <dt>{t("Source draft marker")}</dt>
                      <dd>{post.source_draft_code}</dd>
                    </>
                  ) : null}
                  {post.source_deleted_flag ? (
                    <>
                      <dt>{t("Source deletion marker")}</dt>
                      <dd>{post.source_deleted_flag}</dd>
                    </>
                  ) : null}
                  {post.source_author_code ? (
                    <>
                      <dt>{t("Source author code")}</dt>
                      <dd>{post.source_author_code}</dd>
                    </>
                  ) : null}
                  {post.source_author_name ? (
                    <>
                      <dt>{t("Source author name")}</dt>
                      <dd>{post.source_author_name}</dd>
                    </>
                  ) : null}
                  {post.source_company_code ? (
                    <>
                      <dt>{t("Source company code")}</dt>
                      <dd>{post.source_company_code}</dd>
                    </>
                  ) : null}
                  {post.source_company_name ? (
                    <>
                      <dt>{t("Source company name")}</dt>
                      <dd>{post.source_company_name}</dd>
                    </>
                  ) : null}
                  {post.source_process_unit_name ? (
                    <>
                      <dt>{t("Source process unit name")}</dt>
                      <dd>{post.source_process_unit_name}</dd>
                    </>
                  ) : null}
                  {post.source_process_unit_code ? (
                    <>
                      <dt>{t("Source business unit")}</dt>
                      <dd>{post.source_process_unit_code}</dd>
                    </>
                  ) : null}
                  {post.source_sales_pool_code ? (
                    <>
                      <dt>{t("Source sales pool")}</dt>
                      <dd>{post.source_sales_pool_code}</dd>
                    </>
                  ) : null}
                  {post.source_sales_pool_name ? (
                    <>
                      <dt>{t("Source sales pool name")}</dt>
                      <dd>{post.source_sales_pool_name}</dd>
                    </>
                  ) : null}
                  {post.source_customer_code ? (
                    <>
                      <dt>{t("Source customer code")}</dt>
                      <dd>{post.source_customer_code}</dd>
                    </>
                  ) : null}
                  {post.source_customer_name ? (
                    <>
                      <dt>{t("Source customer name")}</dt>
                      <dd>{post.source_customer_name}</dd>
                    </>
                  ) : null}
                  {post.source_project_code ? (
                    <>
                      <dt>{t("Source project code")}</dt>
                      <dd>{post.source_project_code}</dd>
                    </>
                  ) : null}
                  {post.source_project_name ? (
                    <>
                      <dt>{t("Source project name")}</dt>
                      <dd>{post.source_project_name}</dd>
                    </>
                  ) : null}
                  {post.source_system_code ? (
                    <>
                      <dt>{t("Source system")}</dt>
                      <dd>{post.source_system_code}</dd>
                    </>
                  ) : null}
                  {post.source_record_key ? (
                    <>
                      <dt>{t("Source record key")}</dt>
                      <dd>{post.source_record_key}</dd>
                    </>
                  ) : null}
                </dl>
                <p className="post-meta">{t("Raw source codes are shown; no state label was inferred.")}</p>
              </section>
            )}

					<FiveW1H slots={fiveW1H?.slots ?? null} />

				{post.project_evidence && post.project_evidence.length > 0 ? (
              <section className="popup-section" aria-label={t("Projects / semantic evidence")}>
                <h3>{t("Projects / semantic evidence")}</h3>
                <ul>
                  {post.project_evidence.map((project) => (
                    <li key={`${project.resolution_status}:${project.project_key}`}>
                      <button
                        type="button"
                        className="related-post-card"
                        aria-label={tf("Search related posts for: {name}", { name: project.project_name })}
                        onClick={() => onSearch?.(project.project_name)}
                        disabled={!onSearch}
                      >
                        <strong>{project.project_name}</strong>
                        <span>{t("Search related posts")}</span>
                      </button>{" "}
                      {project.confidence === null
                        ? `(${t("Hint only")})`
                        : `(${Math.round(project.confidence * 100)}%)`}
                      : {project.evidence}
                      <details className="semantic-provenance">
                        <summary>{t("Evidence provenance")}</summary>
                        <span className="post-badge">
                          {t("Ontology class")}: {t(project.ontology_label ?? "Project")}
                        </span>
                        <span className="post-badge">
                          {t("Extraction source")}: {projectExtractionLabel(project.extraction_method)}
                        </span>
                        <span className="post-badge">
                          {t("Evidence field")}: {projectProvenanceLabel(project.provenance)}
                        </span>
                      </details>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}

            <section className="popup-section">
              <h3>{t("Summary")}</h3>
              {summary ? (
                <>
                  {summary.summary_status === "stale" ? (
                    <p className="post-meta" role="status">
                      {t("Last saved summary shown. Retry semantic refresh.")} {" "}
                      <button type="button" onClick={() => setSummaryRetry((value) => value + 1)}>
                        {t("Retry summary refresh")}
                      </button>
                    </p>
                  ) : null}
                  <p>{summary.korean_summary}</p>
                  {(summary.key_event_details?.length ?? summary.key_events.length) > 0 && (
                    <>
                      <h4>{t("Key events")}</h4>
                      <ul>
                        {(summary.key_event_details ?? summary.key_events.map((event) => ({ event_text: event, project_name: null }))).map((event, i) => (
                          <li key={i}>
                            {event.project_name ? <strong>{event.project_name}: </strong> : null}
                            {event.event_text}
                          </li>
                        ))}
                      </ul>
                    </>
                  )}
                  {summary.roles_and_responsibilities.length > 0 && (
                    <>
                      <h4>{t("R&R")}</h4>
                      <ul>
                        {summary.roles_and_responsibilities.map((rr, i) => {
                          const isPerson = rr.actor_type_code === "prov_person";
                          const actorTypeLabel = t(
                            rr.actor_type_code === "prov_team"
                              ? "Team"
                              : isPerson
                                ? "Person"
                                : "Organization",
                          );
                          const person = isPerson
                            ? keymen?.find((row) => row.person_name === rr.actor_name)
                            : undefined;
                          const catalogId = rr.catalog_node_id;
                          const catalogType = rr.catalog_node_type_code;
                          let actorName: ReactNode = <strong>{rr.actor_name}</strong>;
                          if (catalogType === NODE_PERSON && catalogId) {
                            actorName = (
                              <button
                                className="keyman-select"
                                aria-label={tf("R&R person: {name}", { name: rr.actor_name })}
                                onClick={() => {
                                  setFocusEntity(null);
                                  setFocusTeam(null);
                                  setFocusPerson({
                                    personId: catalogId,
                                    personName: rr.actor_name,
                                  });
                                }}
                              >
                                <strong>{rr.actor_name}</strong>
                              </button>
                            );
                          } else if (person) {
                            actorName = (
                              <button
                                className="keyman-select"
                                aria-label={tf("R&R Keyman: {name}", { name: rr.actor_name })}
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
                                aria-label={tf("R&R team: {name}", { name: rr.actor_name })}
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
                                aria-label={tf("R&R organization: {name}", { name: rr.actor_name })}
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
                  {summary.major_event_actions && summary.major_event_actions.length > 0 && (
                    <>
                      <h4>{t("Major event actions")}</h4>
                      <ul className="summary-action-list">
                        {summary.major_event_actions.map((action, i) => (
                          <li key={i}>
                            <strong>
                              {action.project_name ? `${action.project_name}: ` : ""}
                              {action.action_text}
                            </strong>
                            <div>
                              {t("Requester")}: {action.requester_actor_name ?? t("Not stated in source")}
                            </div>
                            <div>
                              {t("Processor")}: {action.processor_actor_name ?? t("Not stated in source")}
                            </div>
                            <small>
                              {t("Evidence")}: {action.evidence_text}
                            </small>
                          </li>
                        ))}
                      </ul>
                    </>
                  )}
                </>
              ) : summaryError ? (
                <p className="error">{summaryError}</p>
              ) : (
                <p className="popup-placeholder">{t("No summary is available for this record yet.")}</p>
              )}
            </section>

            {!focusEventLineage && (
              <EvaluationPanel
                postId={postId}
                accessToken={accessToken}
                responses={evaluation}
                canExtract={canExtract}
                onEvaluated={(rows) => setEvaluation(rows)}
                leftoverFocus={leftoverFocus}
              />
            )}

            <VocEvidenceSection
              evidence={vocEvidence}
              affiliateTrees={affiliateTrees}
              onSelectPerson={(personId, personName) => {
                setFocusEntity(null);
                setFocusTeam(null);
                setFocusPerson({ personId, personName });
              }}
            />

            <SimilarVocPanel
              items={similarVoc}
              error={similarVocError}
              onOpenPost={(candidatePostId) => onSelectPost?.(candidatePostId)}
              loadingMore={similarVocLoadingMore}
              onLoadMore={similarVocNextOffset === null ? null : () => {
                if (similarVocLoadingMoreRef.current) return;
                const requestScope = similarVocScopeRef.current;
                similarVocLoadingMoreRef.current = true;
                setSimilarVocLoadingMore(true);
                setSimilarVocError(null);
                fetchSimilarVoc(accessToken, postId, similarVocNextOffset)
                  .then((result) => {
                    if (similarVocScopeRef.current !== requestScope) return;
                    setSimilarVoc((current) => [...(current ?? []), ...result.items]);
                    setSimilarVocNextOffset(result.next_offset);
                  })
                  .catch(() => {
                    if (similarVocScopeRef.current === requestScope) {
                      setSimilarVocError("이전 VOC를 더 불러오지 못했습니다. 다시 시도하세요.");
                    }
                  })
                  .finally(() => {
                    if (similarVocScopeRef.current !== requestScope) return;
                    similarVocLoadingMoreRef.current = false;
                    setSimilarVocLoadingMore(false);
                  });
              }}
            />

            <RelatedPostsSection lineage={lineage} onSelectPost={onSelectPost} />

            <section className="popup-section">
                <h3 id="post-event-lineage" tabIndex={-1}>
                {t("Event Lineage")}
              </h3>
              <EventLineageSection
                lineage={lineage}
                graph={graph}
                postId={postId}
                onSelectPost={onSelectPost}
                currentNextAction={
                  focusEventLineage ? eventLineageCurrentNextAction(post.post_title) : null
                }
              />
            </section>

            {focusEventLineage && (
              <KeymanPanel
                postId={postId}
                accessToken={accessToken}
                keymen={keymen}
                sourceAuthorContext={sourceAuthorContext}
                canExtract={canExtract}
                onExtracted={reloadKeymen}
                onSelectPost={onSelectPost}
                focusPerson={focusPerson}
                focusEntity={focusEntity}
                focusTeam={focusTeam}
                landFirstKeyman
                landFirstRelated
                afterList={
                  <>
                    <EvaluationPanel
                      postId={postId}
                      accessToken={accessToken}
                      responses={evaluation}
                      canExtract={canExtract}
                      onEvaluated={(rows) => setEvaluation(rows)}
                      leftoverFocus={leftoverFocus}
                    />
                    {keymen?.[0] ? (
                      <p className="post-meta" role="status" aria-label={t("Keyman next action")}>
                        {firstKeymanNextAction(keymen[0].person_name)}
                      </p>
                    ) : null}
                  </>
                }
              />
            )}

            <section className="popup-section">
              <h3>{t("Affiliate tree")}</h3>
              {affiliateTrees === null ? (
                <p role="status">{t("Loading affiliate tree...")}</p>
              ) : affiliateTrees.length === 0 ? (
                <p className="popup-placeholder">{t("No affiliations on this post yet.")}</p>
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

            {!focusEventLineage && (
              <KeymanPanel
                postId={postId}
                accessToken={accessToken}
                keymen={keymen}
                sourceAuthorContext={sourceAuthorContext}
                canExtract={canExtract}
                onExtracted={reloadKeymen}
                onSelectPost={onSelectPost}
                focusPerson={focusPerson}
                focusEntity={focusEntity}
                focusTeam={focusTeam}
              />
            )}

            {counterparties && counterparties.length > 0 && (
              <CounterpartyPanel
                postId={postId}
                accessToken={accessToken}
                counterparties={counterparties}
                canExtract={canExtract}
                onVerified={reloadCounterparties}
                onSelectPost={onSelectPost}
                onSelectEntity={(entityId, entityName) => {
                  setFocusPerson(null);
                  setFocusTeam(null);
                  setFocusEntity({ entityId, entityName });
                }}
              />
            )}

            <IssueTicketPanel postId={postId} accessToken={accessToken} canExtract={canExtract} />

            <ActivityPanel postId={postId} accessToken={accessToken} />

            {!focusEventLineage && (
              <ChatPanel postId={postId} accessToken={accessToken} />
            )}
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
 * Next action for a pending or failed run on the home list and detail.
 *
 * The machine `failure_code` stays on detail history (ADR 0014). Copy
 * is pinned to registered kinds so a pending TEPP row is not mistaken
 * for reconstruction, and a failed lineage row is not mistaken for a
 * missing TEPP transport.
 */
function analysisRunNextAction(run: AnalysisRun): string | null {
  switch (run.status_code) {
    case "analysis_status_pending":
      switch (run.run_kind_code) {
        case "analysis_run_lineage":
          return "Open this run, then start reconstruction. Reconstruction has not started yet.";
        case "analysis_run_tepp":
          return "Open this run to confirm which posts TEPP will measure. Measurement has not started yet — this is not a calibrated result.";
        case "analysis_run_topic_lineage":
          return "Open this run to confirm which posts TEPP will thread into topic lineage. Topic-lineage analysis has not started yet — this is not a calibrated topic result.";
        case "analysis_run_report":
          return "Open this run to confirm which posts the period report will use. The report has not been built yet.";
        default: {
          const unexpected: never = run.run_kind_code;
          return unexpected;
        }
      }
    case "analysis_status_failed":
      switch (run.run_kind_code) {
        case "analysis_run_tepp":
          return "Open this run to see why it failed, then connect the measurement service and re-run.";
        case "analysis_run_topic_lineage":
          return "Open this run to see why it failed, then connect the TEPP transport and re-run.";
        case "analysis_run_lineage":
          return "Open this run to see why it failed, then retry reconstruction from a current snapshot.";
        case "analysis_run_report":
          return "Open this run to see why it failed, then rebuild the period report from a current snapshot.";
        default: {
          const unexpected: never = run.run_kind_code;
          return unexpected;
        }
      }
    case "analysis_status_running":
      return "Refresh this run. Start already queued the work on the durable outbox.";
    case "analysis_status_succeeded":
    case "analysis_status_cancelled":
    case null:
      return null;
    default: {
      const unexpected: never = run.status_code;
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
    case "analysis_run_topic_lineage":
      return (
        "No posts were available at this cutoff for topic-lineage analysis. " +
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
 * Corpus copy for a TEPP or topic-lineage run that already has cutoff posts.
 *
 * Those titles are the measurement bag, not a reconstruction result.
 * Pending or running must not claim a calibrated measurement or topic.
 */
function analysisRunCorpusHint(run: AnalysisRun): string | null {
  const isTopicLineage = run.run_kind_code === "analysis_run_topic_lineage";
  if (run.run_kind_code !== "analysis_run_tepp" && !isTopicLineage) return null;
  const service = isTopicLineage ? "topic-lineage" : "TEPP";
  const result = isTopicLineage ? "a topic-identity result" : "a calibrated result";
  const verb = isTopicLineage ? "thread" : "measure";
  const verbPast = isTopicLineage ? "threaded" : "measured";
  switch (run.status_code) {
    case "analysis_status_failed":
      return (
        `These posts are the cutoff corpus ${service} would ${verb}. Connect a TEPP ` +
        `transport, then re-run, to replace Failed with ${result}.`
      );
    case "analysis_status_succeeded":
      return `These posts are the cutoff corpus this ${service} run ${verbPast}.`;
    case "analysis_status_pending":
    case "analysis_status_running":
      return `These posts are the cutoff corpus ${service} will ${verb} once this run finishes.`;
    case "analysis_status_cancelled":
      return (
        `These posts are the cutoff corpus this ${service} run would have ${verbPast}. ` +
        `The run was cancelled before ${result}.`
      );
    case null:
      return `These posts are the cutoff corpus attached to this ${service} run.`;
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

type LeftoverPairFocus = {
  pairKind: "closest" | "farthest";
  criterionCode: string;
};

type SelectPostOptions = {
  liveAfterCutoff?: boolean;
  knowledgeCutoff?: string;
  fromReportMember?: boolean;
  fromLeftoverPair?: LeftoverPairFocus;
};

/**
 * Next action when a cutoff title opens the live post (ADR 0016 / 0025).
 *
 * Titles marked `live_after_cutoff` were rewritten after this run;
 * others still match the write clock the run knew. The popup then
 * shows the stored cutoff-known body beside the live rewrite. A
 * missing revision is omitted -- never an invented earlier sentence.
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
 * Popup next action when a marked cutoff title opens the live body.
 *
 * ADR 0025 stores the earlier sentence on source_post_revision. This
 * copy still names the live body so the operator compares two texts.
 */
function analysisRunOpenedBodyWarning(cutoffIso?: string | null): string {
  const cutoffDate = cutoffIso?.slice(0, 10);
  const when = cutoffDate ? ` this ${cutoffDate}` : " this";
  return (
    "This is the live body, not a cutoff snapshot. " +
    `Compare it with${when} run before you treat it as reconstructed evidence.`
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
  reconstructionResultSha256,
}: {
  codeRevisionSha?: string;
  configurationSha256?: string;
  reconstructionResultSha256?: string;
}) {
  const parts: { label: string; digest: string }[] = [];
  if (codeRevisionSha) {
    parts.push({ label: "Code", digest: codeRevisionSha });
  }
  if (configurationSha256) {
    parts.push({ label: "Config", digest: configurationSha256 });
  }
  if (reconstructionResultSha256) {
    parts.push({ label: "Result", digest: reconstructionResultSha256 });
  }
  if (parts.length === 0) {
    return null;
  }
  return (
    <div role="group" aria-label="Analysis run reproducibility digests">
      <p className="post-meta">
        <span className="visually-hidden">
          Hover a prefix to read the full digest for verification.{" "}
        </span>
        {parts.map((part, index) => (
          <span key={part.label}>
            {index > 0 ? " · " : null}
            <span title={part.digest}>{`${part.label} ${analysisRunDigestPrefix(part.digest)}`}</span>
          </span>
        ))}
      </p>
    </div>
  );
}

/**
 * Start is for a Pending lineage or TEPP row after Request.
 *
 * Period-report keeps its own rebuild path. TEPP start goes through
 * tepp_client and must not be labeled reconstruction.
 */
function analysisRunCanStart(run: AnalysisRun): boolean {
  return (
    (run.run_kind_code === "analysis_run_lineage" ||
      run.run_kind_code === "analysis_run_tepp" ||
      run.run_kind_code === "analysis_run_topic_lineage") &&
    (run.status_code === "analysis_status_pending" ||
      run.status_code === "analysis_status_running")
  );
}

function analysisRunStartLabel(run: AnalysisRun): string {
  if (run.run_kind_code === "analysis_run_tepp") {
    return "Start TEPP measurement";
  }
  if (run.run_kind_code === "analysis_run_topic_lineage") {
    return "Start topic lineage";
  }
  return "Start reconstruction";
}

/** Failed TEPP/topic-lineage is terminal. Create cannot invent a Pending row. */
function analysisRunCanRequestTeppRetry(run: AnalysisRun): boolean {
  return (
    (run.run_kind_code === "analysis_run_tepp" ||
      run.run_kind_code === "analysis_run_topic_lineage") &&
    run.status_code === "analysis_status_failed"
  );
}

const REPORT_PERIOD_KEY = /^\d{4}-W\d{2}$/;

/**
 * Period code stored on a succeeded report run's scope key.
 *
 * That key is a week label, not a theta. Missing or malformed keys
 * stay closed so we do not invent a period.
 */
/**
 * Report grouping that matches the run's authorized scope.
 *
 * A corporate-entity run must not leave the panel on business unit (PU).
 */
function analysisRunReportGrouping(run: AnalysisRun): string | null {
  switch (run.scope_kind_code) {
    case "analysis_scope_corporate_entity":
      return "corporate_entity";
    case "analysis_scope_process_unit":
      return "process_unit";
    case "analysis_scope_thread_group":
      return "thread_group";
    default:
      return null;
  }
}

function analysisRunReportGroupingKey(run: AnalysisRun): string | undefined {
  return run.scope_grouping_key || undefined;
}

function analysisRunReportPeriod(run: AnalysisRun): string | null {
  if (run.run_kind_code !== "analysis_run_report") {
    return null;
  }
  if (run.status_code !== "analysis_status_succeeded") {
    return null;
  }
  const key = run.scope_key;
  if (!key || !REPORT_PERIOD_KEY.test(key)) {
    return null;
  }
  return key;
}

/**
 * Open options for a reconstructed parent or child.
 *
 * The run-scoped edge is the reconstruction result. The popup still
 * shows the live body; reuse the cutoff write-clock flag when that
 * title is marked rewritten after this run.
 */
function analysisRunPostOpenOptions(run: AnalysisRun, postId: string): SelectPostOptions {
  const post = run.visible_posts?.find((item) => item.post_id === postId);
  return {
    liveAfterCutoff: Boolean(post?.live_after_cutoff),
    knowledgeCutoff: run.knowledge_cutoff,
  };
}

const VISIBLE_POSTS_RENDER_LIMIT = 200;

// Live finding (2026-08-19): the backend already caps source_customer_hints
// / source_author_hints at 100 rows each, but real imported data hits that
// cap routinely (unresolved codes are the common case), and each row's own
// "Related posts" details -- collapsed by default but still mounted in the
// DOM -- pushed the page to a ~37,000px scroll height. Same pattern as
// VISIBLE_POSTS_RENDER_LIMIT above: cap the initial render, name the total.
const HINT_RENDER_LIMIT = 30;

function AnalysisRunsPanel({
  accessToken,
  currentReportPeriod,
  onSelectPost,
  onSelectReportPeriod,
  corporateEntities,
  entitiesLoadError,
}: {
  accessToken: string;
  currentReportPeriod?: string;
  onSelectPost: (postId: string, options?: SelectPostOptions) => void;
  onSelectReportPeriod?: (
    periodCode: string,
    groupingKind?: string,
    groupingKey?: string,
    groupingLabel?: string,
  ) => void;
  corporateEntities: CorporateEntityRef[] | null;
  entitiesLoadError: string | null;
}) {
  const [runs, setRuns] = useState<AnalysisRun[] | null>(null);
  const [selected, setSelected] = useState<AnalysisRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [requesting, setRequesting] = useState(false);
  const [starting, setStarting] = useState(false);
  const [selectedEntityId, setSelectedEntityId] = useState("");
  const inFlightKeyRef = useRef<string | null>(null);
  const entitiesReady = corporateEntities !== null && entitiesLoadError === null;
  const requestLabel = requesting
    ? "Recording the run..."
    : entitiesLoadError
      ? "Reload to choose a corporate entity"
      : corporateEntities === null
        ? "Loading affiliated entities..."
        : "Request a lineage reconstruction";

  useEffect(() => {
    fetchAnalysisRuns(accessToken)
      .then((payload) => setRuns(payload.analysis_runs))
      .catch((err) => setError(String(err)));
  }, [accessToken]);

  useEffect(() => {
    if (!corporateEntities?.length) {
      return;
    }
    setSelectedEntityId((current) => current || corporateEntities[0].corporate_entity_id);
  }, [corporateEntities]);

  async function handleRequestLineage() {
    if (corporateEntities === null || entitiesLoadError) {
      setError(
        entitiesLoadError ?? "Reload to load the corporate entities this account may reconstruct.",
      );
      return;
    }
    if (corporateEntities.length > 1 && !selectedEntityId) {
      setError("Choose which corporate entity to reconstruct.");
      return;
    }
    setError(null);
    setRequesting(true);
    if (inFlightKeyRef.current === null) {
      inFlightKeyRef.current = crypto.randomUUID();
    }
    const idempotencyKey = inFlightKeyRef.current;
    try {
      const created = await createAnalysisRun(accessToken, {
        run_kind_code: "analysis_run_lineage",
        idempotency_key: idempotencyKey,
        ...(selectedEntityId ? { corporate_entity_id: selectedEntityId } : {}),
      });
      const listed = await fetchAnalysisRuns(accessToken);
      setRuns(listed.analysis_runs);
      setSelected(created);
      inFlightKeyRef.current = null;
    } catch (err) {
      if (err instanceof BackendError && err.status === 409) {
        inFlightKeyRef.current = null;
        setError(
          "This request key already names a different reconstruction. Request again to start a new run.",
        );
      } else {
        setError(err instanceof BackendError ? err.message : String(err));
      }
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
  if (runs === null) return <p role="status">Loading analysis runs...</p>;

  const corpusHint = selected ? analysisRunCorpusHint(selected) : null;
  const selectedNextAction = selected ? analysisRunNextAction(selected) : null;

  return (
    <section className="popup-section lineage-home">
      <div className="lineage-home-header">
        <h2>{t("Analysis runs")}</h2>
        <LineageEntityPicker
          entities={corporateEntities ?? []}
          selectedEntityId={selectedEntityId}
          onSelectEntityId={setSelectedEntityId}
        />
        <button
          className="keyman-select"
          aria-label={requestLabel}
          aria-busy={corporateEntities === null || requesting}
          disabled={
            requesting ||
            !entitiesReady ||
            (corporateEntities !== null && corporateEntities.length > 1 && !selectedEntityId)
          }
          onClick={() => void handleRequestLineage()}
        >
          {requestLabel}
        </button>
      </div>
      {(error || entitiesLoadError) && <p className="error">{error ?? entitiesLoadError}</p>}
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
          {selectedNextAction && <p className="post-meta">{selectedNextAction}</p>}
          <p className="post-meta">
            Cutoff {selected.knowledge_cutoff.slice(0, 10)}
            {" · "}
            Requested {selected.requested_at.slice(0, 10)}
          </p>
          <AnalysisRunReproducibilityDigests
            codeRevisionSha={selected.code_revision_sha}
            configurationSha256={selected.configuration_sha256}
            reconstructionResultSha256={selected.reconstruction_result_sha256}
          />
          {analysisRunCanStart(selected) && (
            <button
              className="keyman-select"
              aria-label={analysisRunStartLabel(selected)}
              disabled={starting}
              onClick={() => void handleStartReconstruction()}
            >
              {starting
                ? selected.run_kind_code === "analysis_run_tepp"
                  ? "Submitting the TEPP request..."
                  : selected.run_kind_code === "analysis_run_topic_lineage"
                    ? "Submitting the topic-lineage request..."
                    : "Reconstructing the cutoff bag..."
                : analysisRunStartLabel(selected)}
            </button>
          )}
          {analysisRunCanRequestTeppRetry(selected) && (
            <p className="post-meta">
              {selected.run_kind_code === "analysis_run_topic_lineage"
                ? "Connect a TEPP transport from this Failed row. Request a " +
                  "lineage reconstruction does not invent a topic model."
                : "Connect a TEPP transport from this Failed row. Request a lineage " +
                  "reconstruction does not invent a measurement."}
            </p>
          )}
          {analysisRunReportPeriod(selected) && onSelectReportPeriod && (
            <button
              className="keyman-select"
              aria-label={`Open period report ${analysisRunReportPeriod(selected)}`}
              onClick={() => {
                const periodCode = analysisRunReportPeriod(selected);
                if (periodCode) {
                  const alreadyOnWeek = currentReportPeriod === periodCode;
                  onSelectReportPeriod(
                    periodCode,
                    analysisRunReportGrouping(selected) ?? undefined,
                    analysisRunReportGroupingKey(selected),
                    selected.scope_entity_name,
                  );
                  if (!alreadyOnWeek) {
                    document.getElementById("report-period")?.focus();
                  }
                }
              }}
            >
              Open period report {analysisRunReportPeriod(selected)}
            </button>
          )}
          {selected.reconstructed_edges && selected.reconstructed_edges.length > 0 && (
            <ul aria-label="Reconstructed lineage edges">
              {selected.reconstructed_edges.map((edge) => (
                <li key={`${edge.parent_post_id}-${edge.child_post_id}`}>
                  <button
                    className="keyman-select"
                    aria-label={`Open reconstructed child: ${edge.child_post_title}`}
                    onClick={() =>
                      onSelectPost(
                        edge.child_post_id,
                        analysisRunPostOpenOptions(selected, edge.child_post_id),
                      )
                    }
                  >
                    {edge.child_post_title}
                  </button>
                  {" follows "}
                  <button
                    className="keyman-select"
                    aria-label={`Open reconstructed parent: ${edge.parent_post_title}`}
                    onClick={() =>
                      onSelectPost(
                        edge.parent_post_id,
                        analysisRunPostOpenOptions(selected, edge.parent_post_id),
                      )
                    }
                  >
                    {edge.parent_post_title}
                  </button>
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
          {selected.outbox_deliveries && selected.outbox_deliveries.length > 0 && (
            <ol aria-label="Analysis run outbox delivery">
              {selected.outbox_deliveries.map((event) => (
                <li key={event.delivery_ordinal}>
                  {event.delivery_status_label} {event.occurred_at.slice(0, 16).replace("T", " ")}
                </li>
              ))}
            </ol>
          )}
          {selected.visible_posts && selected.visible_posts.length > 0 ? (
            <>
              {corpusHint && <p className="post-meta">{corpusHint}</p>}
              <p className="post-meta">{analysisRunLivePostWarning(selected.knowledge_cutoff)}</p>
              {selected.visible_posts.length > VISIBLE_POSTS_RENDER_LIMIT && (
                <p className="post-meta">
                  {tf("Showing the first {shown} of {total} posts known at this cutoff.", {
                    shown: VISIBLE_POSTS_RENDER_LIMIT,
                    total: selected.visible_posts.length,
                  })}
                </p>
              )}
              <ul aria-label="Posts known at this run cutoff">
                {selected.visible_posts.slice(0, VISIBLE_POSTS_RENDER_LIMIT).map((post) => (
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
                      <span className="post-badge">{t("Updated after cutoff")}</span>
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

function formatRankingContribution(value: number): string {
  return value.toFixed(6);
}

function RankingsPanel({
  accessToken,
  onSelectPost,
}: {
  accessToken: string;
  onSelectPost: (postId: string) => void;
}) {
  const [ranking, setRanking] = useState<RankingList | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    fetchRankings(accessToken)
      .then(setRanking)
      .catch((err) => setError(String(err)));
  }, [accessToken]);

  return (
    <section className="popup-section lineage-home" aria-label={t("Rankings")}>
      <div className="lineage-home-header">
        <h2>{t("Rankings")}</h2>
        {ranking && (
          <span className="post-badge">
            {ranking.status === "accepted"
              ? t("Ranked result")
              : t("Rankings temporarily unavailable")}
          </span>
        )}
      </div>
      {error && <p className="error">{error}</p>}
      {ranking === null && !error && <p role="status">{t("Loading rankings...")}</p>}
      {ranking && ranking.status === "unavailable" && (
        <p className="popup-placeholder">{t("Rankings are temporarily unavailable. Try again later.")}</p>
      )}
      {ranking && ranking.status === "accepted" && ranking.rankings.length === 0 && (
        <p className="popup-placeholder">{t("No ranked records are available. Try a broader search.")}</p>
      )}
      {ranking && ranking.rankings.length > 0 && (
        <>
          <p className="ranking-channel-evidence-copy">
            {t(
              "Open a result to review the records most relevant to your search. These results are not calibrated measurements.",
            )}
          </p>
          <ul className="ticket-list" aria-label={t("Ranked records")}>
            {ranking.rankings.map((hit) => (
              <li key={hit.post_id} className="ticket-list-item ranking-hit">
                <button
                  className="post-list-item"
                  aria-label={tf("Open ranking: {title}", { title: hit.post_title })}
                  onClick={() => onSelectPost(hit.post_id)}
                >
                  <span className="ticket-title">{hit.post_title}</span>
                  <span className="post-badge">{t("Ranked result")}</span>
                  <span className="post-badge">{tf("rank {rank}", { rank: String(hit.fused_rank) })}</span>
                </button>
                {(hit.channel_evidence ?? []).length > 0 ? (
                  <ul
                    className="ranking-channel-evidence"
                    aria-label={tf("Ranking evidence for {title}", { title: hit.post_title })}
                  >
                    {(hit.channel_evidence ?? []).map((item) => (
                      <li key={item.signal_code}>
                        {tf("{label} rank {rank}, contribution {contribution}", {
                          label: t(item.signal_label),
                          rank: String(item.channel_rank),
                          contribution: formatRankingContribution(item.contribution),
                        })}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

function CalendarPanel({
  accessToken,
  onSelectPost,
  headingId = "lab-calendar-heading",
  heading,
}: {
  accessToken: string;
  onSelectPost: (postId: string) => void;
  headingId?: string;
  heading?: string;
}) {
  const [calendar, setCalendar] = useState<CalendarResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCalendar(accessToken)
      .then(setCalendar)
      .catch((err) => setError(String(err)));
  }, [accessToken]);

  if (error) return <p className="error">{error}</p>;
  if (calendar === null) return <p role="status">{t("Loading calendar...")}</p>;

  return (
    <WorkspaceCalendar
      calendar={calendar}
      onSelectPost={onSelectPost}
      headingId={headingId}
      heading={heading ?? t("Calendar")}
    />
  );
}

const REPORT_GROUPING_LABELS: Record<string, string> = {
  process_unit: "Business unit (PU)",
  corporate_entity: "Corporate entity",
  thread_group: "Thread group",
  team: "Team",
  project: "Project",
};

function comparisonGroupingTitle(groupingKind: string, groupingLabel: string): string {
  return `${t(REPORT_GROUPING_LABELS[groupingKind] ?? groupingKind)}: ${groupingLabel}`;
}

function comparisonChipAccessibleName(
  groupingKind: string,
  groupingLabel: string,
  meanTheta: number,
): string {
  return `Compare ${comparisonGroupingTitle(groupingKind, groupingLabel)}, mean θ ${meanTheta.toFixed(2)}`;
}

function openedReportNextAction(
  groupingLabel: string,
  openedMemberTitle?: string | null,
): string {
  if (openedMemberTitle) {
    return (
      `${openedMemberTitle} is open from ${groupingLabel}. ` +
      "Read Event Lineage, Keyman, and evaluation on this post."
    );
  }
  return (
    `${groupingLabel} is the opened grouping. Read its mean θ and member posts below, then open a post.`
  );
}

function openedReportsFirst<T extends { grouping_key: string; grouping_label?: string }>(
  reports: T[],
  isOpened: (groupingKey: string, groupingLabel?: string) => boolean,
): T[] {
  const opened = reports.filter((report) => isOpened(report.grouping_key, report.grouping_label));
  if (opened.length === 0) {
    return reports;
  }
  const rest = reports.filter((report) => !isOpened(report.grouping_key, report.grouping_label));
  return [...opened, ...rest];
}

function ReportsPanel({
  accessToken,
  canRebuild,
  onSelectPost,
  period,
  onSelectPeriod,
  grouping,
  onSelectGrouping,
  openedGroupingKey,
  openedGroupingLabel,
  onOpenGrouping,
  landOnComparison,
  selectedPostId,
}: {
  accessToken: string;
  canRebuild: boolean;
  onSelectPost: (postId: string, options?: SelectPostOptions) => void;
  period: string;
  onSelectPeriod: (periodCode: string) => void;
  grouping: string;
  onSelectGrouping: (groupingKind: string) => void;
  openedGroupingKey?: string | null;
  openedGroupingLabel?: string | null;
  onOpenGrouping?: (groupingKey: string, groupingLabel: string) => void;
  landOnComparison?: boolean;
  selectedPostId?: string | null;
}) {
  const [payload, setPayload] = useState<PeriodReports | null>(null);
  const [index, setIndex] = useState<PeriodReportIndex | null>(null);
  const [comparison, setComparison] = useState<PeriodComparison | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rebuilding, setRebuilding] = useState(false);
  const openedComparisonRef = useRef<HTMLButtonElement | null>(null);

  function groupingIsOpened(groupingKind: string, groupingKey: string, groupingLabel?: string) {
    if (groupingKind !== grouping) {
      return false;
    }
    if (openedGroupingKey && groupingKey === openedGroupingKey) {
      return true;
    }
    return Boolean(openedGroupingLabel && groupingLabel && groupingLabel === openedGroupingLabel);
  }

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

  useEffect(() => {
    if (!landOnComparison) {
      return;
    }
    const current = openedComparisonRef.current;
    if (!current) {
      return;
    }
    current.scrollIntoView({ block: "nearest" });
    current.focus();
  }, [landOnComparison, grouping, openedGroupingKey, openedGroupingLabel, comparison]);

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

  const orderedReports = payload
    ? openedReportsFirst(payload.reports, (groupingKey, groupingLabel) =>
        groupingIsOpened(grouping, groupingKey, groupingLabel),
      )
    : [];
  const openedMemberTitle = selectedPostId
    ? orderedReports
        .filter((report) =>
          groupingIsOpened(grouping, report.grouping_key, report.grouping_label),
        )
        .flatMap((report) => report.members)
        .find((member) => member.post_id === selectedPostId)?.post_title
    : undefined;
  const reportList =
    payload === null && !error ? (
      <p role="status">Loading reports...</p>
    ) : payload && payload.reports.length === 0 ? (
      <p className="popup-placeholder">
        No calibrated report for this grouping and period. Evaluate posts, then rebuild.
      </p>
    ) : payload && payload.reports.length > 0 ? (
      <ul
        className="ticket-list"
        aria-label={openedGroupingLabel ? "Opened grouping report" : "Period report groups"}
      >
        {orderedReports.map((report) => (
          <li
            key={report.grouping_key}
            className="ticket-list-item"
            aria-current={
              groupingIsOpened(grouping, report.grouping_key, report.grouping_label)
                ? "true"
                : undefined
            }
          >
            <span className="ticket-title">
              {report.grouping_label ?? report.grouping_key}: mean θ {report.mean_theta.toFixed(2)} ({report.selected_model}
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
            {report.leftover_map_coverage && report.leftover_map_coverage.scored_post_count > 0 && (
              <p className="post-meta" role="note" aria-label={t("Leftover map coverage")}>
                {tf("Leftover map used {used} of {scored} scored posts (complete-case)", {
                  used: report.leftover_map_coverage.map_post_count,
                  scored: report.leftover_map_coverage.scored_post_count,
                })}
              </p>
            )}
            {report.leftover_map_axes?.map((axis) => (
              <span key={axis.axis_index} className="post-badge">
                {tf("leftover axis {axis} {share}%", {
                  axis: axis.axis_index,
                  share: (axis.leftover_share * 100).toFixed(0),
                })}
              </span>
            ))}
            {report.leftover_map_axes && report.leftover_map_axes.length > 0 && (
              <p aria-label={t("Leftover-map axis share")}>
                {t(
                  "Leftover-map axis share is Gabriel inertia of residual SVD axes 1 and 2. Open a leftover pair to read the post–criterion cell. The shares do not invent a leftover score.",
                )}
              </p>
            )}
            {report.leftover_pairs && report.leftover_pairs.length > 0 && (
              <LeftoverPairList
                pairs={report.leftover_pairs}
                criterionLabel={criterionShortLabel}
                onSelectPost={(pair) => {
                  onSelectPost(pair.post_id, {
                    fromLeftoverPair: {
                      pairKind: pair.pair_kind === "farthest" ? "farthest" : "closest",
                      criterionCode: pair.criterion_code,
                    },
                  });
                }}
              />
            )}
            {report.members.length > 0 && (
              <ul className="ticket-list">
                {report.members.map((member) => (
                  <li key={member.post_id} className="ticket-list-item">
                    <button
                      className="post-list-item"
                      aria-label={`Open report post: ${member.post_title}`}
                      aria-current={
                        selectedPostId && member.post_id === selectedPostId
                          ? "true"
                          : undefined
                      }
                      onClick={() => onSelectPost(member.post_id, { fromReportMember: true })}
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
    ) : null;

  return (
    <section className="popup-section lineage-home">
      <div className="lineage-home-header">
        <h2>{t("Period reports")}</h2>
        {canRebuild && (
          <button onClick={handleRebuild} disabled={rebuilding}>
            {rebuilding ? "Calibrating..." : "Rebuild report"}
          </button>
        )}
      </div>
      <div className="chat-input-row">
        <label>
          Grouping
          <select aria-label="Report grouping" value={grouping} onChange={(event) => onSelectGrouping(event.target.value)}>
            <option value="process_unit">{t("Business unit (PU)")}</option>
            <option value="corporate_entity">Corporate entity</option>
            <option value="thread_group">Thread group</option>
            <option value="team">Team</option>
            <option value="project">Project</option>
          </select>
        </label>
        <label>
          Period
          <input
            id="report-period"
            aria-label="Report period"
            value={period}
            onChange={(event) => onSelectPeriod(event.target.value)}
          />
        </label>
      </div>
      {comparison && comparison.groupings.length > 0 && (
        <ul className="ticket-list" aria-label="Grouping comparison">
          {comparison.groupings.map((row) => (
            <li key={`${row.grouping_kind}:${row.grouping_key}`} className="ticket-list-item">
              <button
                className="post-list-item"
                ref={
                  groupingIsOpened(row.grouping_kind, row.grouping_key, row.grouping_label)
                    ? openedComparisonRef
                    : undefined
                }
                aria-label={comparisonChipAccessibleName(
                  row.grouping_kind,
                  row.grouping_label,
                  row.mean_theta,
                )}
                aria-current={
                  groupingIsOpened(row.grouping_kind, row.grouping_key, row.grouping_label)
                    ? "true"
                    : undefined
                }
                onClick={() => {
                  onSelectGrouping(row.grouping_kind);
                  onOpenGrouping?.(row.grouping_key, row.grouping_label);
                }}
              >
                <span className="ticket-title">
                  {comparisonGroupingTitle(row.grouping_kind, row.grouping_label)}
                </span>
                <span className="post-badge">mean θ {row.mean_theta.toFixed(2)}</span>
                <span className="post-badge">{row.post_count} posts</span>
              </button>
              {row.leftover_pairs && row.leftover_pairs.length > 0 && (
                <ul className="ticket-list" aria-label={`Leftover pairs for ${row.grouping_label}`}>
                  {row.leftover_pairs.map((pair) => {
                    const kindLabel =
                      pair.pair_kind === "farthest" ? "Farthest leftover" : "Closest leftover";
                    const nextAction =
                      pair.pair_kind === "farthest"
                        ? "Open this post to read the criterion it sat farthest from after main effects."
                        : "Open this post to read the criterion it sat closest to after main effects.";
                    const criterion = criterionShortLabel(pair.criterion_code);
                    return (
                      <li
                        key={`${row.grouping_kind}:${row.grouping_key}:${pair.pair_kind}:${pair.post_id}:${pair.criterion_code}`}
                        className="ticket-list-item"
                      >
                        <button
                          className="post-list-item"
                          aria-label={`Open leftover ${pair.pair_kind} pair from comparison: ${pair.post_title} · ${criterion}`}
                          onClick={() =>
                            // Same promise, same landing: the badge tells the
                            // reader the criterion will be current in Post
                            // quality, exactly like the report-panel pairs
                            // (ADR 0158), so the strip carries the same focus.
                            onSelectPost(pair.post_id, {
                              fromLeftoverPair: {
                                pairKind: pair.pair_kind === "farthest" ? "farthest" : "closest",
                                criterionCode: pair.criterion_code,
                              },
                            })
                          }
                        >
                          <span className="ticket-title">
                            {kindLabel}: {pair.post_title} · {criterion}
                          </span>
                          <span className="post-badge">{nextAction}</span>
                          <span className="post-badge">d {pair.leftover_distance.toFixed(2)}</span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </li>
          ))}
        </ul>
      )}
      {openedGroupingLabel && (
        <p className="post-meta" role="status">
          {openedReportNextAction(openedGroupingLabel, openedMemberTitle)}
        </p>
      )}
      {openedGroupingLabel && reportList}
      {index && index.periods.length > 0 && (
        <ul className="ticket-list">
          {index.periods.map((row) => (
            <li key={`${row.period_code}:${row.grouping_key}`} className="ticket-list-item">
              <button
                className="post-list-item"
                aria-label={`Open report period ${row.period_code}`}
                onClick={() => onSelectPeriod(row.period_code)}
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
      {!openedGroupingLabel && reportList}
    </section>
  );
}

const POST_PAGE_SIZE = 50;
type BoardSortOrder = PostSortOrder;

function PostList({
  accessToken,
  showLabPanels = false,
  postIdToOpen = null,
  onPostOpened,
}: {
  accessToken: string;
  showLabPanels?: boolean;
  postIdToOpen?: string | null;
  onPostOpened?: () => void;
}) {
  const [posts, setPosts] = useState<PostSummary[] | null>(null);
  const [focusedGraph, setFocusedGraph] = useState<LineageGraph | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedPostId, setSelectedPostId] = useState<string | null>(null);
  const [openedAfterCutoff, setOpenedAfterCutoff] = useState(false);
  const [openedCutoffIso, setOpenedCutoffIso] = useState<string | null>(null);
  const [canRebuild, setCanRebuild] = useState(false);
  const [rebuilding, setRebuilding] = useState(false);
  const [rebuildError, setRebuildError] = useState<string | null>(null);
  const [reportPeriod, setReportPeriod] = useState("2026-W02");
  const [reportGrouping, setReportGrouping] = useState("process_unit");
  const [openedGroupingKey, setOpenedGroupingKey] = useState<string | null>(null);
  const [openedGroupingLabel, setOpenedGroupingLabel] = useState<string | null>(null);
  const [landOnComparison, setLandOnComparison] = useState(false);
  const [openedFromReportMember, setOpenedFromReportMember] = useState(false);
  const [openedLeftoverPair, setOpenedLeftoverPair] = useState<LeftoverPairFocus | null>(null);
  const [corporateEntities, setCorporateEntities] = useState<CorporateEntityRef[] | null>(null);
  const [entitiesLoadError, setEntitiesLoadError] = useState<string | null>(null);
  const [totalPosts, setTotalPosts] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [loadingPage, setLoadingPage] = useState(false);
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<string[]>([]);
  const [vocTypeFilterOptions, setVocTypeFilterOptions] = useState<PostFilterOption[]>([]);
  const [visibilityFilter, setVisibilityFilter] = useState("all");
  const [visibilityFilterOptions, setVisibilityFilterOptions] = useState<PostFilterOption[]>([]);
  const [sortOrder, setSortOrder] = useState<BoardSortOrder>("newest");
  const postsRequest = useRef(0);

  function openReportFromAnalysisRun(
    periodCode: string,
    groupingKind?: string,
    groupingKey?: string,
    groupingLabel?: string,
  ) {
    setLandOnComparison(reportPeriod === periodCode);
    setReportPeriod(periodCode);
    if (groupingKind) {
      setReportGrouping(groupingKind);
    }
    setOpenedGroupingKey(groupingKey ?? null);
    setOpenedGroupingLabel(groupingLabel ?? null);
  }

  function selectReportGrouping(groupingKind: string) {
    setReportGrouping(groupingKind);
    setOpenedGroupingKey(null);
    setOpenedGroupingLabel(null);
    setLandOnComparison(false);
  }

  function selectReportPeriod(periodCode: string) {
    setReportPeriod(periodCode);
    setLandOnComparison(false);
  }

  function openComparedGrouping(groupingKey: string, groupingLabel: string) {
    setOpenedGroupingKey(groupingKey);
    setOpenedGroupingLabel(groupingLabel);
  }

  function selectPost(postId: string, options?: SelectPostOptions) {
    if (focusedGraphMustReset(selectedPostId, postId)) {
      setFocusedGraph(null);
    }
    setSelectedPostId(postId);
    setOpenedAfterCutoff(Boolean(options?.liveAfterCutoff));
    setOpenedCutoffIso(options?.knowledgeCutoff ?? null);
    setOpenedFromReportMember(Boolean(options?.fromReportMember));
    setOpenedLeftoverPair(options?.fromLeftoverPair ?? null);
  }

  const openRequestedPost = useEffectEvent((postId: string) => {
    selectPost(postId);
    onPostOpened?.();
  });

  useEffect(() => {
    if (!postIdToOpen) return;
    openRequestedPost(postIdToOpen);
  }, [postIdToOpen]);

  function closeSelectedPost() {
    setSelectedPostId(null);
    setOpenedAfterCutoff(false);
    setOpenedCutoffIso(null);
    setOpenedFromReportMember(false);
    setOpenedLeftoverPair(null);
    const url = new URL(window.location.href);
    if (url.searchParams.has("post")) {
      url.searchParams.delete("post");
      window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
    }
  }

  function searchBoard(query: string) {
    const normalized = query.trim();
    if (!normalized) return;
    setSearchInput(normalized);
    setSearchQuery(normalized);
    setCurrentPage(1);
    closeSelectedPost();
  }

  const loadPostPage = useCallback(async (page: number, query = searchQuery, sort = sortOrder) => {
    const requestId = ++postsRequest.current;
    setLoadingPage(true);
    setError(null);
    try {
      const response = await fetchPosts(
        accessToken,
        POST_PAGE_SIZE,
        (page - 1) * POST_PAGE_SIZE,
        query,
        typeFilter.length > 0 ? typeFilter : undefined,
        visibilityFilter === "all" ? undefined : visibilityFilter,
        sort,
      );
      if (requestId !== postsRequest.current) return;
      setPosts(response.posts);
      setTotalPosts(response.total_count);
      setVocTypeFilterOptions(response.voc_type_options ?? []);
      setVisibilityFilterOptions(response.visibility_options ?? []);
      setCurrentPage(page);
    } catch (err) {
      if (requestId !== postsRequest.current) return;
      setError(String(err));
    } finally {
      if (requestId === postsRequest.current) setLoadingPage(false);
    }
  }, [accessToken, searchQuery, sortOrder, typeFilter, visibilityFilter]);

  useEffect(() => {
    void loadPostPage(1);
  }, [loadPostPage]);

  useEffect(() => {
    fetchMe(accessToken)
      .then((me) => {
        setCanRebuild(me.permission_codes.includes("post_admin"));
        setCorporateEntities(me.corporate_entities ?? []);
        setEntitiesLoadError(null);
      })
      .catch(() => {
        setCanRebuild(false);
        setCorporateEntities([]);
        setEntitiesLoadError("Reload to load the corporate entities this account may reconstruct.");
      });
  }, [accessToken]);

  useEffect(() => {
    if (!selectedPostId) {
      setFocusedGraph(null);
      return;
    }
    setFocusedGraph(null);
    let active = true;
    fetchLineageGraph(accessToken, selectedPostId)
      .then((nextGraph) => {
        if (active) setFocusedGraph(nextGraph);
      })
      .catch(() => {
        if (active) setFocusedGraph({ nodes: [], edges: [] });
      });
    return () => {
      active = false;
    };
  }, [accessToken, selectedPostId]);

  async function handleRebuild() {
    setRebuilding(true);
    setRebuildError(null);
    try {
      await rebuildLineage(accessToken);
    } catch (err) {
      setRebuildError(String(err));
    } finally {
      setRebuilding(false);
    }
  }

  const loadedPosts = posts ?? [];
  const visibilityOptions = visibilityFilterOptions.length
    ? visibilityFilterOptions
    : Array.from(new Set(loadedPosts.map((post) => post.visibility_code)))
        .sort()
        .map((code) => ({
          code,
          label: loadedPosts.find((post) => post.visibility_code === code)?.visibility_label ?? code,
        }));
  const vocTypeOptions = vocTypeFilterOptions.length
    ? vocTypeFilterOptions
    : Array.from(new Set(loadedPosts.map((post) => post.voc_type_code)))
        .sort()
        .map((code) => ({
          code,
          label: loadedPosts.find((post) => post.voc_type_code === code)?.voc_type_label ?? code,
        }));
  const filteredPosts = loadedPosts
    .filter((post) => {
      const matchesType = typeFilter.length === 0 || typeFilter.includes(post.voc_type_code);
      const matchesVisibility = visibilityFilter === "all" || post.visibility_code === visibilityFilter;
      return matchesType && matchesVisibility;
    })
    .sort((left, right) => {
      if (sortOrder === "title") {
        return left.post_title.localeCompare(right.post_title);
      }
      const direction = sortOrder === "newest" ? -1 : 1;
      return direction * left.created_at.localeCompare(right.created_at);
    });
  const hasBoardFilters = Boolean(searchInput.trim()) || Boolean(searchQuery) || typeFilter.length > 0 || visibilityFilter !== "all";
  const totalPages = Math.max(1, Math.ceil(totalPosts / POST_PAGE_SIZE));
  const pageItems: Array<number | "ellipsis"> =
    totalPages <= 7
      ? Array.from({ length: totalPages }, (_, index) => index + 1)
      : Array.from(new Set([1, 2, currentPage - 1, currentPage, currentPage + 1, totalPages - 1, totalPages]))
          .filter((page) => page >= 1 && page <= totalPages)
          .sort((left, right) => left - right)
          .flatMap((page, index, pages) => [
            ...(index > 0 && page - pages[index - 1] > 1 ? ["ellipsis" as const] : []),
            page,
          ]);

  return (
    <section className="board-surface" aria-labelledby="board-title">
      {import.meta.env.MODE === "test" && !showLabPanels ? (
        <RankingsPanel accessToken={accessToken} onSelectPost={selectPost} />
      ) : null}
      <header className="board-header">
        <div>
          <p className="post-meta">{t("Board")}</p>
          <h2 id="board-title">{t("Board")}</h2>
          <p>{t("Authorized posts in this board.")}</p>
        </div>
        {posts && !error && (
          <p className="board-result-count" aria-live="polite">
            {t("Posts shown:")} {filteredPosts.length} / {totalPosts}
          </p>
        )}
      </header>
      {error ? (
        <p className="error" role="alert">
          {error}
        </p>
      ) : !posts ? (
        <p role="status">{t("Loading posts...")}</p>
      ) : (
        <>
          <form
            className="board-controls"
            role="search"
            aria-label={t("Search and filter posts")}
            onSubmit={(event) => {
              event.preventDefault();
              setSearchQuery(searchInput.trim());
            }}
            onReset={() => {
              setSearchInput("");
              setSearchQuery("");
              setTypeFilter([]);
              setVisibilityFilter("all");
              setSortOrder("newest");
            }}
          >
            <label>
              {t("Search semantic evidence")}
              <input
                type="search"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
                placeholder={t("Search semantic evidence")}
                aria-label={t("Search semantic evidence")}
              />
            </label>
            <button type="submit">{t("Search")}</button>
            <p className="board-search-help post-meta">{t("Search includes post text and semantic evidence.")}</p>
            <fieldset className="board-voc-type-filter">
              <legend>{t("Filter by VOC type")}</legend>
              {vocTypeOptions.map((option) => (
                <label key={option.code}>
                  <input
                    type="checkbox"
                    checked={typeFilter.includes(option.code)}
                    onChange={(event) =>
                      setTypeFilter((current) =>
                        event.target.checked
                          ? [...current, option.code]
                          : current.filter((code) => code !== option.code),
                      )
                    }
                  />
                  {t(option.label)}
                </label>
              ))}
            </fieldset>
            <label>
              {t("Filter by visibility")}
              <select
                value={visibilityFilter}
                onChange={(event) => setVisibilityFilter(event.target.value)}
                aria-label={t("Filter by visibility")}
              >
                <option value="all">{t("All visibility")}</option>
                {visibilityOptions.map((option) => (
                  <option key={option.code} value={option.code}>
                    {t(option.label)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              {t("Sort posts")}
              <select
                value={sortOrder}
                onChange={(event) => setSortOrder(event.target.value as BoardSortOrder)}
                aria-label={t("Sort posts")}
              >
                <option value="newest">{t("Newest first")}</option>
                <option value="oldest">{t("Oldest first")}</option>
                <option value="title">{t("Title A-Z")}</option>
              </select>
            </label>
            {hasBoardFilters && (
              <button type="reset" className="board-reset">
                {t("Reset filters")}
              </button>
            )}
          </form>
          {posts.length === 0 ? (
            <p className="board-empty" role="status">
              {hasBoardFilters
                ? t("No posts match the current filters.")
                : t("No posts visible to this account yet -- try `make seed`.")}
            </p>
          ) : filteredPosts.length === 0 ? (
            <p className="board-empty" role="status">
              {t("No posts match the current filters.")}
            </p>
          ) : (
            <ul className="post-list" aria-label={t("Board posts")}>
              {filteredPosts.map((post) => (
                <li key={post.post_id}>
                  <article className="post-card">
                    <button
                      className="post-list-item"
                      aria-label={`${t("View post:")} ${post.post_title}`}
                      onClick={() => selectPost(post.post_id)}
                    >
                      <span className="post-card-main">
                        <span className="post-title">{post.post_title}</span>
                        <span className="post-meta">{t("Post body")}</span>
                        <span
                          className="post-body-excerpt"
                          aria-label={t("Post body preview")}
                        >
                          {decodeHtmlEntities(post.post_body_excerpt || t("No post body."))}
                          {post.post_body_truncated ? " ..." : ""}
                        </span>
                        {post.publication_state_code && post.publication_state_code !== "publication_state_unknown" ? (
                          <span className="post-meta">
                            {t("Publication state")}: {t(
                              post.publication_state_code === "source_draft_marker"
                                ? "Source draft marker present"
                                : "Source deletion marker present",
                            )}
                          </span>
                        ) : null}
                        {post.source_project_code ? (
                          <span className="post-meta">
                            {t("Source project code")}: {post.source_project_code}
                          </span>
                        ) : null}
                        {post.source_project_name ? (
                          <span className="post-meta">
                            {t("Source project name")}: {post.source_project_name}
                          </span>
                        ) : null}
                        {post.project_evidence && post.project_evidence.length > 0 ? (
                          <span className="post-meta">
                            {t("Semantic project")}: {post.project_evidence.map((project) => project.project_name).join(", ")}
                          </span>
                        ) : null}
                        <span className="post-meta">
                          <time dateTime={post.created_at}>{post.created_at.slice(0, 10)}</time>
                        </span>
                      </span>
                      <span className="post-card-badges">
                        <span className="post-badge">{t(post.voc_type_label ?? post.voc_type_code)}</span>
                        <span className="post-badge">{t(post.visibility_label ?? post.visibility_code)}</span>
                        {post.source_detail_state_code ? (
                          <span className="post-badge">
                            {t("Source detail state")}: {post.source_detail_state_code}
                          </span>
                        ) : null}
                      </span>
                    </button>
                  </article>
                </li>
              ))}
            </ul>
          )}
          {totalPages > 1 && (
            <nav className="board-pagination" aria-label={t("Board pages")}>
              <button
                type="button"
                onClick={() => void loadPostPage(currentPage - 1)}
                disabled={loadingPage || currentPage === 1}
              >
                {t("Previous page")}
              </button>
              {pageItems.map((page, index) =>
                page === "ellipsis" ? (
                  <span key={`ellipsis-${index}`} aria-hidden="true">
                    ...
                  </span>
                ) : (
                  <button
                    key={page}
                    type="button"
                    aria-label={`${t("Page")} ${page}`}
                    aria-current={page === currentPage ? "page" : undefined}
                    onClick={() => void loadPostPage(page)}
                    disabled={loadingPage}
                  >
                    {page}
                  </button>
                ),
              )}
              <button
                type="button"
                onClick={() => void loadPostPage(currentPage + 1)}
                disabled={loadingPage || currentPage === totalPages}
              >
                {t("Next page")}
              </button>
            </nav>
          )}
        </>
      )}
      {(showLabPanels || canRebuild) && (
        <details className="advanced-review-tools">
          <summary>{t("Advanced review tools")}</summary>
          {canRebuild && (
            <section className="popup-section">
              <div className="lineage-home-header">
                <h3>{t("Lineage maintenance")}</h3>
                <button onClick={handleRebuild} disabled={rebuilding}>
                  {rebuilding ? t("Rebuilding...") : t("Rebuild lineage")}
                </button>
              </div>
              {rebuildError && <p className="error">{rebuildError}</p>}
            </section>
          )}
          <CalendarPanel accessToken={accessToken} onSelectPost={selectPost} />
          <RankingsPanel accessToken={accessToken} onSelectPost={selectPost} />
          <AnalysisRunsPanel
            accessToken={accessToken}
            currentReportPeriod={reportPeriod}
            onSelectPost={selectPost}
            onSelectReportPeriod={openReportFromAnalysisRun}
            corporateEntities={corporateEntities}
            entitiesLoadError={entitiesLoadError}
          />
          <ReportsPanel
            accessToken={accessToken}
            canRebuild={canRebuild}
            onSelectPost={selectPost}
            period={reportPeriod}
            onSelectPeriod={selectReportPeriod}
            grouping={reportGrouping}
            onSelectGrouping={selectReportGrouping}
            openedGroupingKey={openedGroupingKey}
            openedGroupingLabel={openedGroupingLabel}
            onOpenGrouping={openComparedGrouping}
            landOnComparison={landOnComparison}
            selectedPostId={selectedPostId}
          />
        </details>
      )}
      {selectedPostId && (
        <PostDetailPopup
          postId={selectedPostId}
          accessToken={accessToken}
          canExtract={canRebuild}
          graph={focusedGraph}
          liveBodyWarning={
            openedAfterCutoff ? analysisRunOpenedBodyWarning(openedCutoffIso) : null
          }
          knowledgeCutoff={openedAfterCutoff ? openedCutoffIso : null}
          focusEventLineage={openedFromReportMember}
          leftoverFocus={openedLeftoverPair}
          onClose={closeSelectedPost}
          onSelectPost={selectPost}
          onSearch={searchBoard}
        />
      )}
    </section>
  );
}

interface CustomerEntityTreeNode {
  entity: CustomerMasterEntity;
  children: CustomerEntityTreeNode[];
}

// Live bug (2026-08-19): Customer Master's own entity list rendered every
// corporate_entity as an independent top-level row, even though the API
// already carries parent_entity_id and the codebase already knows how to
// build a real forest from it (lineageweave/affiliate_tree.py, used for
// the post-detail popup's Affiliate tree) -- a group holding company and
// its subsidiaries showed up as an unrelated flat list with no visual
// hierarchy at all. A parent not present in this account's own visible
// entity list (a real possibility -- ABAC can authorize a child entity
// without its parent) is not dropped; that entity becomes a root here
// instead of disappearing.
function buildCustomerEntityTree(entities: CustomerMasterEntity[]): CustomerEntityTreeNode[] {
  const byId = new Map(entities.map((entity) => [entity.corporate_entity_id, entity]));
  const childrenByParent = new Map<string, CustomerMasterEntity[]>();
  const roots: CustomerMasterEntity[] = [];
  for (const entity of entities) {
    if (entity.parent_entity_id && byId.has(entity.parent_entity_id)) {
      const siblings = childrenByParent.get(entity.parent_entity_id) ?? [];
      siblings.push(entity);
      childrenByParent.set(entity.parent_entity_id, siblings);
    } else {
      roots.push(entity);
    }
  }
  const toNode = (entity: CustomerMasterEntity): CustomerEntityTreeNode => ({
    entity,
    children: (childrenByParent.get(entity.corporate_entity_id) ?? []).map(toNode),
  });
  return roots.map(toNode);
}

function CustomerEntityTreeRow({
  node,
  depth,
  expandedEntityId,
  relatedByEntity,
  relatedLoading,
  onToggle,
  onOpenPost,
}: {
  node: CustomerEntityTreeNode;
  depth: number;
  expandedEntityId: string | null;
  relatedByEntity: Record<string, RelatedNode[]>;
  relatedLoading: string | null;
  onToggle: (entityId: string) => void;
  onOpenPost: (postId: string) => void;
}) {
  const { entity, children } = node;
  const relatedPosts = (relatedByEntity[entity.corporate_entity_id] ?? []).filter(
    (related) => related.node_type_code === NODE_POST,
  );
  return (
    <li style={{ marginInlineStart: depth * 20 }}>
      <button
        type="button"
        className="customer-entity-button"
        aria-expanded={expandedEntityId === entity.corporate_entity_id}
        onClick={() => onToggle(entity.corporate_entity_id)}
      >
        <strong>{entity.entity_name}</strong>
        <span>{entity.corporate_entity_code} · {entity.entity_level_label}</span>
      </button>
      {expandedEntityId === entity.corporate_entity_id ? (
        <div className="customer-related-posts">
          {relatedLoading === entity.corporate_entity_id ? <p role="status">{t("Loading related posts...")}</p> : null}
          {relatedLoading !== entity.corporate_entity_id && relatedPosts.length === 0 ? (
            <p className="popup-placeholder">{t("No linked posts yet.")}</p>
          ) : null}
          {relatedPosts.length > 0 ? (
            <ul aria-label={`${t("Related posts")}: ${entity.entity_name}`}>
              {relatedPosts.map((related) => (
                <li key={related.node_id}>
                  <CustomerRelatedPostCard
                    postId={related.node_id}
                    postTitle={related.label ?? related.node_id}
                    postBodyExcerpt={related.post_body_excerpt}
                    postBodyTruncated={related.post_body_truncated}
                    onOpenPost={onOpenPost}
                  />
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
      {children.length > 0 ? (
        <ul className="customer-master-list customer-master-tree-children" aria-label={tf("Affiliates of {name}", { name: entity.entity_name })}>
          {children.map((child) => (
            <CustomerEntityTreeRow
              key={child.entity.corporate_entity_id}
              node={child}
              depth={depth + 1}
              expandedEntityId={expandedEntityId}
              relatedByEntity={relatedByEntity}
              relatedLoading={relatedLoading}
              onToggle={onToggle}
              onOpenPost={onOpenPost}
            />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

function CustomerRelatedPostCard({
  postId,
  postTitle,
  postBodyExcerpt,
  postBodyTruncated,
  onOpenPost,
}: {
  postId: string;
  postTitle: string;
  postBodyExcerpt?: string | null;
  postBodyTruncated?: boolean;
  onOpenPost: (postId: string) => void;
}) {
  return (
    <button
      type="button"
      className="related-post-card"
      aria-label={tf("Open related post: {label}", { label: postTitle })}
      onClick={() => onOpenPost(postId)}
    >
      <span className="related-post-content">
        <strong>{postTitle}</strong>
        <span className="post-body-excerpt" aria-label={t("Post body preview")}>
          {postBodyExcerpt || t("No post body.")}
          {postBodyTruncated ? " ..." : ""}
        </span>
      </span>
      <span>{t("Open record")}</span>
    </button>
  );
}

function CustomerMasterPanel({
  accessToken,
}: {
  accessToken: string;
}) {
  const [master, setMaster] = useState<CustomerMasterResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedEntityId, setExpandedEntityId] = useState<string | null>(null);
  const [relatedByEntity, setRelatedByEntity] = useState<Record<string, RelatedNode[]>>({});
  const [relatedLoading, setRelatedLoading] = useState<string | null>(null);
  // Opening a customer's related post stays IN this panel (the Board
  // hand-off was the reported bug: clicking a customer's post jumped the
  // whole workspace to the Board instead of showing the post here).
  const [selectedPostId, setSelectedPostId] = useState<string | null>(null);
  const [selectedPostGraph, setSelectedPostGraph] = useState<LineageGraph | null>(null);
  const [resolvingHint, setResolvingHint] = useState<string | null>(null);
  const [resolveError, setResolveError] = useState<string | null>(null);
  // Fetched independently, same pattern as PostList's own canRebuild --
  // CustomerMasterPanel is a sibling of PostList under App, not a child,
  // so it cannot read PostList's local post_admin check.
  const [canResolveHints, setCanResolveHints] = useState(false);

  useEffect(() => {
    let active = true;
    fetchMe(accessToken)
      .then((member) => {
        if (active) setCanResolveHints(member.permission_codes.includes("post_admin"));
      })
      .catch(() => {
        if (active) setCanResolveHints(false);
      });
    return () => {
      active = false;
    };
  }, [accessToken]);

  const loadMaster = useCallback(() => {
    setError(null);
    return fetchCustomerMaster(accessToken)
      .then(setMaster)
      .catch(() => setError(t("Customer master could not be loaded.")));
  }, [accessToken]);

  useEffect(() => {
    setMaster(null);
    void loadMaster();
  }, [loadMaster]);

  useEffect(() => {
    if (!selectedPostId) {
      setSelectedPostGraph(null);
      return;
    }
    let active = true;
    fetchLineageGraph(accessToken, selectedPostId)
      .then((nextGraph) => {
        if (active) setSelectedPostGraph(nextGraph);
      })
      .catch(() => {
        if (active) setSelectedPostGraph({ nodes: [], edges: [] });
      });
    return () => {
      active = false;
    };
  }, [accessToken, selectedPostId]);

  function openPost(postId: string) {
    setSelectedPostGraph(null);
    setSelectedPostId(postId);
  }

  async function handleResolveHint(hintCode: string) {
    setResolvingHint(hintCode);
    setResolveError(null);
    try {
      await resolveCustomerHint(accessToken, hintCode);
      await loadMaster();
    } catch {
      setResolveError(t("This hint could not be resolved to a corroborated organization name."));
    } finally {
      setResolvingHint(null);
    }
  }

  async function toggleEntity(entityId: string) {
    if (expandedEntityId === entityId) {
      setExpandedEntityId(null);
      return;
    }
    setExpandedEntityId(entityId);
    if (relatedByEntity[entityId]) return;
    setRelatedLoading(entityId);
    try {
      const response = await fetchRelatedEntity(accessToken, entityId);
      setRelatedByEntity((previous) => ({ ...previous, [entityId]: response.related }));
    } catch {
      setRelatedByEntity((previous) => ({ ...previous, [entityId]: [] }));
    } finally {
      setRelatedLoading(null);
    }
  }

  return (
    <section className="workspace-destination" aria-labelledby="customer-master-heading">
      <p className="section-eyebrow">{t("Authorized customer scope")}</p>
      <h2 id="customer-master-heading">{t("Customer master")}</h2>
      <p className="workspace-destination-intro">{t("Customer entities available to this account.")}</p>
      {error ? <p className="error">{error}</p> : null}
      {master === null && !error ? <p role="status">{t("Loading customer master...")}</p> : null}
      {master?.corporate_entities.length === 0 ? (
        <p className="popup-placeholder">{t("No customer entities are connected to this account.")}</p>
      ) : null}
      {master && master.corporate_entities.length > 0 ? (
        <ul className="customer-master-list customer-master-tree" aria-label={t("Customer entities available to this account.")}>
          {buildCustomerEntityTree(master.corporate_entities).map((node) => (
            <CustomerEntityTreeRow
              key={node.entity.corporate_entity_id}
              node={node}
              depth={0}
              expandedEntityId={expandedEntityId}
              relatedByEntity={relatedByEntity}
              relatedLoading={relatedLoading}
              onToggle={toggleEntity}
              onOpenPost={openPost}
            />
          ))}
        </ul>
      ) : null}
      {master && (master.relationship_network ?? []).length > 0 ? (
        <section className="customer-keymen" aria-labelledby="relationship-network-heading">
          <h3 id="relationship-network-heading">{t("Relationship network")}</h3>
          <p className="workspace-destination-intro">
            {t("A counterparty can hold more than one role over time -- a customer in one post can be a competitor, supplier, or partner in another. Every role observed for a name is listed, not just the most frequent.")}
          </p>
          <ul className="customer-master-list">
            {(master.relationship_network ?? []).map((entry) => (
              <li key={entry.counterparty_entity_name}>
                <strong>{entry.counterparty_entity_name}</strong>
                {entry.multi_role ? (
                  <span className="post-badge">{t("Multiple roles observed")}</span>
                ) : null}
                <span>
                  {entry.relationships
                    .map((role) => `${role.relationship_label} (${role.post_count})`)
                    .join(", ")}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {master && master.source_customer_hints.length > 0 ? (
        <section className="customer-keymen" aria-labelledby="observed-customer-evidence-heading">
          <h3 id="observed-customer-evidence-heading">{t("Observed customer evidence")}</h3>
          <p className="workspace-destination-intro">
            {t("Source identifiers are hints only; ontology and semantic evidence must resolve them before binding a customer.")}
          </p>
          {master.source_customer_hints.length > HINT_RENDER_LIMIT && (
            <p className="post-meta">
              {tf("Showing the first {shown} of {total} observed customer identifiers, ranked by post count.", {
                shown: HINT_RENDER_LIMIT,
                total: master.source_customer_hints.length,
              })}
            </p>
          )}
          {resolveError ? <p className="error">{resolveError}</p> : null}
          <ul className="customer-master-list">
            {master.source_customer_hints.slice(0, HINT_RENDER_LIMIT).map((hint) => (
              <li key={`${hint.customer_code ?? "name"}:${hint.customer_name ?? "unknown"}`}>
                <strong>{hint.customer_name ?? hint.customer_code ?? t("Unresolved source identifier")}</strong>
                {hint.customer_name && hint.customer_code ? <span>{hint.customer_code}</span> : null}
                <span>{t("Unresolved source identifier")}</span>
                <span>{t(hint.hint_trust === "low" ? "Weak source hint" : "Source hint")}</span>
                <span>{hint.post_count} {t("posts")}</span>
                {canResolveHints && hint.customer_code ? (
                  <button
                    onClick={() => void handleResolveHint(hint.customer_code as string)}
                    disabled={resolvingHint === hint.customer_code}
                  >
                    {resolvingHint === hint.customer_code ? t("Resolving...") : t("Resolve")}
                  </button>
                ) : null}
                {hint.related_posts.length > 0 ? (
                  <details className="hint-disclosure">
                    <summary>{t("Related posts")} ({hint.related_posts.length})</summary>
                    <ul aria-label={`${t("Related posts")}: ${hint.customer_name ?? hint.customer_code ?? t("Unresolved source identifier")}`}>
                      {hint.related_posts.map((post) => (
                        <li key={post.post_id}>
                          <CustomerRelatedPostCard
                            postId={post.post_id}
                            postTitle={post.post_title}
                            postBodyExcerpt={post.post_body_excerpt}
                            postBodyTruncated={post.post_body_truncated}
                            onOpenPost={openPost}
                          />
                        </li>
                      ))}
                    </ul>
                  </details>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {master && master.source_author_hints.length > 0 ? (
        <section className="customer-keymen" aria-labelledby="source-author-evidence-heading">
          <h3 id="source-author-evidence-heading">{t("Source author evidence")}</h3>
          {master.source_author_hints.length > HINT_RENDER_LIMIT && (
            <p className="post-meta">
              {tf("Showing the first {shown} of {total} observed source authors, ranked by post count.", {
                shown: HINT_RENDER_LIMIT,
                total: master.source_author_hints.length,
              })}
            </p>
          )}
          <ul className="customer-master-list">
            {master.source_author_hints.slice(0, HINT_RENDER_LIMIT).map((hint) => (
              <li key={`${hint.author_code}:${hint.author_account_id}`}>
                <strong>{hint.author_name ?? hint.author_code}</strong>
                <details className="hint-disclosure">
                  <summary>{hint.author_code} · {t("Hint only")}</summary>
                  <span>{t("Authorization context")}: {hint.account_display_name}</span>
                  {hint.account_affiliations.length > 0 ? (
                    <span>{hint.account_affiliations.map((affiliation) => affiliation.entity_name).join(", ")}</span>
                  ) : null}
                  {hint.keyman_hints.length > 0 ? (
                    <span>
                      {t("Our-side Keymen hints")}: {hint.keyman_hints.map((person) => (
                        `${person.person_name}${person.last_known_job_title ? ` (${person.last_known_job_title})` : ""}`
                      )).join(", ")}
                    </span>
                  ) : null}
                </details>
                <span>{hint.post_count} {t("posts")}</span>
                {hint.related_posts.length > 0 ? (
                  <details className="hint-disclosure">
                    <summary>{t("Related posts")} ({hint.related_posts.length})</summary>
                    <ul className="related-post-list">
                      {hint.related_posts.map((post) => (
                        <li key={post.post_id}>
                          <CustomerRelatedPostCard
                            postId={post.post_id}
                            postTitle={post.post_title}
                            postBodyExcerpt={post.post_body_excerpt}
                            postBodyTruncated={post.post_body_truncated}
                            onOpenPost={openPost}
                          />
                        </li>
                      ))}
                    </ul>
                  </details>
                ) : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {master && master.keymen.length > 0 ? (
        <section className="customer-keymen" aria-labelledby="customer-keymen-heading">
          <h3 id="customer-keymen-heading">{t("Keymen")}</h3>
          <ul className="customer-master-list">
            {master.keymen.map((person) => (
              <li key={person.person_id}>
                <strong>{person.person_name}</strong>
                <span>{person.last_known_job_title ?? person.person_side_label}</span>
                <span>{person.affiliations.map((affiliation) => affiliation.entity_name ?? affiliation.organization_name).join(", ")}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      {selectedPostId && (
        <PostDetailPopup
          postId={selectedPostId}
          accessToken={accessToken}
          canExtract={canResolveHints}
          graph={selectedPostGraph}
          onClose={() => setSelectedPostId(null)}
          onSelectPost={openPost}
        />
      )}
    </section>
  );
}

function AskAgentPanel({
  accessToken,
  onOpenPost,
}: {
  accessToken: string;
  onOpenPost: (postId: string) => void;
}) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<AskAgentResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [asking, setAsking] = useState(false);
  const [evidenceLayerPostId, setEvidenceLayerPostId] = useState<string | null>(null);

  async function handleAsk() {
    const normalized = question.trim();
    if (!normalized) return;
    setAsking(true);
    setError(null);
    try {
      setAnswer(await askAgent(accessToken, normalized));
    } catch (err) {
      setAnswer(null);
      setError(orchestratorUnavailableMessage(err, t("Ask Agent")));
    } finally {
      setAsking(false);
    }
  }

  return (
    <section className="workspace-destination" aria-labelledby="ask-agent-heading">
      <p className="section-eyebrow">{t("Evidence-grounded questions")}</p>
      <h2 id="ask-agent-heading">{t("Ask Agent")}</h2>
      <p className="workspace-destination-intro">{t("Questions use authorized posts and their evidence.")}</p>
      {error ? <p className="error">{error}</p> : null}
      <label className="ask-agent-source">
        <span>{t("Ask a question")}</span>
        <textarea
          aria-label={t("Ask a question")}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          rows={4}
        />
      </label>
      <button className="keyman-select" onClick={() => void handleAsk()} disabled={asking || !question.trim()}>
        {asking ? t("Asking...") : t("Ask")}
      </button>
      {answer && (
        <section className="popup-section" aria-label={t("Answer")}>
          <h3>{t("Answer")}</h3>
          {answer.answer_text ? <p>{answer.answer_text}</p> : null}
          {answer.next_action ? <p className="post-meta">{t(answer.next_action)}</p> : null}
          {answer.delivery ? (
            <aside className="ask-delivery" aria-label={t("Report · alert · MCP")}>
              <h4>{t("Report · alert · MCP")}</h4>
              <p>
                {tf("{count} evidence documents are linked to this report.", {
                  count: answer.delivery.report.source_documents.length,
                })}
                {answer.delivery.alert.eligible
                  ? ` ${t("You can subscribe to evidence-change alerts.")}`
                  : ` ${t("Connect evidence to enable change-alert subscriptions.")}`}
              </p>
              <code>{answer.delivery.report.source_documents[0]?.resource_uri ?? "lineageweave://posts"}</code>
            </aside>
          ) : null}
          {answer.cited_posts && answer.cited_posts.length > 0 && (
            <>
              <h4>{t("Cited posts")}</h4>
              <ul className="related-post-list">
                {answer.cited_posts.map((post) => (
                  <li key={post.post_id}>
                    <button className="post-list-item" onClick={() => onOpenPost(post.post_id)}>
                      <strong>{post.post_title}</strong>
                    </button>
                    <button
                      type="button"
                      className="citation-chip"
                      onClick={() => setEvidenceLayerPostId(post.post_id)}
                    >
                      {t("View evidence")}
                    </button>
                    {answer.cited_post_evidence?.find((item) => item.post_id === post.post_id)?.facts.length ? (
                      <ul className="post-evidence-list" aria-label={t("Evidence facts")}>
                        {answer.cited_post_evidence
                          .find((item) => item.post_id === post.post_id)
                          ?.facts.map((fact, index) => (
                            <li key={`${fact.kind}:${fact.text}:${index}`}>
                              <span>{chatEvidenceKindLabel(fact.kind)}</span>
                              <span>{fact.text}</span>
                            </li>
                          ))}
                      </ul>
                    ) : null}
                    {answer.cited_post_images
                      ?.filter((image) => image.post_id === post.post_id)
                      .map((image) => (
                        <p
                          key={`${image.post_id}:${image.unit_index}`}
                          className="post-meta ask-agent-image-citation"
                        >
                          {t("Image evidence")}: {image.caption?.trim() ? image.caption : t("Untitled image")}
                          {image.extracted_text ? ` — ${image.extracted_text}` : ""}
                          {image.tags.length ? ` — ${t("Image tags")}: ${image.tags.join(", ")}` : ""}
                        </p>
                      ))}
                  </li>
                ))}
              </ul>
            </>
          )}
          {answer.lineage_graph && answer.lineage_graph.nodes.length > 0 ? (
            <LineageDag graph={answer.lineage_graph} onSelectPost={onOpenPost} />
          ) : null}
        </section>
      )}
      {evidenceLayerPostId && answer ? (
        <AskEvidenceLayerPopup
          postId={evidenceLayerPostId}
          postTitle={
            answer.cited_posts?.find((post) => post.post_id === evidenceLayerPostId)?.post_title ??
            evidenceLayerPostId
          }
          facts={
            answer.cited_post_evidence?.find((item) => item.post_id === evidenceLayerPostId)?.facts ?? []
          }
          images={
            answer.cited_post_images?.filter((image) => image.post_id === evidenceLayerPostId) ?? []
          }
          onClose={() => setEvidenceLayerPostId(null)}
          onOpenPost={onOpenPost}
        />
      ) : null}
    </section>
  );
}

export default function App({ showLabPanels = false }: { showLabPanels?: boolean } = {}) {
  useLocale();
  const [brandName, setBrandName] = useState("LineageWeave");
  const auth = useAuth();
  const [destination, setDestination] = useState<WorkspaceDestination>(() =>
    initialWorkspaceDestination(
      typeof window === "undefined" ? "" : window.location.search,
      import.meta.env.MODE === "test",
    ),
  );
  const [postToOpen, setPostToOpen] = useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    return new URLSearchParams(window.location.search).get("post");
  });
  // Test-only compatibility for legacy analysis-panel coverage; this prop
  // never forces the panels open outside Vitest. In a real build the
  // advanced-review section (ADR 0037) is gated on PostList's own
  // post_admin check (`canRebuild`), not on this caller-supplied prop.
  const testOnlyLabPanels = import.meta.env.MODE === "test" && showLabPanels;
  const accessToken = auth.user?.access_token;

  useEffect(() => {
    if (accessToken) {
      fetchTenantConfig(accessToken).then((config) => {
        if (config.brandName) setBrandName(config.brandName);
      }).catch(console.error);
    }
  }, [accessToken]);

  useEffect(() => {
    if (!accessToken) return;
    const postId = new URLSearchParams(window.location.search).get("post");
    if (postId) setPostToOpen(postId);
  }, [accessToken]);

  useEffect(() => {
    if (!accessToken) return;
    let active = true;
    fetchMe(accessToken)
      .then((member) => {
        if (active && isSupportedLocale(member.preferred_locale)) setLocale(member.preferred_locale);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [accessToken]);

  if (auth.isLoading) {
    return <p role="status">{t("Loading authentication state...")}</p>;
  }

  if (auth.error) {
    return <p className="error">{t(auth.error.message)}</p>;
  }

  if (!auth.isAuthenticated) {
    return (
      <div className="app-shell">
        <main className="login-screen">
          <div className="login-card">
            <div className="login-header">
              <h1>{brandName}</h1>
              <p className="login-subtitle">Marketing & Operational Lineage Intelligence</p>
            </div>
            <div className="login-controls">
              <button className="btn-primary" onClick={() => {
                const returnUrl = returnUrlFromLocation();
                rememberOidcReturnUrl(returnUrl);
                void auth.signinRedirect({ state: { returnUrl } });
              }}>
                {t("Log in")}
              </button>
            </div>
            <div className="login-help">
              <small>Enterprise SSO Authentication</small>
            </div>
          </div>
      </main>
        <footer className="app-footer" role="contentinfo">
          <div className="app-footer-title">
            <span className="app-footer-logo">{brandName}</span>
          </div>
          <div className="app-footer-copyright">
            <p>Copyright &copy; {new Date().getFullYear()} by {brandName}. All rights reserved.</p>
          </div>
        </footer>
      </div>
    );
  }

  if (!accessToken) {
    return <p className="error">{t("Authenticated, but no access token was returned.")}</p>;
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-logo">
          <h1 className="app-header-title">{brandName}</h1>
        </div>
        <div className="app-header-top-menu">
          <span className="app-user-profile">{auth.user?.profile.preferred_username}</span>
          <button className="btn-secondary" onClick={() => auth.signoutRedirect()}>{t("Log out")}</button>
        </div>
      </header>
      <WorkspaceNav
        destination={destination}
        onChange={setDestination}
        tools={<LanguageSwitcher accessToken={accessToken} />}
      />
      <main>
        {destination === "dashboard" ? (
          <OperationsDashboard
            accessToken={accessToken}
            onOpenPost={(postId) => {
              setPostToOpen(postId);
              setDestination("board");
            }}
          />
        ) : null}
        {destination === "board" ? (
          <PostList
            accessToken={accessToken}
            showLabPanels={testOnlyLabPanels}
            postIdToOpen={postToOpen}
            onPostOpened={() => setPostToOpen(null)}
          />
        ) : null}
        {destination === "customers" ? (
          <CustomerMasterPanel accessToken={accessToken} />
        ) : null}
        {destination === "calendar" ? (
          <section className="workspace-destination" aria-labelledby="calendar-heading">
            <CalendarPanel
              accessToken={accessToken}
              headingId="calendar-heading"
              heading="달력"
              onSelectPost={(postId) => {
                setPostToOpen(postId);
                setDestination("board");
              }}
            />
          </section>
        ) : null}
        {destination === "ask" ? (
          <AskAgentPanel
            accessToken={accessToken}
            onOpenPost={(postId) => {
              setPostToOpen(postId);
              setDestination("board");
            }}
          />
        ) : null}
        {destination === "admin" && accessToken ? <AdminPanel currentBrandName={brandName} onBrandNameChange={setBrandName} accessToken={accessToken} /> : null}
      </main>
      <footer className="app-footer" role="contentinfo">
        <div className="app-footer-title">
          <span className="app-footer-logo">{brandName}</span>
        </div>
        <div className="app-footer-copyright">
          <p>Copyright &copy; {new Date().getFullYear()} by {brandName}. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
