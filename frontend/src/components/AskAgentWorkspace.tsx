import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import {
  askAgent,
  BackendError,
  type AskAgentResponse,
} from "../api";
import { t } from "../i18n";
import "./AskAgentWorkspace.css";

export const GLOBAL_ASK_SESSION_STORAGE_KEY = "lineageweave.globalAskSessionId";

const CHAT_EVIDENCE_KIND_LABELS: Record<string, string> = {
  source_field: "Source field hint",
  semantic_project: "Semantic project",
  semantic_role: "Semantic role",
  semantic_keyman: "Semantic Keyman",
};

function chatEvidenceKindLabel(kind: string): string {
  return t(CHAT_EVIDENCE_KIND_LABELS[kind] ?? "Evidence");
}

function safeSessionStorage(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

function readSavedSession(storage: Storage | null): string | undefined {
  try {
    return storage?.getItem(GLOBAL_ASK_SESSION_STORAGE_KEY) || undefined;
  } catch {
    return undefined;
  }
}

function saveSession(storage: Storage | null, sessionId: string): void {
  try {
    storage?.setItem(GLOBAL_ASK_SESSION_STORAGE_KEY, sessionId);
  } catch {
    // A blocked browser storage policy must not block an evidence-grounded answer.
  }
}

function clearSession(storage: Storage | null): void {
  try {
    storage?.removeItem(GLOBAL_ASK_SESSION_STORAGE_KEY);
  } catch {
    // The next request can still proceed without the stale session identifier.
  }
}

function askAgentErrorMessage(error: unknown): string {
  if (error instanceof BackendError && error.status === 503) {
    return `${t("Ask Agent")} ${t("is temporarily unavailable.")} ${t("Saved evidence is still available.")}`;
  }
  return String(error);
}

function askCitedNextAction(answer: AskAgentResponse): string {
  if (answer.grounding_status === "fully_cutoff_grounded") {
    return (
      answer.next_action ||
      "This answer is fully grounded at the requested cutoff. Open a cited post to compare the retained body."
    );
  }
  if (answer.grounding_status === "partially_cutoff_grounded") {
    return (
      answer.next_action ||
      "This answer is only partly grounded at the requested cutoff. Open a cited post to see which historical bodies were retained."
    );
  }
  return "Authorized cited posts are current. Open a cited post to read Event Lineage.";
}

function toKnowledgeCutoffIso(value: string): string | undefined {
  const trimmed = value.trim();
  if (!trimmed) return undefined;
  const parsed = new Date(trimmed);
  return Number.isNaN(parsed.getTime()) ? undefined : parsed.toISOString();
}

export type AskAgentRequest = (
  accessToken: string,
  question: string,
  sessionId?: string,
  knowledgeCutoff?: string,
) => Promise<AskAgentResponse>;

export interface AskAgentWorkspaceViewProps {
  question: string;
  knowledgeCutoff: string;
  answer: AskAgentResponse | null;
  error: string | null;
  asking: boolean;
  onQuestionChange: (question: string) => void;
  onKnowledgeCutoffChange: (knowledgeCutoff: string) => void;
  onSubmit: () => void;
  onOpenPost: (postId: string) => void;
}

export function AskAgentWorkspaceView({
  question,
  knowledgeCutoff,
  answer,
  error,
  asking,
  onQuestionChange,
  onKnowledgeCutoffChange,
  onSubmit,
  onOpenPost,
}: AskAgentWorkspaceViewProps) {
  const answerRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (answer && !asking) answerRef.current?.focus();
  }, [answer, asking]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!asking && question.trim()) onSubmit();
  }

  function handleQuestionKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) return;
    event.preventDefault();
    event.currentTarget.form?.requestSubmit();
  }

  return (
    <section className="buyer-destination ask-agent-workspace" aria-labelledby="ask-agent-heading">
      <header className="ask-agent-header">
        <div>
          <p className="section-eyebrow">{t("Evidence-grounded questions")}</p>
          <h2 id="ask-agent-heading">{t("Ask Agent")}</h2>
          <p className="buyer-destination-intro">
            {t("Questions use authorized posts and their evidence.")}
          </p>
        </div>
        <p className="ask-agent-scope">{t("Authorized posts in this board.")}</p>
      </header>

      <div className="ask-agent-layout">
        <form className="ask-agent-composer" onSubmit={handleSubmit}>
          <label className="ask-agent-source">
            <span>{t("Ask a question")}</span>
            <textarea
              aria-label={t("Ask a question")}
              value={question}
              onChange={(event) => onQuestionChange(event.target.value)}
              onKeyDown={handleQuestionKeyDown}
              rows={7}
              disabled={asking}
            />
          </label>
          <label className="ask-agent-source">
            <span>{t("Knowledge cutoff (optional)")}</span>
            <input
              type="datetime-local"
              aria-label={t("Knowledge cutoff (optional)")}
              value={knowledgeCutoff}
              onChange={(event) => onKnowledgeCutoffChange(event.target.value)}
              disabled={asking}
            />
          </label>
          <div className="ask-agent-composer-footer">
            <p className="post-meta">
              {t("Questions use authorized posts and their evidence.")}
            </p>
            <button
              className="ask-agent-submit"
              type="submit"
              disabled={asking || !question.trim()}
            >
              {asking ? t("Asking...") : t("Ask")}
            </button>
          </div>
        </form>

        <div className="ask-agent-output" aria-live="polite">
          {error ? (
            <section className="ask-agent-state ask-agent-error" role="alert">
              <h3>{t("Answer")}</h3>
              <p className="error">{error}</p>
            </section>
          ) : null}

          {asking ? (
            <section className="ask-agent-state ask-agent-loading" role="status">
              <h3>{t("Answer")}</h3>
              <p>{t("Asking...")}</p>
            </section>
          ) : null}

          {!asking && !error && !answer ? (
            <section className="ask-agent-state ask-agent-empty" role="status">
              <h3>{t("Answer")}</h3>
              <p>{t("Questions use authorized posts and their evidence.")}</p>
            </section>
          ) : null}

          {!asking && answer ? (
            <article
              ref={answerRef}
              className="ask-agent-answer"
              aria-label={t("Answer")}
              tabIndex={-1}
            >
              <header className="ask-agent-answer-header">
                <p className="section-eyebrow">{t("Answer")}</p>
                <h3>{t("Answer")}</h3>
              </header>
              {answer.answer_text ? <p className="ask-agent-answer-text">{answer.answer_text}</p> : null}
              {answer.next_action && !(answer.cited_posts && answer.cited_posts.length > 0) ? (
                <p className="board-next-action" aria-label={t("Next action")}>
                  {t(answer.next_action)}
                </p>
              ) : null}

              {answer.timeline && answer.timeline.length > 0 ? (
                <section className="ask-agent-result-section">
                  <h4>{t("Event Lineage timeline")}</h4>
                  <ol className="ask-agent-timeline" aria-label={t("Event Lineage timeline")}>
                    {answer.timeline.map((event) => (
                      <li key={event.post_id}>
                        <button
                          type="button"
                          className="ask-agent-source-card"
                          aria-label={`${t("Open timeline post:")} ${event.post_title}`}
                          onClick={() => onOpenPost(event.post_id)}
                        >
                          <span>{event.post_title}</span>
                          {event.occurred_at ? (
                            <time dateTime={event.occurred_at}>{event.occurred_at}</time>
                          ) : null}
                        </button>
                      </li>
                    ))}
                  </ol>
                </section>
              ) : null}

              {answer.limitations && answer.limitations.length > 0 ? (
                <section
                  className="ask-agent-result-section"
                  aria-label={t("Historical evidence limitations")}
                >
                  <h4>{t("Historical evidence limitations")}</h4>
                  <ul className="post-evidence-list">
                    {answer.limitations.map((limitation) => {
                      const timelinePost = answer.timeline?.find(
                        (event) => event.post_id === limitation.post_id,
                      );
                      return timelinePost ? (
                        <li key={limitation.post_id}>
                          <strong>{timelinePost.post_title}</strong>: {t("Historical body unavailable for this cited post. The live body was not used.")}
                        </li>
                      ) : null;
                    })}
                  </ul>
                </section>
              ) : null}

              {answer.cited_posts && answer.cited_posts.length > 0 ? (
                <section className="ask-agent-result-section">
                  <p className="board-next-action" role="status" aria-label={t("Next action")}>
                    {t(askCitedNextAction(answer))}
                  </p>
                  <h4>{t("Cited posts")}</h4>
                  <ul className="ask-agent-citations">
                    {answer.cited_posts.map((post) => {
                      const evidence = answer.cited_post_evidence?.find(
                        (item) => item.post_id === post.post_id,
                      );
                      return (
                        <li key={post.post_id} className="ask-agent-citation-card">
                          <button
                            type="button"
                            className="ask-agent-source-card"
                            aria-label={`${t("Open cited post:")} ${post.post_title}`}
                            onClick={() => onOpenPost(post.post_id)}
                          >
                            <span>{post.post_title}</span>
                          </button>
                          {post.historical_body_unavailable ? (
                            <p className="post-meta">
                              {t("Historical body unavailable for this cited post. The live body was not used.")}
                            </p>
                          ) : null}
                          {post.live_after_cutoff ? (
                            <p className="post-meta">{t("This live source changed after the cutoff.")}</p>
                          ) : null}
                          {evidence?.facts.length ? (
                            <ul className="post-evidence-list" aria-label={t("Evidence facts")}>
                              {evidence.facts.map((fact, index) => (
                                <li key={`${fact.kind}:${fact.text}:${index}`}>
                                  <span>{chatEvidenceKindLabel(fact.kind)}</span>
                                  <span>{fact.text}</span>
                                </li>
                              ))}
                            </ul>
                          ) : null}
                        </li>
                      );
                    })}
                  </ul>
                </section>
              ) : null}
            </article>
          ) : null}
        </div>
      </div>
    </section>
  );
}

