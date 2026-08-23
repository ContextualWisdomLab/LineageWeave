import { AdminPanel, type AdminBoardTool } from "./components/AdminPanel";

import { useCallback, useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { useAuth } from "react-oidc-context";
import {
  askPostChat,
  askAgent,
  fetchAskConversation,
  fetchAskConversations,
  fetchPostChatConversation,
  fetchPostChatConversations,
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
  fetchPostKnowledgeGraph,
  fetchPostLineage,
  fetchPostFiveW1H,
  fetchPostSummary,
  fetchPostTickets,
  fetchPostVocEvidence,
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
  type AccountAffiliation,
  type AskAgentResponse,
  type AskConversationCursor,
  type AskConversationSummary,
  type CurrentUser,
  type AffiliateNode,
  type AnalysisRun,
  type CalendarResponse,
  type ChatAnswer,
  type ChatExchange,
  type CorporateEntityRef,
  type CustomerMasterEntity,
  type CustomerMasterResponse,
  type CustomerMasterScopeFacet,
  type Counterparty,
  type EvaluationResponse,
  type IssueTicket,
  type LineageGraph,
  type KnowledgeGraph,
  type Keyman,
  type SourceAuthorContext,
  type SourceCustomerHint,
  type PostAiSummary,
  type PostFiveW1H,
  type PostKeyEvent,
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
  type PostRoleResponsibility,
  type PostSemanticRelationship,
  type RelatedNode,
  type RelatedNodeType,
  type TenantConfig,
  type VocEvidence,
  fetchTenantConfig,
} from "./api";
import { CitationChip } from "./components/CitationChip";
import { CutoffKnownBody } from "./components/CutoffKnownBody";
import { GlobalSearch } from "./components/GlobalSearch";
import { LineageEntityPicker } from "./components/LineageEntityPicker";
import { PopupCloseButton } from "./components/PopupCloseButton";
import { RoleEvidence } from "./components/RoleEvidence";
import { LeftoverPairButton } from "./components/LeftoverPairButton";
import { AnalysisRunNextAction } from "./components/AnalysisRunNextAction";
import { ExceptionAlert, SummaryStatus } from "./components/SummaryStatus";
import {
  analysisRunCanRequestTeppRetry,
  analysisRunCaption,
  analysisRunCorpusHint,
  analysisRunEmptyPostsHint,
  analysisRunNextAction,
  analysisRunReportGrouping,
  analysisRunReportGroupingKey,
  analysisRunReportPeriod,
} from "./analysisRunGuidance";
import {
  analysisEvidenceDiagnosis,
  gluedRoleRelationshipNextAction,
} from "./analysisEvidenceDiagnosis";
import { leftoverCriterionLabel, postQualityCriterionElementId } from "./leftoverPairGuidance";
import { productExceptionCopy } from "./productExceptionCopy";
import { SourceResearchPanel } from "./components/SourceResearchPanel";
import { isGenericTeamActor } from "./components/roleEvidenceUtils";
import { WorkspaceNav, type WorkspaceDestination } from "./components/WorkspaceNav";
import { MenuIcon, CloseIcon, SendIcon } from "./components/icons";
import { LineageDag } from "./LineageDag";
import { KnowledgeGraphView } from "./KnowledgeGraph";
import { PostBody } from "./PostBody";
import { decodeHtmlEntities } from "./postBodyDisplay";
import { FiveW1H } from "./components/FiveW1H";
import { subgraphForPost } from "./lineageLayout";
import {
  SOURCE_LINEAGE_FIELDS,
  sourceLineageContextLabel,
  sourceLineageFieldIsPresent,
  sourceLineageFieldLabel,
} from "./sourceLineageHints";
import {
  isSupportedLocale,
  LOCALE_LABELS,
  SUPPORTED_LOCALES,
  setLocale,
  t,
  tf,
  useLocale,
} from "./i18n";
import { rememberOidcReturnUrl, returnUrlFromLocation } from "./oidcReturnUrl";
import "./App.css";

function orchestratorUnavailableMessage(err: unknown, action: string): string {
  return productExceptionCopy(err, action).title;
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

function AuthorizedScope({ affiliations }: { affiliations?: AccountAffiliation[] }) {
  const scopeValues = Array.from(
    new Set(
      (affiliations ?? [])
        .map((affiliation) => {
          const corporateCode = affiliation.corporate_entity_code.trim();
          if (!corporateCode) return null;
          return affiliation.process_unit_code?.trim()
            ? `${corporateCode} / ${affiliation.process_unit_code.trim()}`
            : corporateCode;
        })
        .filter((value): value is string => Boolean(value)),
    ),
  );
  if (scopeValues.length === 0) return null;

  const visibleScopeValues = scopeValues.slice(0, 3);
  const hiddenScopeCount = scopeValues.length - visibleScopeValues.length;
  const fullScopeLabel = scopeValues.join(", ");

  return (
    <details className="app-account-scope" aria-label={t("Authorized scope")}>
      <summary title={fullScopeLabel}>
        <span className="visually-hidden">{t("Authorized scope")}: </span>
        <span className="app-account-scope-summary">
          {visibleScopeValues.join(", ")}
        </span>
        {hiddenScopeCount > 0 ? (
          <span className="app-account-scope-more">+{hiddenScopeCount}</span>
        ) : null}
      </summary>
      <div className="app-account-scope-panel">
        <p className="app-account-scope-heading">{t("Authorized scope")}</p>
        <ul>
          {scopeValues.map((scopeValue) => (
            <li key={scopeValue}>{scopeValue}</li>
          ))}
        </ul>
      </div>
    </details>
  );
}

function SiteMapUtility({
  destination,
  onChange,
  showAdmin,
  open,
  onToggle,
}: {
  destination: WorkspaceDestination;
  onChange: (destination: WorkspaceDestination) => void;
  showAdmin: boolean;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="site-map-utility">
      <button
        type="button"
        className="btn-secondary"
        aria-expanded={open}
        aria-controls="site-map-menu"
        aria-haspopup="true"
        onClick={onToggle}
      >
        {t("Site map")}
      </button>
      {open ? (
        <div id="site-map-menu" className="site-map-menu" role="region" aria-label={t("Site map")}>
          <WorkspaceNav destination={destination} onChange={onChange} showAdmin={showAdmin} id="site-map-navigation" />
        </div>
      ) : null}
    </div>
  );
}

function searchUnavailableMessage(err: unknown): string {
  if (err instanceof BackendError && err.status === 503) {
    return t("Verification unavailable (search is not configured).");
  }
  return productExceptionCopy(err, t("Verification")).title;
}

function criterionShortLabel(itemCode: string): string {
  return leftoverCriterionLabel(itemCode);
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
  const [evidenceRetry, setEvidenceRetry] = useState(0);

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
  }, [postId, accessToken, evidenceRetry]);

  return (
    <div className="evidence-panel" role="complementary" aria-label={t("Evidence")}>
      {onClose ? <PopupCloseButton onClose={onClose} label={t("Close evidence panel")} /> : null}
      <h3>{t("Evidence")}</h3>
      {!post && !postError && <p>{t("Loading source post...")}</p>}
      {postError && (
        <ExceptionAlert
          title={t("Source evidence is unavailable. Continue with the saved answer.")}
          description={t("Retry opening this source, or keep reading the saved answer.")}
          retryLabel={t("Retry evidence")}
          onRetry={() => setEvidenceRetry((value) => value + 1)}
        />
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

export function ChatPanel({
  postId,
  accessToken,
  nameFirstAsk,
}: {
  postId: string;
  accessToken: string;
  nameFirstAsk?: boolean;
}) {
  const [question, setQuestion] = useState("");
  const [seededExchanges, setSeededExchanges] = useState<ChatExchange[]>([]);
  const [conversationExchanges, setConversationExchanges] = useState<ChatExchange[]>([]);
  const [conversations, setConversations] = useState<AskConversationSummary[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [historySelected, setHistorySelected] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [answer, setAnswer] = useState<ChatAnswer | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [evidencePostId, setEvidencePostId] = useState<string | null>(null);
  const [seededOnly, setSeededOnly] = useState(false);
  const historyRequestIdRef = useRef(0);

  const exchanges = historySelected ? conversationExchanges : seededExchanges;
  const suggestionExchanges = seededExchanges;

  useEffect(() => {
    const requestId = ++historyRequestIdRef.current;
    setQuestion("");
    setSeededExchanges([]);
    setConversationExchanges([]);
    setConversations([]);
    setConversationId(null);
    setHistorySelected(false);
    setHistoryError(null);
    setHistoryLoading(true);
    setAnswer(null);
    setError(null);
    setSeededOnly(false);
    setEvidencePostId(null);
    fetchPostChat(accessToken, postId)
      .then((history) => {
        if (requestId !== historyRequestIdRef.current) return;
        setSeededExchanges(history.exchanges);
      })
      .catch(() => {
        if (requestId !== historyRequestIdRef.current) return;
        setSeededExchanges([]);
      });
    fetchPostChatConversations(accessToken, postId)
      .then((page) => {
        if (requestId !== historyRequestIdRef.current) return;
        setConversations(page.conversations);
      })
      .catch(() => {
        if (requestId !== historyRequestIdRef.current) return;
        setHistoryError(t("Conversation history could not be loaded."));
      })
      .finally(() => {
        if (requestId === historyRequestIdRef.current) setHistoryLoading(false);
      });
  }, [postId, accessToken]);

  async function selectConversation(nextConversationId: string) {
    if (loading) return;
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      const conversation = await fetchPostChatConversation(accessToken, postId, nextConversationId);
      setConversationId(conversation.conversation_id);
      setConversationExchanges(
        conversation.exchanges.map((exchange) => ({
          question_text: exchange.question_text,
          answer_text: exchange.answer_text,
          cited_post_ids: exchange.cited_post_ids,
          cited_posts: exchange.cited_posts,
        })),
      );
      setHistorySelected(true);
      setAnswer(null);
      setError(null);
      setEvidencePostId(null);
    } catch {
      setHistoryError(t("Conversation history could not be loaded."));
    } finally {
      setHistoryLoading(false);
    }
  }

  function startNewConversation() {
    if (loading) return;
    setConversationId(null);
    setHistorySelected(false);
    setConversationExchanges([]);
    setQuestion("");
    setAnswer(null);
    setError(null);
    setEvidencePostId(null);
    setHistoryError(null);
  }

  async function handleAsk(asked = question) {
    if (!asked.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await askPostChat(accessToken, postId, asked, conversationId);
      const next: ChatExchange = {
        question_text: asked.trim(),
        answer_text: result.answer_text,
        cited_post_ids: result.cited_post_ids,
        cited_posts: result.cited_posts,
      };
      const appendToSelected = historySelected;
      setAnswer(result);
      setQuestion("");
      if (result.conversation_id) {
        setConversationId(result.conversation_id);
        setConversations((current) => [
          {
            conversation_id: result.conversation_id!,
            title:
              current.find((item) => item.conversation_id === result.conversation_id)?.title ??
              asked.trim().slice(0, 80),
            updated_at: new Date().toISOString(),
            turn_count:
              (current.find((item) => item.conversation_id === result.conversation_id)?.turn_count ?? 0) + 1,
          },
          ...current.filter((item) => item.conversation_id !== result.conversation_id),
        ]);
      }
      setConversationExchanges((prev) => [
        ...(appendToSelected ? prev : []).filter((row) => row.question_text !== next.question_text),
        next,
      ]);
      setHistorySelected(true);
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
      <div className="chat-layout">
        <aside className="ask-agent-history chat-history" aria-label={t("Conversation history")}>
          <div className="ask-agent-history-header">
            <p>{t("Switch between saved questions and source links.")}</p>
            <button
              type="button"
              className="ask-agent-new"
              onClick={startNewConversation}
              disabled={loading || historyLoading}
            >
              {t("New conversation")}
            </button>
          </div>
          {historyLoading && conversations.length === 0 ? (
            <p className="ask-agent-history-loading">{t("Loading conversation history...")}</p>
          ) : historyError && conversations.length === 0 ? (
            <ExceptionAlert
              title={historyError}
              description={t("Retry loading this conversation, or continue with saved evidence.")}
            />
          ) : conversations.length > 0 ? (
            <ul className="ask-agent-history-list">
              {conversations.map((conversation) => (
                <li key={conversation.conversation_id}>
                  <button
                    type="button"
                    className="ask-agent-history-item"
                    aria-current={
                      historySelected && conversation.conversation_id === conversationId
                        ? "page"
                        : undefined
                    }
                    onClick={() => void selectConversation(conversation.conversation_id)}
                    disabled={historyLoading || loading}
                  >
                    <strong>{conversation.title}</strong>
                    <span>
                      {conversation.turn_count} {t("questions")}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <div className="ask-agent-history-empty">
              <strong>{t("No saved conversations yet.")}</strong>
              <span>{t("Ask a question to save your first conversation.")}</span>
            </div>
          )}
        </aside>
        <div className="chat-main">
          {!seededOnly && (
            <div className="chat-input-row">
              <input
                type="text"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={(event) => event.key === "Enter" && handleAsk()}
                placeholder={t("What happened between these events?")}
                aria-label={t("What happened between these events?")}
              />
              <button onClick={() => handleAsk()} disabled={loading || !question.trim()}>
                <SendIcon />
                {loading ? t("Asking...") : t("Ask")}
              </button>
            </div>
          )}
          {seededOnly && suggestionExchanges.length > 0 && (
            <p className="popup-placeholder">
              {t("Interactive questions are unavailable right now; saved evidence remains available.")}
            </p>
          )}
          {suggestionExchanges.length > 0 && (
            <div className="chat-suggestions">
              {suggestionExchanges.map((exchange) => (
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
          {error && <ExceptionAlert title={error} />}
          {historyError && conversations.length > 0 ? (
            <ExceptionAlert
              title={historyError}
              description={t("Retry loading this conversation, or continue with saved evidence.")}
            />
          ) : null}
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
        </div>
      </div>
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

// ADR 0143: distinguish "reconstruct compared this post against real
// candidates and found no relation" from "there was nothing to compare it
// against" -- both used to render as one flat "No linked posts yet."
function lineageIsolationMessage(
  isolationReason: LineageGraph["isolation_reason"],
): string {
  switch (isolationReason) {
    case "no_relation_found":
      return t("Compared against other posts in its group; none were found related.");
    case "no_comparison_group":
      return t("No other posts share this record's group yet, so nothing was available to compare it against.");
    default:
      return t("No linked posts yet.");
  }
}

function EventLineageSection({
  lineage,
  lineageUnavailable = false,
  graph,
  postId,
  onSelectPost,
  currentNextAction,
}: {
  lineage: PostLineage | null;
  lineageUnavailable?: boolean;
  graph: LineageGraph | null;
  postId: string;
  onSelectPost: (postId: string) => void;
  currentNextAction?: string | null;
}) {
  if (lineageUnavailable) return null;
  if (!lineage) return <p>{t("Loading lineage...")}</p>;
  if (!graph) return <p>{t("Loading lineage...")}</p>;
  const scoped = subgraphForPost(graph, postId);
  const hasLinks = lineage.direct.length > 0 || lineage.indirect.length > 0;
  if (scoped.nodes.length === 0) {
    return (
      <p className="lineage-empty">
        {hasLinks
          ? t("The linked records are listed above. The graph is not available for this view.")
          : lineageIsolationMessage(graph.isolation_reason)}
      </p>
    );
  }
  return (
    <>
      {scoped.nodes.length > 0 && (
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
  return productExceptionCopy(err, t("Summary")).title;
}

function RelatedPostsSection({
  lineage,
  error,
  onSelectPost,
}: {
  lineage: PostLineage | null;
  error?: string | null;
  onSelectPost: (postId: string) => void;
}) {
  if (error) {
    return (
      <section className="popup-section related-posts-section" aria-labelledby="related-posts-heading">
        <h3 id="related-posts-heading">{t("Related posts")}</h3>
        <ExceptionAlert title={error} />
      </section>
    );
  }
  if (!lineage) {
    return (
      <section className="popup-section related-posts-section" aria-labelledby="related-posts-heading">
        <div className="related-posts-header">
          <div>
            <p className="section-eyebrow">{t("Evidence trail")}</p>
            <h3 id="related-posts-heading">{t("Related posts")}</h3>
          </div>
        </div>
        <p>{t("Loading related posts...")}</p>
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
                    <span className="related-post-content">
                      <strong>{post.post_title}</strong>
                      <span className="post-body-excerpt" aria-label={t("Post body preview")}>
                        {post.post_body_excerpt || t("No post body.")}
                        {post.post_body_truncated ? " ..." : ""}
                      </span>
                    </span>
                  </>
                );
                return (
                  <button
                    type="button"
                    className="related-post-card"
                    aria-label={tf("Open related post: {label}", { label: post.post_title })}
                    onClick={() => onSelectPost(post.post_id)}
                  >
                    {cardContent}
                    <span className="related-post-cta">{t("Open record")}</span>
                  </button>
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
  onSelectPerson: (personId: string, personName: string) => void;
  onSelectEntity: (entityId: string, entityName: string) => void;
}) {
  return (
    <li>
      <span className={node.resolved ? "affiliate-resolved" : "affiliate-unresolved"}>
        {node.resolved && node.entity_id ? (
          <button
            className="keyman-select"
            aria-label={tf("Affiliate org: {name}", { name: node.entity_name })}
            onClick={() => onSelectEntity(node.entity_id!, node.entity_name)}
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
      {!node.resolved && <span className="affiliate-unresolved-mark"> {t("unresolved")}</span>}
      {node.people.length > 0 && (
        <span className="keyman-affiliations">
          {" -- "}
          {node.people.map((person, index) => (
            <span key={person.person_id}>
              {index > 0 ? ", " : null}
              <button
                className="keyman-select"
                aria-label={tf("Affiliate Keyman: {name}", { name: person.person_name })}
                onClick={() => onSelectPerson(person.person_id, person.person_name)}
              >
                {person.person_name} ({person.person_side_label ?? person.person_side_code})
              </button>
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
  if (!evidence) return <p>{t("Loading VOC evidence...")}</p>;
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

const CHAT_EVIDENCE_KIND_LABELS: Record<string, string> = {
  source_field: "Source field hint",
  semantic_project: "Semantic project",
  semantic_role: "Semantic role",
  semantic_keyman: "Semantic Keyman",
  semantic_event: "Semantic event",
  semantic_event_clue: "Semantic event clue",
  semantic_quantitative: "Semantic quantitative evidence",
  semantic_source_fact: "Semantic source-grounded fact",
  semantic_relation: "Semantic relationship",
};

function chatEvidenceKindLabel(kind: string): string {
  return t(CHAT_EVIDENCE_KIND_LABELS[kind] ?? "Evidence");
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
  onSelectPost: (postId: string) => void;
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
        <p>{t("Loading related nodes...")}</p>
      ) : related.length === 0 ? (
        <p className="popup-placeholder">{t("No related nodes in the visible graph.")}</p>
      ) : (
        <>
          {relatedPosts.length > 0 ? (
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
                      aria-label={tf("Related nodes for {name}", { name: node.label ?? node.node_id })}
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
                      aria-label={tf("Related nodes for {name}", { name: node.label ?? node.node_id })}
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
        {canExtract && !orchestratorOff && (
          <details className="operator-action-tools">
            <summary>{t("Evidence operations")}</summary>
            <button onClick={handleExtract} disabled={extracting}>
              {extracting ? t("Extracting...") : t("Extract Keymen")}
            </button>
          </details>
        )}
      </div>
      {error && <ExceptionAlert title={error} />}
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
                        <button
                          className="keyman-select"
                          aria-label={tf("Keyman affiliation: {name}", { name: affiliation.organization_name })}
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
            <p>{t("Loading related nodes...")}</p>
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
    </>
  );
}

function EvaluationPanel({
  postId,
  accessToken,
  responses,
  canExtract,
  onEvaluated,
  focusCriterionCode,
  channelDropped = false,
}: {
  postId: string;
  accessToken: string;
  responses: EvaluationResponse[] | null;
  canExtract: boolean;
  onEvaluated: (rows: EvaluationResponse[]) => void;
  focusCriterionCode?: string;
  channelDropped?: boolean;
}) {
  const [evaluating, setEvaluating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [orchestratorOff, setOrchestratorOff] = useState(false);

  useEffect(() => {
    setOrchestratorOff(false);
    setError(null);
  }, [postId]);

  const channelUnavailable = orchestratorOff || channelDropped;
  const hasSavedScores = responses !== null && responses.length > 0;
  const droppedDiagnosis = channelUnavailable
    ? analysisEvidenceDiagnosis("dropped_channel")
    : null;

  useEffect(() => {
    if (!focusCriterionCode || responses === null) {
      return;
    }
    const target =
      document.getElementById(postQualityCriterionElementId(focusCriterionCode)) ??
      document.getElementById("post-quality-evaluation");
    target?.focus();
    target?.scrollIntoView?.({ block: "nearest" });
  }, [focusCriterionCode, responses]);

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
        <h3 id="post-quality-evaluation" tabIndex={-1}>
          {t("Post quality (IRT)")}
        </h3>
        {canExtract && !channelUnavailable && (
          <details className="operator-action-tools">
            <summary>{t("Evidence operations")}</summary>
            <button onClick={handleEvaluate} disabled={evaluating}>
              {evaluating ? t("Evaluating...") : t("Evaluate post")}
            </button>
          </details>
        )}
      </div>
      {error && <ExceptionAlert title={error} />}
      {droppedDiagnosis ? (
        <p className="post-meta" role="status">
          {t(droppedDiagnosis.title)}. {t(droppedDiagnosis.nextAction)}
        </p>
      ) : null}
      {responses === null ? (
        <p>{t("Loading evaluation...")}</p>
      ) : hasSavedScores ? (
        <ul>
          {responses.map((row) => {
            const negative =
              row.criterion_code === "general_sentiment_negative" && row.response_category >= 2
                ? analysisEvidenceDiagnosis("confident_negative")
                : null;
            return (
              <li
                key={row.criterion_code}
                id={postQualityCriterionElementId(row.criterion_code)}
                tabIndex={-1}
                aria-current={focusCriterionCode === row.criterion_code ? "true" : undefined}
              >
                {row.criterion_label ?? row.criterion_code}: {row.response_category}
                {negative ? (
                  <span className="post-meta" role="status">
                    {" "}
                    {t(negative.nextAction)}
                  </span>
                ) : null}
              </li>
            );
          })}
        </ul>
      ) : channelUnavailable ? null : (
        <p className="popup-placeholder">{t("Not yet evaluated.")}</p>
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
  onSelectEntity: (entityId: string, entityName: string) => void;
  onSelectPost: (postId: string) => void;
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
      {error && <ExceptionAlert title={error} />}
      <ul>
        {counterparties.map((c) => (
          <li key={c.counterparty_entity_name}>
            {c.corporate_entity_id ? (
              <button
                className="keyman-select"
                aria-label={tf("Counterparty org: {name}", { name: c.counterparty_entity_name })}
                onClick={() => onSelectEntity(c.corporate_entity_id!, c.counterparty_entity_name)}
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
              ariaLabel={tf("Counterparty verification: {name}", { name: c.counterparty_entity_name })}
            />
            {c.verification_evidence_post_id ? (
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
      setError(productExceptionCopy(err, t("Issue tickets")).title);
    } finally {
      setCreating(false);
    }
  }

  async function handleStatusChange(ticket: IssueTicket, nextStatus: string) {
    try {
      await updateTicketStatus(accessToken, ticket.issue_ticket_id, nextStatus);
      reload();
    } catch (err) {
      setError(productExceptionCopy(err, t("Issue tickets")).title);
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
      {error && <ExceptionAlert title={error} />}
      {tickets === null ? (
        <p>{t("Loading tickets...")}</p>
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
          aria-label={t("New ticket title")}
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
      .catch((err) => setError(productExceptionCopy(err, t("Activity")).title));
  }

  useEffect(() => {
    setEvents(null);
    setError(null);
    fetchPostActivity(accessToken, postId)
      .then((r) => setEvents(r.events))
      .catch((err) => setError(productExceptionCopy(err, t("Activity")).title));
  }, [postId, accessToken]);

  return (
    <section className="popup-section">
      <div className="lineage-home-header">
        <h3>{t("Activity")}</h3>
        <button onClick={reload}>{t("Refresh")}</button>
      </div>
      {error && (
        <ExceptionAlert
          title={error}
          retryLabel={t("Refresh")}
          onRetry={reload}
        />
      )}
      {events === null ? (
        <p>{t("Loading activity...")}</p>
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

const SEMANTIC_RELATION_LABELS: Record<string, string> = {
  org_member_of: "Organization member of",
  org_unit_of: "Organization unit of",
  org_suborganization_of: "Sub-organization of",
  lw_responsible_for: "Responsible for",
  lw_supports: "Supports",
};

function semanticRelationLabel(relation: PostSemanticRelationship): string {
  return t(
    SEMANTIC_RELATION_LABELS[relation.predicate_code] ??
      relation.ontology_label ??
      relation.predicate_code,
  );
}

const ROLE_ACTOR_TYPE_RANK: Record<string, number> = {
  prov_organization: 0,
  prov_team: 1,
  prov_software_agent: 2,
  prov_person: 3,
};

// R&R read order follows the PROV-O broader/narrower direction (ADR 0004):
// an organization, then the teams affiliated with it, then the people
// affiliated with it -- not raw LLM extraction order. Grouping is keyed by
// `affiliated_organization_name` for every actor type, including
// organization rows themselves (a subsidiary org's row is affiliated with
// its parent org and must cluster under it, not stand as its own group)
// -- a row only anchors its own group when it has no
// affiliated_organization_name at all. A person's specific team
// membership isn't part of PostRoleResponsibility, so people group by
// their affiliated organization alongside that organization's teams, not
// nested under one specific team.
function sortRolesByOntologyOrder(
  roles: PostRoleResponsibility[],
): PostRoleResponsibility[] {
  const groupKey = (role: PostRoleResponsibility) =>
    role.affiliated_organization_name || role.actor_name;
  const isGroupAnchor = (role: PostRoleResponsibility) =>
    role.actor_type_code === "prov_organization" && !role.affiliated_organization_name;
  return roles
    .map((role, index) => ({ role, index }))
    .sort((a, b) => {
      const groupCompare = groupKey(a.role).localeCompare(groupKey(b.role));
      if (groupCompare !== 0) return groupCompare;
      const anchorCompare = Number(isGroupAnchor(b.role)) - Number(isGroupAnchor(a.role));
      if (anchorCompare !== 0) return anchorCompare;
      const rankCompare =
        (ROLE_ACTOR_TYPE_RANK[a.role.actor_type_code] ?? 3) -
        (ROLE_ACTOR_TYPE_RANK[b.role.actor_type_code] ?? 3);
      if (rankCompare !== 0) return rankCompare;
      return a.index - b.index;
    })
    .map(({ role }) => role);
}

// ADR 0141: translate a closed catalog_unresolved_reason_code into the
// specific, honest reason a reader can act on, instead of one flat
// "Not linked to catalog" label for every cause. Returns null (render
// nothing) for a historical row written before the reason was tracked.
function catalogUnresolvedReasonLabel(
  reasonCode: string | null | undefined,
  translate: (key: string) => string,
): string | null {
  switch (reasonCode) {
    case "reason_tied_candidates":
      return translate("Multiple equally likely matches");
    case "reason_no_live_client":
      return translate("No live enrichment service configured");
    case "reason_not_corroborated":
      return translate("Checked, not independently corroborated");
    case "reason_no_catalog_entry":
      return translate("No matching catalog entry yet");
    default:
      return null;
  }
}

interface RoleTreeNode {
  role: PostRoleResponsibility;
  children: RoleTreeNode[];
}

// Turns the sorted, grouped list into a real tree: a person or team whose
// affiliated_organization_name matches another row's own actor_name nests
// under that row instead of repeating "· 소속: X" as a flat, disconnected
// bullet next to it -- two researchers at the same institute now share a
// visual parent instead of just sorting adjacent to each other.
function buildRoleTree(roles: PostRoleResponsibility[]): RoleTreeNode[] {
  const sorted = sortRolesByOntologyOrder(roles);
  const organizationsByName = new Map<string, PostRoleResponsibility>();
  for (const role of sorted) {
    if (role.actor_type_code === "prov_organization" && !organizationsByName.has(role.actor_name)) {
      organizationsByName.set(role.actor_name, role);
    }
  }
  const nodesByRole = new Map<PostRoleResponsibility, RoleTreeNode>();
  for (const role of sorted) nodesByRole.set(role, { role, children: [] });
  const roots: RoleTreeNode[] = [];
  for (const role of sorted) {
    const parent = role.affiliated_organization_name
      ? organizationsByName.get(role.affiliated_organization_name)
      : undefined;
    const node = nodesByRole.get(role) as RoleTreeNode;
    if (parent && parent !== role) {
      (nodesByRole.get(parent) as RoleTreeNode).children.push(node);
    } else {
      roots.push(node);
    }
  }
  return roots;
}

interface KeyEventGroup {
  projectName: string | null;
  items: { event: PostKeyEvent; originalIndex: number }[];
}

// Consecutive key events sharing the same project_name (the LLM's own
// grouping signal) nest under one heading instead of repeating "{project
// name}: " as a flat text prefix on every line -- only adjacent events are
// merged so this never reorders the events' original narrative sequence.
function groupKeyEventsByProject(events: PostKeyEvent[]): KeyEventGroup[] {
  const groups: KeyEventGroup[] = [];
  events.forEach((event, originalIndex) => {
    const projectName = event.project_name ?? null;
    const last = groups[groups.length - 1];
    if (projectName !== null && last?.projectName === projectName) {
      last.items.push({ event, originalIndex });
    } else {
      groups.push({ projectName, items: [{ event, originalIndex }] });
    }
  });
  return groups;
}

function isWritingSourceDetailState(code: string | null | undefined): boolean {
  return (code ?? "").trim().toUpperCase() === "W";
}

function PostDetailPopup({
  postId,
  accessToken,
  canExtract,
  graph,
  liveBodyWarning,
  knowledgeCutoff,
  focusEventLineage,
  focusCriterionCode,
  onClose,
  onAskPost,
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
  focusCriterionCode?: string;
  onClose: () => void;
  onAskPost: (postId: string, postTitle: string) => void;
  onSelectPost: (postId: string) => void;
  onSearch: (query: string) => void;
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
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [summaryRetry, setSummaryRetry] = useState(0);
  const contentStatusRef = useRef<"ready" | "processing" | "unavailable" | undefined>(undefined);
  const [contentStatus, setContentStatus] = useState<"ready" | "processing" | "unavailable" | undefined>(undefined);
  const [fiveW1H, setFiveW1H] = useState<PostFiveW1H | null>(null);
  const [keymen, setKeymen] = useState<Keyman[] | null>(null);
  const [sourceAuthorContext, setSourceAuthorContext] = useState<SourceAuthorContext | null>(null);
  const [counterparties, setCounterparties] = useState<Counterparty[] | null>(null);
  const [lineage, setLineage] = useState<PostLineage | null>(null);
  const [lineageError, setLineageError] = useState<string | null>(null);
  const [knowledgeGraph, setKnowledgeGraph] = useState<KnowledgeGraph | null>(null);
  const [affiliateTrees, setAffiliateTrees] = useState<AffiliateNode[] | null>(null);
  const [vocEvidence, setVocEvidence] = useState<VocEvidence | null>(null);
  const [evaluation, setEvaluation] = useState<EvaluationResponse[] | null>(null);
  const [evaluationDropped, setEvaluationDropped] = useState(false);
  const [focusPerson, setFocusPerson] = useState<{ personId: string; personName: string } | null>(null);
  const [focusEntity, setFocusEntity] = useState<{ entityId: string; entityName: string } | null>(null);
  const [focusTeam, setFocusTeam] = useState<{ teamId: string; teamName: string } | null>(null);
  const contentReloadRef = useRef<() => void>(() => undefined);
  const popupPanelRef = useRef<HTMLDivElement>(null);
  const onCloseRef = useRef(onClose);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    const panel = popupPanelRef.current;
    const previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    if (!panel) return;
    panel.focus({ preventScroll: true });

    const focusableSelector =
      'a[href], area[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), summary, [tabindex]:not([tabindex="-1"])';
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab") return;
      const focusable = Array.from(panel.querySelectorAll<HTMLElement>(focusableSelector)).filter(
        (element) =>
          !element.hidden &&
          !element.closest('[aria-hidden="true"]') &&
          (!element.closest("details:not([open])") || element.matches("summary")),
      );
      if (focusable.length === 0) {
        event.preventDefault();
        panel.focus();
        return;
      }
      const currentIndex = focusable.indexOf(document.activeElement as HTMLElement);
      const nextIndex = event.shiftKey
        ? currentIndex <= 0
          ? focusable.length - 1
          : currentIndex - 1
        : currentIndex < 0 || currentIndex === focusable.length - 1
          ? 0
          : currentIndex + 1;
      event.preventDefault();
      focusable[nextIndex].focus();
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      if (previouslyFocused && document.contains(previouslyFocused)) previouslyFocused.focus();
    };
  }, []);

  function reloadKeymen() {
    if (isWritingSourceDetailState(post?.source_detail_state_code)) return;
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
    if (isWritingSourceDetailState(post?.source_detail_state_code)) return;
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
    setSummaryLoading(true);
    contentStatusRef.current = undefined;
    setContentStatus(undefined);
    setFiveW1H(null);
    setKeymen(null);
    setSourceAuthorContext(null);
    setCounterparties(null);
    setLineage(null);
    setLineageError(null);
    setKnowledgeGraph(null);
    setAffiliateTrees(null);
    setVocEvidence(null);
    setEvaluation(null);
    setEvaluationDropped(false);
    setFocusPerson(null);
    setFocusEntity(null);
    setFocusTeam(null);
    let disposed = false;
    let contentPollTimer: number | undefined;
    const asOf = liveBodyWarning && knowledgeCutoff ? knowledgeCutoff : undefined;
    const loadDerivedPostData = (loadedPost: PostDetail) => {
      if (isWritingSourceDetailState(loadedPost.source_detail_state_code)) return;
      fetchPostEvaluation(accessToken, postId)
        .then((r) => {
          setEvaluation(r.responses);
          setEvaluationDropped(false);
        })
        .catch((err) => {
          setEvaluation([]);
          setEvaluationDropped(err instanceof BackendError && err.status === 503);
        });
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
      fetchPostLineage(accessToken, postId)
        .then((value) => {
          setLineage(value);
          setLineageError(null);
        })
        .catch((err) => {
          setLineage(null);
          setLineageError(productExceptionCopy(err, t("Related posts")).title);
        });
      fetchPostKnowledgeGraph(accessToken, postId)
        .then(setKnowledgeGraph)
        .catch(() => setKnowledgeGraph(null));
      fetchPostAffiliateTree(accessToken, postId)
        .then((r) => setAffiliateTrees(r.trees))
        .catch(() => setAffiliateTrees([]));
      fetchPostVocEvidence(accessToken, postId).then(setVocEvidence).catch(() => setVocEvidence(null));
    };
    fetchPost(accessToken, postId, asOf)
      .then((loadedPost) => {
        if (disposed) return;
        setPost(loadedPost);
        loadDerivedPostData(loadedPost);
        if (!isWritingSourceDetailState(loadedPost.source_detail_state_code)) {
          reloadContent();
        }
      })
      .catch((err) => setError(productExceptionCopy(err, "This post").title));
    const reloadContent = () =>
      fetchPostContent(accessToken, postId)
        .then((content) => {
          if (disposed) return;
          const previousStatus = contentStatusRef.current;
          contentStatusRef.current = content.status;
          setContentStatus(content.status);
          setImageContent(content.images);
          setStructureUnits(content.units);
          if (previousStatus === "processing" && content.status === "ready") {
            setSummaryRetry((value) => value + 1);
          }
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
    fetchPostBookmark(accessToken, postId)
      .then((r) => setBookmarked(r.bookmarked))
      .catch(() => {
        setBookmarked(null);
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
    setSummaryLoading(true);
    if (!post) {
      return () => {
        disposed = true;
      };
    }
    if (isWritingSourceDetailState(post.source_detail_state_code)) {
      setSummaryLoading(false);
      return () => {
        disposed = true;
      };
    }
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
      })
      .finally(() => {
        if (!disposed) setSummaryLoading(false);
      });
    return () => {
      disposed = true;
    };
  }, [postId, accessToken, summaryRetry, post]);

  const permanentLink = (() => {
    const url = new URL(window.location.href);
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

  return (
    <div className="popup-backdrop" onClick={onClose}>
      <div
        ref={popupPanelRef}
        className="popup-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby={post ? "post-detail-title" : undefined}
        aria-label={!post ? t("Post details") : undefined}
        tabIndex={-1}
        onClick={(event) => event.stopPropagation()}
      >
        <PopupCloseButton onClose={onClose} label={t("Close")} />
        {error && <ExceptionAlert title={error} />}
        {!post && !error && <p>{t("Loading...")}</p>}
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
              {!isWritingSourceDetailState(post.source_detail_state_code) ? (
                <button type="button" onClick={() => onAskPost(postId, post.post_title)}>
                  {t("Ask about this lineage")}
                </button>
              ) : null}
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

					<div className="popup-analysis-grid">
              <section className="popup-section popup-analysis-col">
              <h3>{t("Summary")}</h3>
              {isWritingSourceDetailState(post.source_detail_state_code) ? (
                <SummaryStatus
                  kind="empty"
                  title={t("Summary is not created for writing posts.")}
                  description={t("The source is still being written; analysis starts after approval.")}
                />
              ) : !summary && (summaryLoading || contentStatus === "processing") ? (
                <SummaryStatus
                  kind="processing"
                  title={t("Summary is being prepared.")}
                  description={
                    contentStatus === "processing"
                      ? t("Source evidence is still being processed.")
                      : t("The source evidence is still being analyzed.")
                  }
                />
              ) : summary ? (
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
                        {(() => {
                          const summarySnapshot = summary;
                          function renderKeyEventBody(event: PostKeyEvent, index: number): ReactNode {
                            return (
                              <>
                                {event.evidence_text ? (
                                  <small>
                                    {t("Evidence")}: {event.evidence_text}
                                  </small>
                                ) : null}
                                {summarySnapshot.event_clues?.filter((clue) => clue.event_index === index).length ? (
                                  <div className="summary-event-clues">
                                    <small>{t("Connected clues")}</small>
                                    {summarySnapshot.event_clues
                                      .filter((clue) => clue.event_index === index)
                                      .map((clue, clueIndex) => (
                                        <span className="post-badge" key={`${clue.clue_type_code}:${clueIndex}`}>
                                          {clue.clue_type_code.replace(/^clue_/, "")}: {clue.clue_text}
                                          {clue.target_text ? ` · ${t("Target")}: ${clue.target_text}` : ""}
                                          {clue.assertion_code === "assertion_negated" ? ` · ${t("Negated clue")}` : ""}
                                        </span>
                                      ))}
                                  </div>
                                ) : null}
                              </>
                            );
                          }
                          const events: PostKeyEvent[] =
                            summary.key_event_details ??
                            summary.key_events.map((event) => ({
                              event_text: event,
                              project_name: null,
                              evidence_text: null,
                            }));
                          return groupKeyEventsByProject(events).map((group, groupIndex) => {
                            if (group.projectName && group.items.length > 1) {
                              return (
                                <li key={`event-group-${groupIndex}`}>
                                  <strong>{group.projectName}</strong>
                                  <ul className="customer-master-tree-children">
                                    {group.items.map(({ event, originalIndex }) => (
                                      <li key={originalIndex}>
                                        {event.event_text}
                                        {renderKeyEventBody(event, originalIndex)}
                                      </li>
                                    ))}
                                  </ul>
                                </li>
                              );
                            }
                            const { event, originalIndex } = group.items[0];
                            return (
                              <li key={originalIndex}>
                                {event.project_name ? <strong>{event.project_name}: </strong> : null}
                                {event.event_text}
                                {renderKeyEventBody(event, originalIndex)}
                              </li>
                            );
                          });
                        })()}
                      </ul>
                    </>
                  )}
                  {summary.roles_and_responsibilities.length > 0 && (
                    <>
                      <h4>{t("R&R")}</h4>
                      <ul>
                        {(() => {
                          function renderRoleNode(node: RoleTreeNode, isChild: boolean): ReactNode {
                          const rr = node.role;
                          const isPerson = rr.actor_type_code === "prov_person";
                          const actorTypeLabel = t(
                            rr.actor_type_code === "prov_team"
                              ? "Team"
                              : rr.actor_type_code === "prov_software_agent"
                                ? "Software agent"
                                : isPerson
                                  ? "Person"
                                  : "Organization",
                          );
                          const person = isPerson
                            ? keymen?.find((row) => row.person_name === rr.actor_name)
                            : undefined;
                          const catalogId = rr.catalog_node_id;
                          const catalogType = rr.catalog_node_type_code;
                          const genericTeam = isGenericTeamActor(rr.actor_type_code, rr.actor_name);
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
                          } else if (catalogType === NODE_TEAM && catalogId && !genericTeam) {
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
                            <RoleEvidence
                              key={rr.actor_name + rr.actor_type_code + rr.responsibility}
                              actorContent={actorName}
                              actorName={rr.actor_name}
                              actorTypeCode={rr.actor_type_code}
                              actorTypeLabel={actorTypeLabel}
                              responsibility={rr.responsibility}
                              // A row nested under its affiliated org's <li>
                              // already shows that relationship structurally
                              // -- repeating "· 소속: X" next to it would be
                              // redundant, so only un-nested (root) rows show it.
                              affiliationName={isChild ? null : rr.affiliated_organization_name}
                              affiliationCatalogId={rr.affiliated_organization_catalog_id}
                              affiliationLabel={t("Affiliation")}
                              affiliationAriaLabel={tf("R&R affiliation: {name}", {
                                name: rr.affiliated_organization_name ?? "",
                              })}
                              unresolvedLabel={t("Not linked to catalog")}
                              affiliationUnresolvedReasonLabel={catalogUnresolvedReasonLabel(
                                rr.affiliation_catalog_unresolved_reason_code,
                                t,
                              )}
                              actorUnresolvedReasonLabel={catalogUnresolvedReasonLabel(
                                rr.catalog_unresolved_reason_code,
                                t,
                              )}
                              unresolvedNextAction={t(analysisEvidenceDiagnosis("catalog_unbound").nextAction)}
                              relationshipNextAction={t(gluedRoleRelationshipNextAction())}
                              genericUnitNote={t("Specific business unit not stated in source")}
                              onSelectAffiliation={(entityId, entityName) => {
                                setFocusPerson(null);
                                setFocusTeam(null);
                                setFocusEntity({ entityId, entityName });
                              }}
                            >
                              {node.children.length > 0 ? (
                                <ul className="customer-master-tree-children">
                                  {node.children.map((child) => renderRoleNode(child, true))}
                                </ul>
                              ) : null}
                            </RoleEvidence>
                          );
                          }
                          return buildRoleTree(summary.roles_and_responsibilities).map((node) =>
                            renderRoleNode(node, false),
                          );
                        })()}
                      </ul>
                    </>
                  )}
                  {summary.semantic_relationships && summary.semantic_relationships.length > 0 && (
                    <>
                      <h4>{t("Explicit semantic relationships")}</h4>
                      <ul className="summary-action-list semantic-relationship-list">
                        {summary.semantic_relationships.map((relation) => (
                          <li key={`${relation.relation_ordinal}:${relation.subject_name}:${relation.object_name}`}>
                            <div className="semantic-relationship-line">
                              <strong>{relation.subject_name}</strong>
                              <span className="post-badge">{semanticRelationLabel(relation)}</span>
                              <strong>{relation.object_name}</strong>
                            </div>
                            <small>
                              {t("Evidence")}: {relation.evidence_text} · {t("Confidence")}: {Math.round(relation.confidence * 100)}%
                            </small>
                            <details className="semantic-provenance">
                              <summary>{t("Evidence provenance")}</summary>
                              <span className="post-badge">
                                {t("Subject type")}: {relation.subject_type}
                              </span>
                              <span className="post-badge">
                                {t("Object type")}: {relation.object_type}
                              </span>
                              <span className="post-badge">
                                {t("Extraction source")}: {relation.extraction_method ?? t("Recorded extraction")}
                              </span>
                            </details>
                          </li>
                        ))}
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
                  {summary.quantitative_observations && summary.quantitative_observations.length > 0 && (
                    <>
                      <h4>{t("Quantitative evidence")}</h4>
                      <ul className="summary-action-list">
                        {summary.quantitative_observations.map((observation, i) => (
                          <li key={`${observation.measurement_type_code}:${observation.raw_value_text}:${i}`}>
                            <strong>
                              {observation.label_text}: {observation.raw_value_text}
                            </strong>
                            {observation.quantity_numeric !== null ? (
                              <div>
                                {t("Quantity")}: {observation.quantity_numeric} {observation.quantity_unit_code}
                              </div>
                            ) : null}
                            {observation.qualifier_text ? <div>{observation.qualifier_text}</div> : null}
                            <small>
                              {t("Evidence")}: {observation.evidence_text}
                            </small>
                            <details className="semantic-provenance">
                              <summary>{t("Evidence provenance")}</summary>
                              <span className="post-badge">
                                {t("Ontology class")}: {t(observation.ontology_label ?? "Quantitative observation")}
                              </span>
                              <span className="post-badge">
                                {t("Extraction source")}: {observation.extraction_method}
                              </span>
                            </details>
                          </li>
                        ))}
                      </ul>
                    </>
                  )}
                  {summary.source_grounded_facts && summary.source_grounded_facts.length > 0 && (
                    <>
                      <h4>{t("Source-grounded facts")}</h4>
                      <ul className="summary-action-list">
                        {summary.source_grounded_facts.map((fact, i) => (
                          <li key={`${fact.fact_type_code}:${fact.value_text}:${i}`}>
                            <strong>
                              {fact.label_text}: {fact.value_text}
                            </strong>
                            {fact.assertion_code === "assertion_negated" ? (
                              <div>{t("Negated condition")}</div>
                            ) : null}
                            {fact.normalized_date ? (
                              <div>
                                {t("Normalized date")}: {fact.normalized_date}
                              </div>
                            ) : null}
                            {fact.normalization_evidence_text ? (
                              <small>
                                {t("Normalization evidence")}: {fact.normalization_evidence_text}
                              </small>
                            ) : null}
                            <small>
                              {t("Evidence")}: {fact.evidence_text}
                            </small>
                            <details className="semantic-provenance">
                              <summary>{t("Evidence provenance")}</summary>
                              <span className="post-badge">
                                {t("Ontology class")}: {t(fact.ontology_label ?? "Source-grounded fact")}
                              </span>
                              <span className="post-badge">
                                {t("Extraction source")}: {fact.extraction_method}
                              </span>
                            </details>
                          </li>
                        ))}
                      </ul>
                    </>
                  )}
                </>
              ) : summaryError ? (
                <SummaryStatus
                  kind="unavailable"
                  title={t("Summary could not be generated.")}
                  description={t("The source record remains available.")}
                  detail={summaryError}
                  retryLabel={t("Retry summary refresh")}
                  onRetry={() => setSummaryRetry((value) => value + 1)}
                />
              ) : (
                <SummaryStatus
                  kind="empty"
                  title={t("No saved summary exists for this record.")}
                  description={t("The source record is available, but no summary has been saved.")}
                  retryLabel={t("Retry summary refresh")}
                  onRetry={() => setSummaryRetry((value) => value + 1)}
                />
              )}
              </section>
              <div className="popup-analysis-col">
                <FiveW1H slots={fiveW1H?.slots ?? null} />
              </div>
            </div>

            <div className="popup-secondary-grid">
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
                        onClick={() => onSearch(project.project_name)}
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
              post.source_process_unit_catalog_name ||
              post.source_sales_pool_code ||
              post.source_sales_pool_name ||
              post.source_order_pool_code ||
              post.source_sales_order_code ||
              (post.source_sales_order_item_number !== null && post.source_sales_order_item_number !== undefined) ||
              post.source_inspection_point_code ||
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
                      {(() => {
                        const presentation = presentSourceDetailState(post.source_detail_state_code);
                        return (
                          <dd aria-label={presentation.accessibleName}>
                            <strong className="board-source-detail-state-code">{presentation.code}</strong> · {presentation.description}
                          </dd>
                        );
                      })()}
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
                  {post.source_process_unit_catalog_name ? (
                    <>
                      <dt>{t("Source process unit catalog hint")}</dt>
                      <dd className="source-context-hint">
                        {t("Catalog hint")}: {post.source_process_unit_catalog_name}
                      </dd>
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
                  {post.source_order_pool_code ? (
                    <>
                      <dt>{t("Source order pool")}</dt>
                      <dd>{post.source_order_pool_code}</dd>
                    </>
                  ) : null}
                  {post.source_sales_order_code ? (
                    <>
                      <dt>{t("Source sales order")}</dt>
                      <dd>{post.source_sales_order_code}</dd>
                    </>
                  ) : null}
                  {post.source_sales_order_item_number !== null && post.source_sales_order_item_number !== undefined ? (
                    <>
                      <dt>{t("Source sales order item")}</dt>
                      <dd>{post.source_sales_order_item_number}</dd>
                    </>
                  ) : null}
                  {post.source_inspection_point_code ? (
                    <>
                      <dt>{t("Source inspection point")}</dt>
                      <dd>{post.source_inspection_point_code}</dd>
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
                {post.source_lineage_hints ? (
                  <div className="source-lineage-hint" aria-label={t("Source lineage combination")}>
                    <h4>{t("Source lineage combination")}</h4>
                    <p>
                      <strong>{sourceLineageContextLabel(post.source_lineage_hints)}</strong>{" "}
                      <span className="post-badge">{t("Combination code")}: {post.source_lineage_hints.combination_code}</span>{" "}
                      <span className="post-meta">{t("Inferred from field presence")}</span>
                    </p>
                    <p className="post-meta">{t("Field combination")}</p>
                    <ul className="source-lineage-fields">
                      {SOURCE_LINEAGE_FIELDS.map((field) => {
                        const values: Record<string, string | null> = {
                          customer: post.source_customer_code || post.source_customer_name || null,
                          order_pool: post.source_order_pool_code || null,
                          sales_order: post.source_sales_order_code || null,
                          sales_order_item:
                            post.source_sales_order_item_number === null || post.source_sales_order_item_number === undefined
                              ? null
                              : String(post.source_sales_order_item_number),
                        };
                        const present = sourceLineageFieldIsPresent(post.source_lineage_hints!, field);
                        return (
                          <li key={field} className={present ? "is-present" : "is-missing"}>
                            <span>{sourceLineageFieldLabel(field)}</span>
                            <strong>{present ? values[field] || t("Present") : t("Not present")}</strong>
                          </li>
                        );
                      })}
                    </ul>
                    <p className="post-meta">
                      {t("Lifecycle vector")}: {post.source_lineage_hints.lifecycle_vector} · {t("Raw codes only")}
                    </p>
                  </div>
                ) : null}
              </section>
            )}
            </div>

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

            {!isWritingSourceDetailState(post.source_detail_state_code) ? (
              <SourceResearchPanel postId={postId} accessToken={accessToken} canResearch={canExtract} />
            ) : null}

            {!focusEventLineage && (
              <EvaluationPanel
                postId={postId}
                accessToken={accessToken}
                responses={evaluation}
                canExtract={canExtract}
                onEvaluated={(rows) => {
                  setEvaluation(rows);
                  setEvaluationDropped(false);
                }}
                focusCriterionCode={focusCriterionCode}
                channelDropped={evaluationDropped}
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

            <RelatedPostsSection lineage={lineage} error={lineageError} onSelectPost={onSelectPost} />

            <section className="popup-section">
                <h3 id="post-event-lineage" tabIndex={-1}>
                {t("Event Lineage")}
              </h3>
              <EventLineageSection
                lineage={lineage}
                lineageUnavailable={Boolean(lineageError)}
                graph={graph}
                postId={postId}
                onSelectPost={onSelectPost}
                currentNextAction={
                  focusEventLineage ? eventLineageCurrentNextAction(post.post_title) : null
                }
              />
            </section>

            {knowledgeGraph ? (
              <section className="popup-section" aria-label={t("Knowledge Graph")}>
                <KnowledgeGraphView graph={knowledgeGraph} onSelectPost={onSelectPost} />
              </section>
            ) : null}

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
                      onEvaluated={(rows) => {
                        setEvaluation(rows);
                        setEvaluationDropped(false);
                      }}
                      focusCriterionCode={focusCriterionCode}
                      channelDropped={evaluationDropped}
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
                <p>{t("Loading affiliate tree...")}</p>
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

/** Git-style prefix. The full digest stays on `title` for verification. */
const ANALYSIS_RUN_DIGEST_PREFIX_LENGTH = 12;

function analysisRunDigestPrefix(digest: string): string {
  return digest.slice(0, ANALYSIS_RUN_DIGEST_PREFIX_LENGTH);
}

type SelectPostOptions = {
  liveAfterCutoff?: boolean;
  knowledgeCutoff?: string;
  fromReportMember?: boolean;
  /** Land leftover clicks on this Post quality criterion (ADR 0049 / 0135). */
  focusCriterionCode?: string;
  /** Set when re-entering a post from a popstate (browser back/forward) so
   * the handler doesn't push a duplicate history entry for a navigation
   * the browser already performed. */
  fromPopState?: boolean;
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
  currentReportPeriod: string;
  onSelectPost: (postId: string, options?: SelectPostOptions) => void;
  onSelectReportPeriod: (
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
      .catch((err) => setError(productExceptionCopy(err, t("Analysis runs")).title));
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
        setError(productExceptionCopy(err, t("Analysis runs")).title);
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
      setError(productExceptionCopy(err, t("Analysis runs")).title);
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
      setError(productExceptionCopy(err, t("Analysis runs")).title);
    }
  }

  if (error && runs === null) {
    return (
      <ExceptionAlert
        title={error}
        retryLabel={t("Retry")}
        onRetry={() => {
          setError(null);
          fetchAnalysisRuns(accessToken)
            .then((payload) => setRuns(payload.analysis_runs))
            .catch((err) => setError(productExceptionCopy(err, t("Analysis runs")).title));
        }}
      />
    );
  }
  if (runs === null) return <p>Loading analysis runs...</p>;

  const corpusHint = selected ? analysisRunCorpusHint(selected) : null;

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
      {(error || entitiesLoadError) && <ExceptionAlert title={error ?? entitiesLoadError ?? ""} />}
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
          <AnalysisRunNextAction
            run={selected}
            starting={starting}
            onStart={() => void handleStartReconstruction()}
            onRefresh={() => void handleOpen(selected.analysis_run_id)}
          />
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
          {analysisRunCanRequestTeppRetry(selected) && (
            <p className="post-meta">
              Connect a TEPP transport from this Failed row. Request a lineage
              reconstruction does not invent a measurement.
            </p>
          )}
          {analysisRunReportPeriod(selected) && (
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
      .catch((err) => setError(productExceptionCopy(err, t("Rankings")).title));
  }, [accessToken]);

  return (
    <section className="popup-section lineage-home" aria-label="Rankings">
      <div className="lineage-home-header">
        <h2>Rankings</h2>
        {ranking && (
          <span className="post-badge">
            {ranking.status === "accepted"
              ? "rankweave"
              : `rankweave · ${ranking.status_reason ?? "unavailable"}`}
          </span>
        )}
      </div>
      {error && (
        <ExceptionAlert
          title={error}
          retryLabel={t("Retry")}
          onRetry={() => {
            setError(null);
            fetchRankings(accessToken)
              .then(setRanking)
              .catch((err) => setError(productExceptionCopy(err, t("Rankings")).title));
          }}
        />
      )}
      {ranking === null && !error && <p>Loading rankings...</p>}
      {ranking && ranking.status === "unavailable" && (
        <p className="popup-placeholder">Rankings · RankWeave not available</p>
      )}
      {ranking && ranking.status === "accepted" && ranking.rankings.length === 0 && (
        <p className="popup-placeholder">No fused rankings from RankWeave.</p>
      )}
      {ranking && ranking.rankings.length > 0 && (
        <ul className="ticket-list" aria-label="Fused rankings">
          {ranking.rankings.map((hit) => (
            <li key={hit.post_id} className="ticket-list-item">
              <button
                className="post-list-item"
                aria-label={`Open ranking: ${hit.post_title}`}
                onClick={() => onSelectPost(hit.post_id)}
              >
                <span className="ticket-title">{hit.post_title}</span>
                <span className="post-badge">Rankings · rankweave</span>
                <span className="post-badge">rank {hit.fused_rank}</span>
              </button>
            </li>
          ))}
        </ul>
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
  const [calendar, setCalendar] = useState<CalendarResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCalendar(accessToken)
      .then(setCalendar)
      .catch((err) => setError(productExceptionCopy(err, t("Calendar")).title));
  }, [accessToken]);

  if (error) {
    return (
      <ExceptionAlert
        title={error}
        retryLabel={t("Retry")}
        onRetry={() => {
          setError(null);
          fetchCalendar(accessToken)
            .then(setCalendar)
            .catch((err) => setError(productExceptionCopy(err, t("Calendar")).title));
        }}
      />
    );
  }
  if (calendar === null) return <p>{t("Loading calendar...")}</p>;

  const events = calendar.events ?? [];
  const commitments = calendar.commitments ?? [];
  const caldavAvailable = calendar.calendar_sources?.caldav_available ?? false;
  const caldavNextAction = calendar.calendar_sources?.caldav_next_action;

  return (
    <section className="popup-section lineage-home">
      <h2>{t("Calendar")}</h2>
      <section className="popup-section">
        <h3>{t("CalDAV events")}</h3>
        {events.length === 0 ? (
          <p className="popup-placeholder">
            {caldavAvailable
              ? t("No CalDAV events are available.")
              : caldavNextAction ?? t("CalDAV is not connected.")}
          </p>
        ) : (
          <ul className="ticket-list">
            {events.map((event) => (
              <li key={event.event_id} className="ticket-list-item">
                <div className="post-list-item">
                  <span className="ticket-title">{event.summary}</span>
                  <span className="post-badge">{event.starts_at}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
      <section className="popup-section">
        <h3>{t("Upcoming commitments")}</h3>
        {commitments.length === 0 ? (
          <p className="popup-placeholder">
            {t("No upcoming commitments. Derive one from a post, or create a ticket with a due date.")}
          </p>
        ) : (
          <ul className="ticket-list">
            {commitments.map((entry) => (
              <li key={entry.issue_ticket_id} className="ticket-list-item">
                <button
                  className="post-list-item"
                  aria-label={`${t("Open commitment for:")} ${entry.post_title}`}
                  onClick={() => onSelectPost(entry.post_id)}
                >
                  <span className="ticket-title">
                    {entry.commitment_summary ?? entry.ticket_title}
                  </span>
                  <span className="post-badge">{entry.post_title}</span>
                  <span className="post-badge">
                    {entry.ticket_status_label ?? entry.ticket_status_code}
                  </span>
                  <span className="post-badge">{t("due")} {entry.due_date}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
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
      .catch((err) => setError(productExceptionCopy(err, t("Period reports")).title));
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
      setError(productExceptionCopy(err, t("Period reports")).title);
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
      <p>Loading reports...</p>
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
            {report.leftover_pairs && report.leftover_pairs.length > 0 && (
              <ul className="ticket-list" aria-label="Leftover pairs">
                {report.leftover_pairs.map((pair) => (
                  <li
                    key={`${pair.pair_kind}:${pair.post_id}:${pair.criterion_code}`}
                    className="ticket-list-item"
                  >
                    <LeftoverPairButton
                      pair={pair}
                      leftoverDistance={pair.leftover_distance}
                      observedResponse={pair.observed_response}
                      expectedResponse={pair.expected_response}
                      onOpen={onSelectPost}
                    />
                  </li>
                ))}
              </ul>
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
      {error && <ExceptionAlert title={error} />}
      {!openedGroupingLabel && reportList}
    </section>
  );
}

const POST_PAGE_SIZE = 50;
type BoardSortOrder = PostSortOrder;

const VOC_TYPE_PRESENTATIONS: Record<string, { code: string; englishLabel: string }> = {
  voc: { code: "VOC", englishLabel: "Voice of Customer" },
  vocc: { code: "VOCC", englishLabel: "Voice of Customer's Customer" },
  voco: { code: "VOCO", englishLabel: "Voice of Competitor" },
  vom: { code: "VOM", englishLabel: "Voice of Market" },
  vop: { code: "VOP", englishLabel: "Voice of Partner" },
};

function presentVocType(option: PostFilterOption): {
  code: string;
  description: string;
  accessibleName: string;
} {
  const presentation = VOC_TYPE_PRESENTATIONS[option.code.trim().toLowerCase()];
  const englishLabel = presentation?.englishLabel ?? option.label;
  const description = t(englishLabel);
  return {
    code: presentation?.code ?? option.code.toUpperCase(),
    description,
    accessibleName:
      description === englishLabel
        ? `${presentation?.code ?? option.code.toUpperCase()} — ${englishLabel}`
        : `${presentation?.code ?? option.code.toUpperCase()} — ${description} (${englishLabel})`,
  };
}

const SOURCE_DETAIL_STATE_PRESENTATIONS: Record<string, string> = {
  W: "Writing in progress",
  D: "Pending approval",
  A: "Approved",
};

function presentSourceDetailState(code: string): {
  code: string;
  description: string;
  accessibleName: string;
} {
  const normalizedCode = code.trim().toUpperCase();
  const englishLabel = SOURCE_DETAIL_STATE_PRESENTATIONS[normalizedCode] ?? "Unmapped source detail state";
  const description = t(englishLabel);
  return {
    code: normalizedCode || code,
    description,
    accessibleName:
      description === englishLabel
        ? `${normalizedCode || code} — ${englishLabel}`
        : `${normalizedCode || code} — ${description} (${englishLabel})`,
  };
}

function PostList({
  accessToken,
  showLabPanels,
  postIdToOpen,
  onPostOpened,
  onAskPost,
  focusSearchRequest,
  onSearchFocusHandled,
  globalSearchRequest,
  onGlobalSearchHandled,
  adminTool,
  onAdminToolHandled,
}: {
  accessToken: string;
  showLabPanels: boolean;
  postIdToOpen: string | null;
  onPostOpened: () => void;
  onAskPost: (postId: string, postTitle: string) => void;
  focusSearchRequest: number;
  onSearchFocusHandled: () => void;
  globalSearchRequest: { id: number; query: string } | null;
  onGlobalSearchHandled: () => void;
  adminTool: AdminBoardTool | null;
  onAdminToolHandled: () => void;
}) {
  const [posts, setPosts] = useState<PostSummary[] | null>(null);
  const [graph, setGraph] = useState<LineageGraph | null>(null);
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
  const [openedFocusCriterionCode, setOpenedFocusCriterionCode] = useState<string | null>(null);
  const [corporateEntities, setCorporateEntities] = useState<CorporateEntityRef[] | null>(null);
  const [entitiesLoadError, setEntitiesLoadError] = useState<string | null>(null);
  const [totalPosts, setTotalPosts] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [loadingPage, setLoadingPage] = useState(false);
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<string[]>([]);
  const [vocTypeFilterOptions, setVocTypeFilterOptions] = useState<PostFilterOption[]>([]);
  const [sourceDetailStateFilter, setSourceDetailStateFilter] = useState<string[]>([]);
  const [sourceDetailStateFilterOptions, setSourceDetailStateFilterOptions] = useState<PostFilterOption[]>([]);
  const [visibilityFilter, setVisibilityFilter] = useState("all");
  const [visibilityFilterOptions, setVisibilityFilterOptions] = useState<PostFilterOption[]>([]);
  const [sortOrder, setSortOrder] = useState<BoardSortOrder>("newest");
  const postsRequest = useRef(0);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const lastFocusedSearchRequest = useRef(0);
  const lastGlobalSearchRequest = useRef(0);
  const advancedReviewRef = useRef<HTMLDetailsElement>(null);

  useEffect(() => {
    if (focusSearchRequest <= 0) {
      // The parent intentionally reuses 1 after each handled request resets
      // its counter to 0. Reset the local guard with it so the next global
      // Search action can focus the input again.
      lastFocusedSearchRequest.current = 0;
      return;
    }
    if (focusSearchRequest <= lastFocusedSearchRequest.current) return;
    const input = searchInputRef.current;
    if (!input) return;
    lastFocusedSearchRequest.current = focusSearchRequest;
    input.focus();
    onSearchFocusHandled();
  }, [focusSearchRequest, onSearchFocusHandled, posts]);

  useEffect(() => {
    if (!globalSearchRequest) {
      lastGlobalSearchRequest.current = 0;
      return;
    }
    if (globalSearchRequest.id <= lastGlobalSearchRequest.current) return;
    lastGlobalSearchRequest.current = globalSearchRequest.id;
    searchBoard(globalSearchRequest.query);
    onGlobalSearchHandled();
  }, [globalSearchRequest, onGlobalSearchHandled]);

  useEffect(() => {
    if (!adminTool || !posts || !advancedReviewRef.current) return;
    const details = advancedReviewRef.current;
    details.open = true;
    const target = adminTool === "advanced" || adminTool === "lineage"
      ? details
      : details.querySelector<HTMLElement>(`[data-admin-surface="${adminTool}"]`) ?? details;
    window.requestAnimationFrame(() => target.scrollIntoView?.({ behavior: "smooth", block: "start" }));
    onAdminToolHandled();
  }, [adminTool, onAdminToolHandled, posts]);

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
    setSelectedPostId(postId);
    setFocusedGraph(null);
    setOpenedAfterCutoff(Boolean(options?.liveAfterCutoff));
    setOpenedCutoffIso(options?.knowledgeCutoff ?? null);
    setOpenedFromReportMember(Boolean(options?.fromReportMember));
    setOpenedFocusCriterionCode(options?.focusCriterionCode ?? null);
    if (!options?.fromPopState) {
      const url = new URL(window.location.href);
      if (url.searchParams.get("post") !== postId) {
        url.searchParams.set("post", postId);
        window.history.pushState({}, "", `${url.pathname}${url.search}${url.hash}`);
      }
    }
  }

  useEffect(() => {
    if (!postIdToOpen) return;
    selectPost(postIdToOpen);
    onPostOpened();
  }, [onPostOpened, postIdToOpen]);

  useEffect(() => {
    function handlePopState() {
      const postId = new URLSearchParams(window.location.search).get("post");
      if (postId) {
        selectPost(postId, { fromPopState: true });
      } else {
        setSelectedPostId(null);
        setOpenedAfterCutoff(false);
        setOpenedCutoffIso(null);
        setOpenedFromReportMember(false);
      }
    }
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  function closeSelectedPost() {
    setSelectedPostId(null);
    setOpenedAfterCutoff(false);
    setOpenedCutoffIso(null);
    setOpenedFromReportMember(false);
    setOpenedFocusCriterionCode(null);
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
        sourceDetailStateFilter.length > 0 ? sourceDetailStateFilter : undefined,
        visibilityFilter === "all" ? undefined : visibilityFilter,
        sort,
      );
      if (requestId !== postsRequest.current) return;
      setPosts(response.posts);
      setTotalPosts(response.total_count);
      setVocTypeFilterOptions(response.voc_type_options ?? []);
      setSourceDetailStateFilterOptions(response.source_detail_state_options ?? []);
      setVisibilityFilterOptions(response.visibility_options ?? []);
      setCurrentPage(page);
    } catch (err) {
      if (requestId !== postsRequest.current) return;
      setError(productExceptionCopy(err, t("Board")).title);
    } finally {
      if (requestId === postsRequest.current) setLoadingPage(false);
    }
  }, [accessToken, searchQuery, sortOrder, typeFilter, sourceDetailStateFilter, visibilityFilter]);

  useEffect(() => {
    void loadPostPage(1);
  }, [loadPostPage]);

  useEffect(() => {
    fetchLineageGraph(accessToken).then(setGraph).catch(() => setGraph({ nodes: [], edges: [] }));
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
      setGraph(await fetchLineageGraph(accessToken));
    } catch (err) {
      setRebuildError(productExceptionCopy(err, t("Event Lineage")).title);
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
  const sourceDetailStateOptions = sourceDetailStateFilterOptions.length
    ? sourceDetailStateFilterOptions
    : Array.from(
        new Set(
          loadedPosts
            .map((post) => post.source_detail_state_code)
            .filter((code): code is string => Boolean(code?.trim())),
        ),
      )
        .sort()
        .map((code) => ({ code, label: code }));
  const filteredPosts = loadedPosts
    .filter((post) => {
      const matchesType = typeFilter.length === 0 || typeFilter.includes(post.voc_type_code);
      const matchesSourceDetailState =
        sourceDetailStateFilter.length === 0 ||
        (post.source_detail_state_code !== null &&
          post.source_detail_state_code !== undefined &&
          sourceDetailStateFilter.includes(post.source_detail_state_code));
      const matchesVisibility = visibilityFilter === "all" || post.visibility_code === visibilityFilter;
      return matchesType && matchesSourceDetailState && matchesVisibility;
    })
    .sort((left, right) => {
      if (sortOrder === "title") {
        return left.post_title.localeCompare(right.post_title);
      }
      const direction = sortOrder === "newest" ? -1 : 1;
      return direction * left.created_at.localeCompare(right.created_at);
    });
  const hasBoardFilters =
    Boolean(searchInput.trim()) ||
    Boolean(searchQuery) ||
    typeFilter.length > 0 ||
    sourceDetailStateFilter.length > 0 ||
    visibilityFilter !== "all";
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
        <ExceptionAlert
          title={error}
          retryLabel={t("Retry")}
          onRetry={() => void loadPostPage(currentPage)}
        />
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
              setSourceDetailStateFilter([]);
              setVisibilityFilter("all");
              setSortOrder("newest");
            }}
          >
            <div className="board-search-row">
              <label>
                {t("Search semantic evidence")}
                <input
                  ref={searchInputRef}
                  type="search"
                  value={searchInput}
                  onChange={(event) => setSearchInput(event.target.value)}
                  placeholder={t("Search semantic evidence")}
                  aria-label={t("Search semantic evidence")}
                />
              </label>
              <button type="submit" className="btn-primary">{t("Search")}</button>
            </div>
            <p className="board-search-help post-meta">{t("Search includes post text and semantic evidence.")}</p>
            <div className="board-filter-row">
              <fieldset className="board-voc-type-filter">
                <legend>{t("Filter by VOC type")}</legend>
                {vocTypeOptions.map((option) => {
                  const presentation = presentVocType(option);
                  return (
                    <label key={option.code} className="board-voc-type-option">
                      <input
                        type="checkbox"
                        checked={typeFilter.includes(option.code)}
                        aria-label={presentation.accessibleName}
                        onChange={(event) =>
                          setTypeFilter((current) =>
                            event.target.checked
                              ? [...current, option.code]
                              : current.filter((code) => code !== option.code),
                          )
                        }
                      />
                      <span className="board-voc-type-code">{presentation.code}</span>
                      <span className="board-voc-type-description">{presentation.description}</span>
                    </label>
                  );
                })}
              </fieldset>
              {sourceDetailStateOptions.length > 0 ? (
                <fieldset className="board-voc-type-filter board-source-detail-state-filter">
                  <legend>{t("Filter by source detail state")}</legend>
                  <p className="board-source-detail-state-help">
                    {t("W = writing in progress · D = pending approval · A = approved")}
                  </p>
                  {sourceDetailStateOptions.map((option) => {
                    const presentation = presentSourceDetailState(option.code);
                    return (
                      <label key={option.code} className="board-choice-option">
                        <input
                          type="checkbox"
                          checked={sourceDetailStateFilter.includes(option.code)}
                          aria-label={presentation.accessibleName}
                          onChange={(event) =>
                            setSourceDetailStateFilter((current) =>
                              event.target.checked
                                ? [...current, option.code]
                                : current.filter((code) => code !== option.code),
                            )
                          }
                        />
                        <span className="board-voc-type-code">{presentation.code}</span>
                        <span className="board-voc-type-description">{presentation.description}</span>
                      </label>
                    );
                  })}
                </fieldset>
              ) : null}
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
                <button type="reset" className="board-reset btn-secondary">
                  {t("Reset filters")}
                </button>
              )}
            </div>
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
              {filteredPosts.map((post) => {
                const sourceDetailState = post.source_detail_state_code
                  ? presentSourceDetailState(post.source_detail_state_code)
                  : null;
                return (
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
                        {post.source_lineage_hints ? (
                          <>
                            <span className="post-meta">
                              {t("Source context")}: {sourceLineageContextLabel(post.source_lineage_hints)}
                            </span>
                            <span className="post-meta source-lineage-presence" aria-label={t("Source fields") + ": " + SOURCE_LINEAGE_FIELDS.map((field) => `${sourceLineageFieldLabel(field)}: ${sourceLineageFieldIsPresent(post.source_lineage_hints!, field) ? t("Present") : t("Not present")}`).join(", ")}>
                              <span>{t("Source fields")}:</span>
                              {SOURCE_LINEAGE_FIELDS.map((field) => {
                                const present = sourceLineageFieldIsPresent(post.source_lineage_hints!, field);
                                return (
                                  <span key={field} className={`source-lineage-presence-item ${present ? "is-present" : "is-missing"}`}>
                                    {sourceLineageFieldLabel(field)} {present ? "✓" : "—"}
                                  </span>
                                );
                              })}
                            </span>
                          </>
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
                        {post.source_lineage_hints ? (
                          <span
                            className="post-badge source-lineage-combination"
                            aria-label={`${t("Field combination")}: ${post.source_lineage_hints.combination_code}, ${sourceLineageContextLabel(post.source_lineage_hints)}`}
                          >
                            <span>{t("Combination code")}</span>
                            <strong className="source-lineage-combination-code">{post.source_lineage_hints.combination_code}</strong>
                            <span className="source-lineage-combination-label">{sourceLineageContextLabel(post.source_lineage_hints)}</span>
                          </span>
                        ) : null}
                        {sourceDetailState ? (
                          <span className="post-badge" aria-label={`${t("Source detail state")}: ${sourceDetailState.accessibleName}`}>
                            {t("Source detail state")}: <strong className="board-source-detail-state-code">{sourceDetailState.code}</strong> · <span className="board-source-detail-state-description">{sourceDetailState.description}</span>
                          </span>
                        ) : null}
                      </span>
                    </button>
                  </article>
                </li>
                );
              })}
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
        <details ref={advancedReviewRef} className="advanced-review-tools">
          <summary>{t("Advanced review tools")}</summary>
          {canRebuild && (
            <section className="popup-section">
              <div className="lineage-home-header">
                <h3>{t("Lineage maintenance")}</h3>
                <button onClick={handleRebuild} disabled={rebuilding}>
                  {rebuilding ? t("Rebuilding...") : t("Rebuild lineage")}
                </button>
              </div>
              {rebuildError && <ExceptionAlert title={rebuildError} />}
            </section>
          )}
          <CalendarPanel accessToken={accessToken} onSelectPost={selectPost} />
          <div data-admin-surface="rankings"><RankingsPanel accessToken={accessToken} onSelectPost={selectPost} /></div>
          <div data-admin-surface="analysis">
            <AnalysisRunsPanel
              accessToken={accessToken}
              currentReportPeriod={reportPeriod}
              onSelectPost={selectPost}
              onSelectReportPeriod={openReportFromAnalysisRun}
              corporateEntities={corporateEntities}
              entitiesLoadError={entitiesLoadError}
            />
          </div>
          <div data-admin-surface="reports">
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
          </div>
        </details>
      )}
      {selectedPostId && (
        <PostDetailPopup
          postId={selectedPostId}
          accessToken={accessToken}
          canExtract={canRebuild}
          graph={focusedGraph ?? graph}
          liveBodyWarning={
            openedAfterCutoff ? analysisRunOpenedBodyWarning(openedCutoffIso) : null
          }
          knowledgeCutoff={openedAfterCutoff ? openedCutoffIso : null}
          focusEventLineage={openedFromReportMember}
          focusCriterionCode={openedFocusCriterionCode ?? undefined}
          onClose={closeSelectedPost}
          onAskPost={onAskPost}
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

function customerScopeFacetLabel(facet: CustomerMasterScopeFacet): string {
  switch (facet) {
    case "authorized_own":
      return t("Own company");
    case "authorized_granted":
      return t("Granted company");
    case "scope_unclassified":
      return t("Scope not classified");
    case "observed_organization":
      return t("Observed organization");
    case "observed_hierarchy":
      return t("Observed hierarchy");
  }
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
  const priorNames = (entity.name_history ?? []).filter(
    (name) => name.name_role_code !== "entity_name_preferred",
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
        <span className="customer-entity-meta">
          <span>{entity.corporate_entity_code} · {entity.entity_level_label}</span>
          {(entity.scope_facets ?? []).map((facet) => (
            <span className="customer-scope-chip" key={facet}>{customerScopeFacetLabel(facet)}</span>
          ))}
        </span>
      </button>
      {expandedEntityId === entity.corporate_entity_id ? (
        <div className="customer-related-posts">
          {priorNames.length > 0 ? (
            <ul aria-label={`${t("Name history")}: ${entity.entity_name}`}>
              {priorNames.map((name) => (
                <li key={`${name.name_role_code}:${name.entity_name}`}>
                  {t(name.name_role_code === "entity_name_former" ? "Former name" : "Alternate name")}: {name.entity_name}
                </li>
              ))}
            </ul>
          ) : null}
          {relatedLoading === entity.corporate_entity_id ? <p>{t("Loading related posts...")}</p> : null}
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

const CUSTOMER_MASTER_SCOPE_FILTERS = ["own", "granted", "observed", "unclassified"] as const;
type CustomerMasterScopeFilter = (typeof CUSTOMER_MASTER_SCOPE_FILTERS)[number];
const CUSTOMER_MASTER_SCOPE_FILTER_LABELS: Record<CustomerMasterScopeFilter, string> = {
  own: "Own company",
  granted: "Granted customer",
  observed: "Observed in posts",
  unclassified: "Unclassified",
};

// An entity can carry more than one facet (e.g. it is both this account's
// own company and an organization observed in a post); it belongs to
// every bucket that applies. No facet at all means an authorized but
// undifferentiated (scope_unclassified) affiliation -- ADR 0125's
// deliberate honest third state, not a guessed own/customer label.
function customerMasterScopeBuckets(entity: CustomerMasterEntity): CustomerMasterScopeFilter[] {
  const facets = entity.scope_facets ?? [];
  const buckets: CustomerMasterScopeFilter[] = [];
  if (facets.includes("authorized_own")) buckets.push("own");
  if (facets.includes("authorized_granted")) buckets.push("granted");
  if (facets.includes("observed_organization") || facets.includes("observed_hierarchy")) buckets.push("observed");
  if (buckets.length === 0) buckets.push("unclassified");
  return buckets;
}

function CustomerMasterPanel({
  accessToken,
  onOpenPost,
}: {
  accessToken: string;
  onOpenPost: (postId: string) => void;
}) {
  const [master, setMaster] = useState<CustomerMasterResponse | null>(null);
  const [scopeFilter, setScopeFilter] = useState<Set<CustomerMasterScopeFilter>>(
    () => new Set(CUSTOMER_MASTER_SCOPE_FILTERS),
  );
  const [error, setError] = useState<string | null>(null);
  const [expandedEntityId, setExpandedEntityId] = useState<string | null>(null);
  const [relatedByEntity, setRelatedByEntity] = useState<Record<string, RelatedNode[]>>({});
  const [relatedLoading, setRelatedLoading] = useState<string | null>(null);
  const [resolvingHint, setResolvingHint] = useState<string | null>(null);
  const [resolveError, setResolveError] = useState<string | null>(null);
  const [hintCodeInput, setHintCodeInput] = useState("");
  const [searchedHintCode, setSearchedHintCode] = useState("");
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
    return fetchCustomerMaster(accessToken, searchedHintCode)
      .then(setMaster)
      .catch(() => setError(t("Customer master could not be loaded.")));
  }, [accessToken, searchedHintCode]);

  useEffect(() => {
    setMaster(null);
    void loadMaster();
  }, [loadMaster]);

  async function handleResolveHint(hint: SourceCustomerHint) {
    if (!hint.customer_code) return;
    const hintKey = `${hint.source_system_code ?? ""}:${hint.customer_code}`;
    setResolvingHint(hintKey);
    setResolveError(null);
    try {
      await resolveCustomerHint(accessToken, hint.customer_code, hint.source_system_code);
      await loadMaster();
    } catch {
      setResolveError(t("This hint could not be resolved to a corroborated organization name."));
    } finally {
      setResolvingHint(null);
    }
  }

  function handleHintSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSearchedHintCode(hintCodeInput.trim());
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

  const filteredEntities = (master?.corporate_entities ?? []).filter((entity) =>
    customerMasterScopeBuckets(entity).some((bucket) => scopeFilter.has(bucket)),
  );

  return (
    <section className="workspace-destination" aria-labelledby="customer-master-heading">
      <p className="section-eyebrow">{t("Customer scope")}</p>
      <h2 id="customer-master-heading">{t("Customer master")}</h2>
      <p className="workspace-destination-intro">{t("Customer entities available to this account.")}</p>
      {error ? <ExceptionAlert title={error} /> : null}
      {master === null && !error ? <p>{t("Loading customer master...")}</p> : null}
      {master?.corporate_entities.length === 0 ? (
        <p className="popup-placeholder">{t("No customer entities are connected to this account.")}</p>
      ) : null}
      <form className="customer-master-hint-search" onSubmit={handleHintSearch}>
        <label htmlFor="customer-master-hint-code">{t("Find source customer code")}</label>
        <div className="customer-master-hint-search-row">
          <input
            id="customer-master-hint-code"
            type="search"
            value={hintCodeInput}
            onChange={(event) => setHintCodeInput(event.target.value)}
            placeholder={t("Paste an observed customer code")}
          />
          <button type="submit">{t("Find")}</button>
        </div>
        <p className="post-meta">{t("Searches all authorized source hints, not only the ranked first page.")}</p>
      </form>
      {searchedHintCode && master && master.source_customer_hints.length === 0 ? (
        <p className="popup-placeholder" role="status">
          {tf("No source customer evidence matches {code}.", { code: searchedHintCode })}
        </p>
      ) : null}
      {master && master.corporate_entities.length > 0 ? (
        <fieldset className="board-voc-type-filter">
          <legend>{t("Filter by scope")}</legend>
          {CUSTOMER_MASTER_SCOPE_FILTERS.map((bucket) => (
            <label key={bucket}>
              <input
                type="checkbox"
                checked={scopeFilter.has(bucket)}
                onChange={(event) =>
                  setScopeFilter((current) => {
                    const next = new Set(current);
                    if (event.target.checked) next.add(bucket);
                    else next.delete(bucket);
                    return next;
                  })
                }
              />
              {t(CUSTOMER_MASTER_SCOPE_FILTER_LABELS[bucket])}
            </label>
          ))}
        </fieldset>
      ) : null}
      {master && master.corporate_entities.length > 0 && filteredEntities.length === 0 ? (
        <p className="popup-placeholder" role="status">
          {t("No entities match the current scope filter.")}
        </p>
      ) : null}
      {filteredEntities.length > 0 ? (
        <ul className="customer-master-list customer-master-tree" aria-label={t("Customer entities available to this account.")}>
          {buildCustomerEntityTree(filteredEntities).map((node) => (
            <CustomerEntityTreeRow
              key={node.entity.corporate_entity_id}
              node={node}
              depth={0}
              expandedEntityId={expandedEntityId}
              relatedByEntity={relatedByEntity}
              relatedLoading={relatedLoading}
              onToggle={toggleEntity}
              onOpenPost={onOpenPost}
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
          {resolveError ? <ExceptionAlert title={resolveError} /> : null}
          <ul className="customer-master-list">
            {master.source_customer_hints.slice(0, HINT_RENDER_LIMIT).map((hint) => (
              <li key={`${hint.source_system_code ?? "no-system"}:${hint.customer_code ?? "name"}:${hint.customer_name ?? "unknown"}`}>
                <strong>{hint.resolved_entity_name ?? hint.customer_name ?? hint.customer_code ?? t("Unresolved source identifier")}</strong>
                {hint.source_system_code ? <span>{t("Source system")}: {hint.source_system_code}</span> : null}
                {hint.customer_name && hint.customer_code ? <span>{hint.customer_code}</span> : null}
                <span>{t(hint.resolution_status === "customer_identity_promoted" ? "Managed customer" : "Hint only")}</span>
                <span>{t(hint.hint_trust === "low" ? "Weak source hint" : "Source hint")}</span>
                <span>{hint.post_count} {t("posts")}</span>
                {canResolveHints && hint.customer_code && hint.resolution_status !== "customer_identity_promoted" ? (
                  <button
                    onClick={() => void handleResolveHint(hint)}
                    disabled={resolvingHint === `${hint.source_system_code ?? ""}:${hint.customer_code}`}
                  >
                    {resolvingHint === `${hint.source_system_code ?? ""}:${hint.customer_code}` ? t("Resolving...") : t("Resolve")}
                  </button>
                ) : null}
                {hint.related_posts.length > 0 ? (
                  <details>
                    <summary>{t("Related posts")} ({hint.related_posts.length})</summary>
                    <ul aria-label={`${t("Related posts")}: ${hint.customer_name ?? hint.customer_code ?? t("Unresolved source identifier")}`}>
                      {hint.related_posts.map((post) => (
                        <li key={post.post_id}>
                          <CustomerRelatedPostCard
                            postId={post.post_id}
                            postTitle={post.post_title}
                            postBodyExcerpt={post.post_body_excerpt}
                            postBodyTruncated={post.post_body_truncated}
                            onOpenPost={onOpenPost}
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
                <details>
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
                  <details>
                    <summary>{t("Related posts")} ({hint.related_posts.length})</summary>
                    <ul className="related-post-list">
                      {hint.related_posts.map((post) => (
                        <li key={post.post_id}>
                          <CustomerRelatedPostCard
                            postId={post.post_id}
                            postTitle={post.post_title}
                            postBodyExcerpt={post.post_body_excerpt}
                            postBodyTruncated={post.post_body_truncated}
                            onOpenPost={onOpenPost}
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
    </section>
  );
}

type AskAgentExchange = {
  id: string;
  question: string;
  status: "pending" | "complete" | "error";
  response?: AskAgentResponse;
  error?: string;
};

const ASK_AGENT_STARTERS = [
  "What happened between these events?",
  "Who is involved?",
  "What is the next commitment?",
] as const;

function toAskAgentExchanges(conversation: Awaited<ReturnType<typeof fetchAskConversation>>): AskAgentExchange[] {
  return conversation.exchanges.map((exchange) => ({
    id: exchange.turn_id,
    question: exchange.question_text,
    status: "complete",
    response: exchange,
  }));
}

export function AskAgentPanel({
  accessToken,
  onOpenPost,
  anchorPostId,
  anchorPostTitle,
  onClearAnchor,
}: {
  accessToken: string;
  onOpenPost: (postId: string) => void;
  anchorPostId?: string | null;
  anchorPostTitle?: string | null;
  onClearAnchor?: () => void;
}) {
  const [question, setQuestion] = useState("");
  const [exchanges, setExchanges] = useState<AskAgentExchange[]>([]);
  const [conversations, setConversations] = useState<AskConversationSummary[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [historyCursor, setHistoryCursor] = useState<AskConversationCursor | null>(null);
  const [historyLoadingMore, setHistoryLoadingMore] = useState(false);
  const [historyMoreError, setHistoryMoreError] = useState(false);
  const [asking, setAsking] = useState(false);
  const [olderTurnCursor, setOlderTurnCursor] = useState<number | null>(null);
  const [olderTurnsLoading, setOlderTurnsLoading] = useState(false);
  const [olderTurnsError, setOlderTurnsError] = useState(false);
  const exchangeIdRef = useRef(0);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const historyRequestIdRef = useRef(0);
  const historyListRef = useRef<HTMLUListElement>(null);
  const threadRef = useRef<HTMLDivElement>(null);
  const scrollToLatestRef = useRef(false);
  const initialAnchorPostIdRef = useRef(anchorPostId);
  const previousAnchorPostIdRef = useRef(anchorPostId);

  const loadInitialHistory = useCallback(async () => {
    const requestId = ++historyRequestIdRef.current;
    setHistoryLoading(true);
    setHistoryError(null);
    setHistoryMoreError(false);
    setHistoryCursor(null);
    setOlderTurnCursor(null);
    setOlderTurnsError(false);
    try {
      const result = await fetchAskConversations(accessToken);
      if (requestId !== historyRequestIdRef.current) return;
      setConversations(result.conversations);
      setHistoryCursor(result.next_cursor ?? null);
      if (initialAnchorPostIdRef.current) {
        setConversationId(null);
        setExchanges([]);
        return;
      }
      const latest = result.conversations[0];
      if (!latest) {
        setConversationId(null);
        setExchanges([]);
        return;
      }
      const conversation = await fetchAskConversation(accessToken, latest.conversation_id);
      if (requestId !== historyRequestIdRef.current) return;
      setConversationId(conversation.conversation_id);
      setExchanges(toAskAgentExchanges(conversation));
      setOlderTurnCursor(conversation.older_cursor ? Number(conversation.older_cursor) : null);
      setOlderTurnsError(false);
      scrollToLatestRef.current = true;
    } catch {
      if (requestId !== historyRequestIdRef.current) return;
      setHistoryError(t("Conversation history could not be loaded."));
    } finally {
      if (requestId === historyRequestIdRef.current) setHistoryLoading(false);
    }
  }, [accessToken]);

  useEffect(() => {
    void loadInitialHistory();
  }, [loadInitialHistory]);

  useEffect(() => {
    if (anchorPostId && anchorPostId !== previousAnchorPostIdRef.current) {
      setConversationId(null);
      setExchanges([]);
      setQuestion("");
      setOlderTurnCursor(null);
      setOlderTurnsError(false);
    }
    previousAnchorPostIdRef.current = anchorPostId;
  }, [anchorPostId]);

  useEffect(() => {
    if (!scrollToLatestRef.current || exchanges.length === 0) return;
    const thread = threadRef.current;
    if (!thread) return;
    thread.scrollTop = thread.scrollHeight;
    scrollToLatestRef.current = false;
  }, [conversationId, exchanges.length]);

  async function loadMoreConversations() {
    if (!historyCursor || historyLoadingMore || asking) return;
    setHistoryLoadingMore(true);
    setHistoryMoreError(false);
    try {
      const result = await fetchAskConversations(accessToken, historyCursor);
      setConversations((current) => {
        const existingIds = new Set(current.map((item) => item.conversation_id));
        return [
          ...current,
          ...result.conversations.filter((item) => !existingIds.has(item.conversation_id)),
        ];
      });
      setHistoryCursor(result.next_cursor ?? null);
    } catch {
      setHistoryMoreError(true);
    } finally {
      setHistoryLoadingMore(false);
    }
  }

  async function loadOlderExchanges() {
    if (!conversationId || olderTurnCursor === null || olderTurnsLoading || asking) return;
    const thread = threadRef.current;
    const previousHeight = thread?.scrollHeight ?? 0;
    setOlderTurnsLoading(true);
    setOlderTurnsError(false);
    try {
      const conversation = await fetchAskConversation(accessToken, conversationId, olderTurnCursor);
      const olderExchanges = toAskAgentExchanges(conversation);
      setExchanges((current) => {
        const existingIds = new Set(current.map((item) => item.id));
        return [
          ...olderExchanges.filter((item) => !existingIds.has(item.id)),
          ...current,
        ];
      });
      setOlderTurnCursor(conversation.older_cursor ? Number(conversation.older_cursor) : null);
      window.requestAnimationFrame(() => {
        if (thread) thread.scrollTop += thread.scrollHeight - previousHeight;
      });
    } catch {
      setOlderTurnsError(true);
    } finally {
      setOlderTurnsLoading(false);
    }
  }

  async function selectConversation(nextConversationId: string) {
    if (asking) return;
    setHistoryLoading(true);
    setHistoryError(null);
    setOlderTurnsError(false);
    try {
      const conversation = await fetchAskConversation(accessToken, nextConversationId);
      setConversationId(conversation.conversation_id);
      setExchanges(toAskAgentExchanges(conversation));
      setOlderTurnCursor(conversation.older_cursor ? Number(conversation.older_cursor) : null);
      scrollToLatestRef.current = true;
      onClearAnchor?.();
    } catch {
      setHistoryError(t("Conversation history could not be loaded."));
    } finally {
      setHistoryLoading(false);
    }
  }

  function startNewConversation() {
    if (asking) return;
    setConversationId(null);
    setExchanges([]);
    setQuestion("");
    setHistoryError(null);
    setOlderTurnCursor(null);
    setOlderTurnsError(false);
    inputRef.current?.focus();
  }

  function chooseStarter(prompt: string) {
    setQuestion(t(prompt));
    inputRef.current?.focus();
  }

  async function handleAsk() {
    const normalized = question.trim();
    if (!normalized || asking) return;
    const exchangeId = String(++exchangeIdRef.current);
    setExchanges((current) => [...current, { id: exchangeId, question: normalized, status: "pending" }]);
    setQuestion("");
    setAsking(true);
    try {
      const response = await askAgent(accessToken, normalized, conversationId, anchorPostId);
      if (response.conversation_id) {
        setConversationId(response.conversation_id);
        setConversations((current) => [
          {
            conversation_id: response.conversation_id!,
            title: current.find((item) => item.conversation_id === response.conversation_id)?.title ?? normalized.slice(0, 80),
            updated_at: new Date().toISOString(),
            turn_count: (current.find((item) => item.conversation_id === response.conversation_id)?.turn_count ?? 0) + 1,
          },
          ...current.filter((item) => item.conversation_id !== response.conversation_id),
        ]);
      }
      setExchanges((current) => current.map((exchange) => (
        exchange.id === exchangeId ? { ...exchange, status: "complete", response } : exchange
      )));
    } catch (err) {
      setExchanges((current) => current.map((exchange) => (
        exchange.id === exchangeId
          ? { ...exchange, status: "error", error: orchestratorUnavailableMessage(err, t("Ask Agent")) }
          : exchange
      )));
    } finally {
      setAsking(false);
    }
  }

  const showEmptyState = !historyLoading && !historyError && exchanges.length === 0;

  return (
    <section className={`workspace-destination ask-agent-workspace${showEmptyState ? " ask-agent-workspace-empty" : ""}`} aria-labelledby="ask-agent-heading">
      <div className="ask-agent-layout">
        <aside className="ask-agent-history" aria-label={t("Conversation history")}>
          <div className="ask-agent-history-context">
            <div>
              <p className="section-eyebrow">{t("Ask Agent")}</p>
              <strong>{t("Conversation history")}</strong>
            </div>
          </div>
          <div className="ask-agent-history-header">
            <p>{t("Switch between saved questions and source links.")}</p>
            <button type="button" className="ask-agent-new" onClick={startNewConversation} disabled={asking || historyLoading || historyLoadingMore || olderTurnsLoading}>
              {t("New conversation")}
            </button>
          </div>
          {historyLoading && conversations.length === 0 ? (
            <p className="ask-agent-history-loading" role="status">{t("Loading conversation history...")}</p>
          ) : historyError && conversations.length === 0 ? (
            <ExceptionAlert
              title={historyError}
              description={t("Retry loading this conversation, or continue with saved evidence.")}
              retryLabel={t("Retry")}
              onRetry={() => void loadInitialHistory()}
            />
          ) : conversations.length > 0 ? (
            <ul
              ref={historyListRef}
              className="ask-agent-history-list"
              onScroll={(event) => {
                const element = event.currentTarget;
                if (element.scrollHeight - element.scrollTop - element.clientHeight < 96) {
                  void loadMoreConversations();
                }
              }}
            >
              {conversations.map((conversation) => (
                <li key={conversation.conversation_id}>
                  <button
                    type="button"
                    className="ask-agent-history-item"
                    aria-current={conversation.conversation_id === conversationId ? "page" : undefined}
                    onClick={() => void selectConversation(conversation.conversation_id)}
                    disabled={historyLoading || historyLoadingMore || olderTurnsLoading || asking}
                  >
                    <strong>{conversation.title}</strong>
                    <span>{conversation.turn_count} {t("questions")}</span>
                  </button>
                </li>
              ))}
              {historyCursor ? (
                <li className="ask-agent-history-load-status">
                  {historyLoadingMore ? (
                    <p role="status">{t("Loading older conversations...")}</p>
                  ) : historyMoreError ? (
                    <button type="button" className="ask-agent-retry" onClick={() => void loadMoreConversations()}>
                      {t("Retry loading history")}
                    </button>
                  ) : (
                    <p role="status">{t("Scroll to load older conversations")}</p>
                  )}
                </li>
              ) : null}
            </ul>
          ) : (
            <div className="ask-agent-history-empty">
              <strong>{t("No saved conversations yet.")}</strong>
              <span>{t("Ask a question to save your first conversation.")}</span>
            </div>
          )}
        </aside>

        <div className={`ask-agent-main${showEmptyState ? " ask-agent-main-empty" : ""}`}>
          <header className="ask-agent-header">
            <div className="ask-agent-header-topline">
              <div>
                <p className="section-eyebrow">{t("Evidence-grounded questions")}</p>
                <h2 id="ask-agent-heading">{t("Ask Agent")}</h2>
              </div>
              <span className="ask-agent-scope">{t("Authorized evidence")}</span>
            </div>
            <p className="workspace-destination-intro">{t("Questions use authorized posts and their evidence.")}</p>
            {anchorPostId ? (
              <p className="post-meta" role="status">
                {tf("Starting evidence: {post}", {
                  post: anchorPostTitle ?? anchorPostId.slice(0, 8),
                })}{" "}
                {onClearAnchor ? (
                  <button type="button" onClick={onClearAnchor}>
                    {t("Use all authorized evidence")}
                  </button>
                ) : null}
              </p>
            ) : null}
          </header>

      <div
        ref={threadRef}
        className="ask-agent-thread"
        role="log"
        aria-label={t("Conversation")}
        aria-live="polite"
        aria-busy={asking || historyLoading || olderTurnsLoading}
        onScroll={(event) => {
          if (event.currentTarget.scrollTop < 120) void loadOlderExchanges();
        }}
      >
        {historyError ? (
          <ExceptionAlert
            title={historyError}
            description={t("Retry loading this conversation, or continue with saved evidence.")}
            retryLabel={t("Retry")}
            onRetry={() => void loadInitialHistory()}
          />
        ) : null}
        {historyLoading && exchanges.length === 0 ? <p className="ask-agent-history-loading">{t("Loading...")}</p> : null}
        {olderTurnsLoading ? <p className="ask-agent-history-loading" role="status">{t("Loading older questions...")}</p> : null}
        {olderTurnsError ? (
          <button type="button" className="ask-agent-retry ask-agent-thread-retry" onClick={() => void loadOlderExchanges()}>
            {t("Retry loading older questions")}
          </button>
        ) : null}
        {exchanges.length === 0 ? (
          <div className="ask-agent-empty" hidden={!showEmptyState}>
            <p className="ask-agent-empty-kicker">{t("Evidence workspace")}</p>
            <h3>{t("Start with a question about the evidence")}</h3>
            <p>{t("Ask about an event, decision, or source post.")}</p>
            <div className="ask-agent-starter-group">
              <p className="ask-agent-starter-label">{t("Suggested questions")}</p>
              <div className="ask-agent-starters" aria-label={t("Suggested questions")}>
              {ASK_AGENT_STARTERS.map((prompt) => (
                <button key={prompt} type="button" className="ask-agent-starter" onClick={() => chooseStarter(prompt)}>
                  {t(prompt)}
                </button>
              ))}
              </div>
            </div>
          </div>
        ) : exchanges.map((exchange) => {
          const response = exchange.response;
          return (
            <article className="ask-agent-turn" key={exchange.id}>
              <div className="ask-agent-message-row ask-agent-user-row">
                <span className="ask-agent-avatar ask-agent-user-avatar" aria-hidden="true">U</span>
                <div className="ask-agent-message ask-agent-user-message">
                  <p className="ask-agent-message-label">{t("You")}</p>
                  <p>{exchange.question}</p>
                </div>
              </div>
              <div className="ask-agent-message-row ask-agent-assistant-row">
                <span className="ask-agent-avatar ask-agent-assistant-avatar" aria-hidden="true">LW</span>
                <div className="ask-agent-message ask-agent-assistant-message">
                  <p className="ask-agent-message-label">{t("Ask Agent")}</p>
                  {exchange.status === "pending" ? <p className="ask-agent-pending">{t("Thinking...")}</p> : null}
                  {exchange.status === "error" && exchange.error ? (
                    <ExceptionAlert title={exchange.error} />
                  ) : null}
                  {response?.answer_text ? <p>{response.answer_text}</p> : null}
                  {response?.next_action ? <p className="post-meta">{t(response.next_action)}</p> : null}
                  {response?.cited_posts && response.cited_posts.length > 0 ? (
                    <section className="ask-agent-citations" aria-label={t("Cited posts")}>
                      <h4>{t("Cited posts")}</h4>
                      <ul className="ask-agent-citation-list">
                        {response.cited_posts.map((post) => (
                          <li key={post.post_id}>
                            <button className="ask-agent-citation" onClick={() => onOpenPost(post.post_id)}>
                              <strong>{post.post_title}</strong>
                              <span>{t("Open source")}</span>
                            </button>
                            {response.cited_post_evidence?.find((item) => item.post_id === post.post_id)?.facts.length ? (
                              <ul className="post-evidence-list" aria-label={t("Evidence facts")}>
                                {response.cited_post_evidence
                                  .find((item) => item.post_id === post.post_id)
                                  ?.facts.map((fact, index) => (
                                    <li key={fact.kind + ":" + fact.text + ":" + index}>
                                      <span>{chatEvidenceKindLabel(fact.kind)}</span>
                                      <span>{fact.text}</span>
                                    </li>
                                  ))}
                              </ul>
                            ) : null}
                          </li>
                        ))}
                      </ul>
                    </section>
                  ) : null}
                </div>
              </div>
            </article>
          );
        })}
      </div>

      <form
        className="ask-agent-composer"
        onSubmit={(event) => {
          event.preventDefault();
          void handleAsk();
        }}
      >
        <div className="ask-agent-composer-label-row">
          <label className="ask-agent-composer-label" htmlFor="ask-agent-input">{t("Ask a question")}</label>
          <span>{t("Answers cite authorized posts when available.")}</span>
        </div>
        <div className="ask-agent-composer-field">
          <textarea
            id="ask-agent-input"
            ref={inputRef}
            aria-label={t("Ask a question")}
            aria-describedby="ask-agent-input-help"
            placeholder={t("What happened between these events?")}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (event.nativeEvent.isComposing) return;
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void handleAsk();
              }
            }}
            rows={1}
          />
          <button className="ask-agent-send" type="submit" aria-label={t("Ask")} disabled={asking || !question.trim()}>
            <SendIcon />
          </button>
        </div>
        <p id="ask-agent-input-help" className="ask-agent-composer-help">{t("Enter to send. Shift+Enter for a new line.")}</p>
      </form>
        </div>
      </div>
    </section>
  );
}

const WORKSPACE_QUERY_PARAM = "workspace";
const WORKSPACE_DESTINATIONS: readonly WorkspaceDestination[] = [
  "board",
  "customers",
  "calendar",
  "ask",
  "admin",
];

function workspaceDestinationFromLocation(
  location: Pick<Location, "search"> = window.location,
): WorkspaceDestination {
  const candidate = new URLSearchParams(location.search).get(WORKSPACE_QUERY_PARAM);
  return WORKSPACE_DESTINATIONS.includes(candidate as WorkspaceDestination)
    ? (candidate as WorkspaceDestination)
    : "board";
}

function updateWorkspaceLocation(
  destination: WorkspaceDestination,
  mode: "push" | "replace" = "push",
): void {
  if (typeof window === "undefined") return;
  const url = new URL(window.location.href);
  if (destination === "board") {
    url.searchParams.delete(WORKSPACE_QUERY_PARAM);
  } else {
    url.searchParams.set(WORKSPACE_QUERY_PARAM, destination);
  }
  const nextUrl = `${url.pathname}${url.search}${url.hash}`;
  const currentUrl = `${window.location.pathname}${window.location.search}${window.location.hash}`;
  if (nextUrl === currentUrl) return;
  window.history[mode === "replace" ? "replaceState" : "pushState"]({}, "", nextUrl);
}

const DEFAULT_TENANT_CONFIG: TenantConfig = {
  brandName: "LineageWeave",
  systemName: "LineageWeave",
  copyrightYear: 2026,
  copyrightHolder: "LineageWeave",
};

export default function App({ showLabPanels = false }: { showLabPanels?: boolean } = {}) {
  useLocale();
  const [tenantConfig, setTenantConfig] = useState<TenantConfig>(DEFAULT_TENANT_CONFIG);
  const auth = useAuth();
  const [destination, setDestination] = useState<WorkspaceDestination>(() => workspaceDestinationFromLocation());
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [siteMapOpen, setSiteMapOpen] = useState(false);
  const [globalSearchOpen, setGlobalSearchOpen] = useState(false);
  const [globalSearchValue, setGlobalSearchValue] = useState("");
  const [searchFocusRequest, setSearchFocusRequest] = useState(0);
  const [globalSearchRequest, setGlobalSearchRequest] = useState<{ id: number; query: string } | null>(null);
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [boardAdminTool, setBoardAdminTool] = useState<AdminBoardTool | null>(null);
  const mobileDrawerRef = useRef<HTMLDialogElement>(null);
  const mobileDrawerTriggerRef = useRef<HTMLButtonElement>(null);
  const [postToOpen, setPostToOpen] = useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    return new URLSearchParams(window.location.search).get("post");
  });
  const [askAnchor, setAskAnchor] = useState<{ postId: string; postTitle: string | null } | null>(
    () => {
      if (typeof window === "undefined") return null;
      const params = new URLSearchParams(window.location.search);
      const postId = params.get("post");
      return params.get(WORKSPACE_QUERY_PARAM) === "ask" && postId
        ? { postId, postTitle: null }
        : null;
    },
  );
  // Test-only compatibility for legacy analysis-panel coverage; this prop
  // never forces the panels open outside Vitest. In a real build the
  // advanced-review section (ADR 0037) is gated on PostList's own
  // post_admin check (`canRebuild`), not on this caller-supplied prop.
  const testOnlyLabPanels = import.meta.env.MODE === "test" && showLabPanels;
  const accessToken = auth.user?.access_token;
  const canAdmin = Boolean(currentUser?.permission_codes.includes("post_admin"));
  const activeDestination = destination === "admin" && !canAdmin ? "board" : destination;
  const changeDestination = (nextDestination: WorkspaceDestination) => {
    if (nextDestination === "admin" && !canAdmin) return;
    setDestination(nextDestination);
    updateWorkspaceLocation(nextDestination);
    if (nextDestination !== "board") setBoardAdminTool(null);
    setMobileMenuOpen(false);
    setSiteMapOpen(false);
    setGlobalSearchOpen(false);
    if (nextDestination !== "board") setSearchFocusRequest(0);
  };

  useEffect(() => {
    const handlePopState = () => {
      const nextDestination = workspaceDestinationFromLocation();
      const postId = new URLSearchParams(window.location.search).get("post");
      setDestination(nextDestination);
      setPostToOpen(nextDestination === "board" ? postId : null);
      setAskAnchor(
        nextDestination === "ask" && postId ? { postId, postTitle: null } : null,
      );
      setBoardAdminTool(null);
      setMobileMenuOpen(false);
      setSiteMapOpen(false);
      setGlobalSearchOpen(false);
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  useEffect(() => {
    if (currentUser && destination === "admin" && !canAdmin) {
      setDestination("board");
      updateWorkspaceLocation("board", "replace");
    }
  }, [canAdmin, currentUser, destination]);

  const openAdminBoardTool = (tool: AdminBoardTool) => {
    setBoardAdminTool(tool);
    changeDestination("board");
  };

  function openGlobalSearch() {
    setMobileMenuOpen(false);
    setSiteMapOpen(false);
    setGlobalSearchOpen(true);
  }

  function submitGlobalSearch(query: string) {
    const normalized = query.trim();
    if (!normalized) return;
    setGlobalSearchOpen(false);
    setGlobalSearchValue("");
    setGlobalSearchRequest((current) => ({
      id: (current?.id ?? 0) + 1,
      query: normalized,
    }));
    changeDestination("board");
    setSearchFocusRequest((request) => request + 1);
  }

  useEffect(() => {
    if (!siteMapOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setSiteMapOpen(false);
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [siteMapOpen]);

  useEffect(() => {
    const dialog = mobileDrawerRef.current;
    if (!dialog) return;
    if (mobileMenuOpen) {
      if (!dialog.open) {
        if (typeof dialog.showModal === "function") dialog.showModal();
        else dialog.setAttribute("open", "");
      }
      dialog.querySelector<HTMLButtonElement>(".mobile-drawer-close")?.focus();
    } else if (dialog.open) {
      if (typeof dialog.close === "function") dialog.close();
      else dialog.removeAttribute("open");
      mobileDrawerTriggerRef.current?.focus();
    }
  }, [mobileMenuOpen]);

  useEffect(() => {
    if (accessToken) {
      fetchTenantConfig(accessToken).then((config) => {
        setTenantConfig({ ...DEFAULT_TENANT_CONFIG, ...config });
      }).catch(console.error);
    }
  }, [accessToken]);

  useEffect(() => {
    if (!accessToken) return;
    const nextDestination = workspaceDestinationFromLocation();
    const postId = new URLSearchParams(window.location.search).get("post");
    setDestination(nextDestination);
    setPostToOpen(nextDestination === "board" ? postId : null);
    setAskAnchor(nextDestination === "ask" && postId ? { postId, postTitle: null } : null);
  }, [accessToken]);

  useEffect(() => {
    if (!accessToken) return;
    let active = true;
    fetchMe(accessToken)
      .then((member) => {
        if (!active) return;
        setCurrentUser(member);
        if (isSupportedLocale(member.preferred_locale)) setLocale(member.preferred_locale);
      })
      .catch(() => {
        if (active) setCurrentUser(null);
      });
    return () => {
      active = false;
    };
  }, [accessToken]);

  if (auth.isLoading) {
    return <p>{t("Loading authentication state...")}</p>;
  }

  if (auth.error) {
    return (
      <div className="app-shell">
        <main className="login-screen">
          <div className="login-card">
            <ExceptionAlert
              title={t("Sign-in could not be completed.")}
              description={t("Log in again to open the workspace.")}
              retryLabel={t("Log in")}
              onRetry={() => {
                const returnUrl = returnUrlFromLocation();
                rememberOidcReturnUrl(returnUrl);
                void auth.signinRedirect({ state: { returnUrl } });
              }}
            />
          </div>
        </main>
      </div>
    );
  }

  if (!auth.isAuthenticated) {
    return (
      <div className="app-shell">
        <main className="login-screen">
          <div className="login-card">
            <div className="login-header">
              <p className="login-brand">{tenantConfig.brandName}</p>
              <h1>{tenantConfig.systemName}</h1>
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
            <span className="app-footer-logo">{tenantConfig.brandName}</span>
          </div>
          <div className="app-footer-copyright">
            <p>Copyright &copy; {tenantConfig.copyrightYear} by {tenantConfig.copyrightHolder}. All rights reserved.</p>
          </div>
        </footer>
      </div>
    );
  }

  if (!accessToken) {
    return (
      <div className="app-shell">
        <main className="login-screen">
          <div className="login-card">
            <ExceptionAlert
              title={t("Authenticated, but no access token was returned.")}
              description={t("Log in again to open the workspace.")}
              retryLabel={t("Log in")}
              onRetry={() => {
                const returnUrl = returnUrlFromLocation();
                rememberOidcReturnUrl(returnUrl);
                void auth.signinRedirect({ state: { returnUrl } });
              }}
            />
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <a
        href="#main-content"
        className="skip-link"
        onClick={(event) => {
          event.preventDefault();
          document.getElementById("main-content")?.focus();
        }}
      >
        {t("Skip to main content")}
      </a>
      <header className="app-header">
        <div className="app-header-logo">
          <span className="app-header-brand">{tenantConfig.brandName}</span>
          <h1 className="app-header-title">{tenantConfig.systemName}</h1>
        </div>
        <button
          ref={mobileDrawerTriggerRef}
          type="button"
          className="mobile-drawer-trigger"
          aria-label={
            mobileMenuOpen ? `${t("Close")} ${t("Workspace navigation")}` : t("Open navigation")
          }
          aria-expanded={mobileMenuOpen}
          aria-controls="mobile-workspace-navigation"
          onClick={() => setMobileMenuOpen((open) => !open)}
        >
          <MenuIcon />
        </button>
        <div className="app-header-top-menu">
          <AuthorizedScope affiliations={currentUser?.account_affiliations} />
          <span className="app-user-profile">{auth.user?.profile.preferred_username}</span>
          <LanguageSwitcher accessToken={accessToken} />
          <GlobalSearch
            open={globalSearchOpen}
            value={globalSearchValue}
            searchLabel={t("Search")}
            inputLabel={t("Search semantic evidence")}
            closeLabel={t("Close")}
            helpText={t("Search includes post text and semantic evidence.")}
            onOpen={openGlobalSearch}
            onClose={() => setGlobalSearchOpen(false)}
            onChange={setGlobalSearchValue}
            onSubmit={submitGlobalSearch}
          />
          <SiteMapUtility
            destination={activeDestination}
            onChange={changeDestination}
            showAdmin={canAdmin}
            open={siteMapOpen}
            onToggle={() => setSiteMapOpen((open) => !open)}
          />
          <button className="btn-secondary" onClick={() => auth.signoutRedirect()}>{t("Log out")}</button>
        </div>
      </header>
      <WorkspaceNav destination={activeDestination} onChange={changeDestination} showAdmin={canAdmin} />
      <dialog
        ref={mobileDrawerRef}
        className="mobile-drawer-backdrop"
        aria-label={t("Workspace navigation")}
        onCancel={(event) => {
          event.preventDefault();
          setMobileMenuOpen(false);
        }}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            event.preventDefault();
            setMobileMenuOpen(false);
          }
        }}
        onClick={(event) => {
          if (event.target === event.currentTarget) setMobileMenuOpen(false);
        }}
      >
          <aside
            className="mobile-drawer"
          >
            <button
              type="button"
              className="mobile-drawer-close"
              aria-label={t("Close")}
              onClick={() => setMobileMenuOpen(false)}
            >
              <CloseIcon />
            </button>
            <WorkspaceNav
              id="mobile-workspace-navigation"
              destination={activeDestination}
              onChange={changeDestination}
              showAdmin={canAdmin}
              drawer
            />
          </aside>
      </dialog>
      <main id="main-content" tabIndex={-1}>
        {activeDestination === "board" ? (
          <PostList
            accessToken={accessToken}
            showLabPanels={testOnlyLabPanels}
            postIdToOpen={postToOpen}
            onPostOpened={() => setPostToOpen(null)}
            onAskPost={(postId, postTitle) => {
              setAskAnchor({ postId, postTitle });
              changeDestination("ask");
            }}
            focusSearchRequest={searchFocusRequest}
            onSearchFocusHandled={() => setSearchFocusRequest(0)}
            globalSearchRequest={globalSearchRequest}
            onGlobalSearchHandled={() => setGlobalSearchRequest(null)}
            adminTool={boardAdminTool}
            onAdminToolHandled={() => setBoardAdminTool(null)}
          />
        ) : null}
        {activeDestination === "customers" ? (
          <CustomerMasterPanel
            accessToken={accessToken}
            onOpenPost={(postId) => {
              setPostToOpen(postId);
              changeDestination("board");
            }}
          />
        ) : null}
        {activeDestination === "calendar" ? (
          <CalendarPanel
            accessToken={accessToken}
            onSelectPost={(postId) => {
              setPostToOpen(postId);
              changeDestination("board");
            }}
          />
        ) : null}
        {activeDestination === "ask" ? (
          <AskAgentPanel
            accessToken={accessToken}
            anchorPostId={askAnchor?.postId}
            anchorPostTitle={askAnchor?.postTitle}
            onClearAnchor={() => {
              setAskAnchor(null);
              const url = new URL(window.location.href);
              url.searchParams.delete("post");
              window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
            }}
            onOpenPost={(postId) => {
              setPostToOpen(postId);
              changeDestination("board");
            }}
          />
        ) : null}
        {activeDestination === "admin" ? <AdminPanel currentTenantConfig={tenantConfig} onTenantConfigChange={setTenantConfig} accessToken={accessToken} currentUser={currentUser} onNavigate={changeDestination} onOpenBoardTool={openAdminBoardTool} /> : null}
      </main>
      <footer className="app-footer" role="contentinfo">
        <div className="app-footer-title">
          <span className="app-footer-logo">{tenantConfig.brandName}</span>
        </div>
        <div className="app-footer-copyright">
          <p>Copyright &copy; {tenantConfig.copyrightYear} by {tenantConfig.copyrightHolder}. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
