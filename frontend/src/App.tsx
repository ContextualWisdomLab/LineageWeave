import { useEffect, useState } from "react";
import { useAuth } from "react-oidc-context";
import {
  askPostChat,
  createPostTicket,
  fetchLineageGraph,
  fetchMe,
  fetchPost,
  fetchPostCounterparties,
  fetchPostKeymen,
  fetchPostLineage,
  fetchPostSummary,
  fetchPostTickets,
  fetchPosts,
  rebuildLineage,
  updateTicketStatus,
  type ChatAnswer,
  type Counterparty,
  type IssueTicket,
  type LineageGraph,
  type Keyman,
  type LinkedPostRef,
  type PostAiSummary,
  type PostDetail,
  type PostLineage,
  type PostSummary,
} from "./api";
import { LineageDag } from "./LineageDag";
import "./App.css";

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
          <p className="post-body">{post.post_body}</p>
        </>
      )}
    </div>
  );
}

function ChatPanel({ postId, accessToken }: { postId: string; accessToken: string }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<ChatAnswer | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [evidencePostId, setEvidencePostId] = useState<string | null>(null);

  async function handleAsk() {
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await askPostChat(accessToken, postId, question);
      setAnswer(result);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="popup-section chat-section">
      <h3>Ask about this lineage</h3>
      <div className="chat-input-row">
        <input
          type="text"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={(event) => event.key === "Enter" && handleAsk()}
          placeholder="What happened between these events?"
        />
        <button onClick={handleAsk} disabled={loading || !question.trim()}>
          {loading ? "Asking..." : "Ask"}
        </button>
      </div>
      {error && <p className="error">{error}</p>}
      {answer && (
        <div className="chat-answer">
          <p>{answer.answer_text}</p>
          {answer.cited_post_ids.length > 0 && (
            <div className="chat-citations">
              <span>Sources: </span>
              {answer.cited_post_ids.map((citedId) => (
                <button
                  key={citedId}
                  className="citation-chip"
                  onClick={() => setEvidencePostId(citedId)}
                >
                  {citedId.slice(0, 8)}
                </button>
              ))}
            </div>
          )}
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

function EventLineageSection({ lineage }: { lineage: PostLineage | null }) {
  if (!lineage) return <p>Loading lineage...</p>;
  if (lineage.direct.length === 0 && lineage.indirect.length === 0) {
    return <p className="lineage-empty">No linked posts yet.</p>;
  }
  const renderLink = (post: LinkedPostRef, kind: "direct" | "indirect") => (
    <li key={post.post_id} className={`lineage-link lineage-link-${kind}`}>
      <span className="lineage-badge">{kind === "direct" ? "직접" : "간접"}</span>
      {post.post_title}
    </li>
  );
  return (
    <ul className="lineage-list">
      {lineage.direct.map((post) => renderLink(post, "direct"))}
      {lineage.indirect.map((post) => renderLink(post, "indirect"))}
    </ul>
  );
}

const TICKET_STATUS_OPTIONS = ["open", "in_progress", "closed"];

function IssueTicketPanel({ postId, accessToken }: { postId: string; accessToken: string }) {
  const [tickets, setTickets] = useState<IssueTicket[] | null>(null);
  const [newTitle, setNewTitle] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  function reload() {
    fetchPostTickets(accessToken, postId)
      .then((r) => setTickets(r.tickets))
      .catch(() => setTickets([]));
  }

  useEffect(() => {
    setTickets(null);
    fetchPostTickets(accessToken, postId)
      .then((r) => setTickets(r.tickets))
      .catch(() => setTickets([]));
  }, [postId, accessToken]);

  async function handleCreate() {
    if (!newTitle.trim()) return;
    setCreating(true);
    setError(null);
    try {
      await createPostTicket(accessToken, postId, newTitle, "open");
      setNewTitle("");
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

  return (
    <section className="popup-section">
      <h3>이슈 티켓 (Issue tickets)</h3>
      {error && <p className="error">{error}</p>}
      {tickets === null ? (
        <p>Loading tickets...</p>
      ) : tickets.length === 0 ? (
        <p className="popup-placeholder">No tickets yet.</p>
      ) : (
        <ul className="ticket-list">
          {tickets.map((ticket) => (
            <li key={ticket.issue_ticket_id} className="ticket-list-item">
              <span className="ticket-title">{ticket.ticket_title}</span>
              <select
                value={ticket.ticket_status_code}
                onChange={(event) => handleStatusChange(ticket, event.target.value)}
                aria-label={`Status for ${ticket.ticket_title}`}
              >
                {TICKET_STATUS_OPTIONS.map((code) => (
                  <option key={code} value={code}>
                    {code}
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
        <button onClick={handleCreate} disabled={creating || !newTitle.trim()}>
          {creating ? "Creating..." : "Create ticket"}
        </button>
      </div>
    </section>
  );
}

function PostDetailPopup({
  postId,
  accessToken,
  onClose,
}: {
  postId: string;
  accessToken: string;
  onClose: () => void;
}) {
  const [post, setPost] = useState<PostDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<PostAiSummary | null>(null);
  const [keymen, setKeymen] = useState<Keyman[] | null>(null);
  const [counterparties, setCounterparties] = useState<Counterparty[] | null>(null);
  const [lineage, setLineage] = useState<PostLineage | null>(null);

  useEffect(() => {
    setPost(null);
    setError(null);
    setSummary(null);
    setKeymen(null);
    setCounterparties(null);
    setLineage(null);
    fetchPost(accessToken, postId).then(setPost).catch((err) => setError(String(err)));
    fetchPostSummary(accessToken, postId).then(setSummary).catch(() => setSummary(null));
    fetchPostKeymen(accessToken, postId).then((r) => setKeymen(r.keymen)).catch(() => setKeymen([]));
    fetchPostCounterparties(accessToken, postId)
      .then((r) => setCounterparties(r.counterparties))
      .catch(() => setCounterparties([]));
    fetchPostLineage(accessToken, postId).then(setLineage).catch(() => setLineage(null));
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
              {post.voc_type_code} &middot; {post.visibility_code} &middot;{" "}
              {new Date(post.created_at).toLocaleString()}
            </p>
            <p className="post-body">{post.post_body}</p>

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
                        {summary.roles_and_responsibilities.map((rr, i) => (
                          <li key={i}>
                            <strong>{rr.person_name}</strong>: {rr.responsibility}
                          </li>
                        ))}
                      </ul>
                    </>
                  )}
                </>
              ) : (
                <p className="popup-placeholder">Summary unavailable (LLM orchestrator not configured).</p>
              )}
            </section>

            <section className="popup-section">
              <h3>Event Lineage</h3>
              <EventLineageSection lineage={lineage} />
            </section>

            <section className="popup-section">
              <h3>Keyman</h3>
              {keymen && keymen.length > 0 ? (
                <ul className="keyman-list">
                  {keymen.map((person) => (
                    <li key={person.person_id}>
                      <strong>{person.person_name}</strong> ({person.person_side_code})
                      {person.affiliations.length > 0 && (
                        <span className="keyman-affiliations">
                          {" -- "}
                          {person.affiliations.map((a) => a.organization_name).join(", ")}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="popup-placeholder">No Keyman extracted yet.</p>
              )}
            </section>

            {counterparties && counterparties.length > 0 && (
              <section className="popup-section">
                <h3>Counterparties</h3>
                <ul>
                  {counterparties.map((c) => (
                    <li key={c.counterparty_entity_name}>
                      {c.counterparty_entity_name} -- {c.relationship_type_code}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            <IssueTicketPanel postId={postId} accessToken={accessToken} />

            <ChatPanel postId={postId} accessToken={accessToken} />
          </>
        )}
      </div>
    </div>
  );
}

function PostList({ accessToken }: { accessToken: string }) {
  const [posts, setPosts] = useState<PostSummary[] | null>(null);
  const [graph, setGraph] = useState<LineageGraph | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedPostId, setSelectedPostId] = useState<string | null>(null);
  const [canRebuild, setCanRebuild] = useState(false);
  const [rebuilding, setRebuilding] = useState(false);
  const [rebuildError, setRebuildError] = useState<string | null>(null);

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
        {graph && <LineageDag graph={graph} onSelectPost={setSelectedPostId} />}
      </section>
      <ul className="post-list">
        {posts.map((post) => (
          <li key={post.post_id}>
            <button
              className="post-list-item"
              aria-label={`View post: ${post.post_title}`}
              onClick={() => setSelectedPostId(post.post_id)}
            >
              <span className="post-title">{post.post_title}</span>
              <span className="post-badge">{post.visibility_code}</span>
            </button>
          </li>
        ))}
      </ul>
      {selectedPostId && (
        <PostDetailPopup
          postId={selectedPostId}
          accessToken={accessToken}
          onClose={() => setSelectedPostId(null)}
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