export function AskAgentWorkspace({
  accessToken,
  onOpenPost,
  request = askAgent,
  storage = safeSessionStorage(),
}: {
  accessToken: string;
  onOpenPost: (postId: string) => void;
  request?: AskAgentRequest;
  storage?: Storage | null;
}) {
  const [question, setQuestion] = useState("");
  const [knowledgeCutoff, setKnowledgeCutoff] = useState("");
  const [answer, setAnswer] = useState<AskAgentResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [asking, setAsking] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>(() => readSavedSession(storage));
  const requestOrdinal = useRef(0);

  async function handleAsk() {
    const normalized = question.trim();
    if (!normalized || asking) return;
    const normalizedKnowledgeCutoff = toKnowledgeCutoffIso(knowledgeCutoff);
    const ordinal = ++requestOrdinal.current;
    setAsking(true);
    setError(null);
    setAnswer(null);
    try {
      let nextAnswer: AskAgentResponse;
      try {
        nextAnswer = normalizedKnowledgeCutoff
          ? await request(accessToken, normalized, sessionId, normalizedKnowledgeCutoff)
          : await request(accessToken, normalized, sessionId);
      } catch (requestError) {
        if (!(requestError instanceof BackendError) || requestError.status !== 404 || !sessionId) {
          throw requestError;
        }
        setSessionId(undefined);
        clearSession(storage);
        nextAnswer = normalizedKnowledgeCutoff
          ? await request(accessToken, normalized, undefined, normalizedKnowledgeCutoff)
          : await request(accessToken, normalized);
      }
      if (ordinal !== requestOrdinal.current) return;
      setAnswer(nextAnswer);
      setSessionId(nextAnswer.session_id);
      saveSession(storage, nextAnswer.session_id);
    } catch (requestError) {
      if (ordinal !== requestOrdinal.current) return;
      setAnswer(null);
      setError(askAgentErrorMessage(requestError));
    } finally {
      if (ordinal === requestOrdinal.current) setAsking(false);
    }
  }

  return (
    <AskAgentWorkspaceView
      question={question}
      knowledgeCutoff={knowledgeCutoff}
      answer={answer}
      error={error}
      asking={asking}
      onQuestionChange={setQuestion}
      onKnowledgeCutoffChange={setKnowledgeCutoff}
      onSubmit={() => void handleAsk()}
      onOpenPost={onOpenPost}
    />
  );
}
