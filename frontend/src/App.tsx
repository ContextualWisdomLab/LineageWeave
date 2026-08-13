import { useEffect, useState } from "react";
import { useAuth } from "react-oidc-context";
import {
  askPostChat,
  createPostTicket,
  deriveCommitment,
  extractPostKeymen,
  fetchCalendar,
  fetchLineageGraph,
  fetchMe,
  fetchPost,
  fetchPostActivity,
  fetchPostAffiliateTree,
  fetchPostCounterparties,
  fetchPostKeymen,
  fetchPostLineage,
  fetchPostSummary,
  fetchPostTickets,
  fetchPostVocEvidence,
  fetchPosts,
  fetchRelatedKeymen,
  rebuildLineage,
  updateTicketStatus,
  type ActivityEvent,
  type AffiliateNode,
  type CalendarEntry,
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
  type RelatedNode,
  type VocEvidence,
} from "./api";
import { LineageDag } from "./LineageDag";
import { subgraphForPost } from "./lineageLayout";
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

function AffiliateTreeNode({ node }: { node: AffiliateNode }) {
  return (
    <li>
      <span className={node.resolved ? "affiliate-resolved" : "affiliate-unresolved"}>
        {node.entity_name}
      </span>
      {node.entity_level_code && <span className="affiliate-level"> ({node.entity_level_code})</span>}
      {!node.resolved && <span className="affiliate-unresolved-mark"> unresolved</span>}
      {node.people.length > 0 && (
        <span className="keyman-affiliations">
          {" -- "}
          {node.people.map((person) => `${person.person_name} (${person.person_side_code})`).join(", ")}
        </span>
      )}
      {node.children.length > 0 && (
        <ul>
          {node.children.map((child) => (
            <AffiliateTreeNode key={child.entity_id ?? child.entity_name} node={child} />
          ))}
        </ul>
      )}
    </li>
  );
}

function VocEvidenceSection({ evidence }: { evidence: VocEvidence | null }) {
  if (!evidence) return <p>Loading VOC evidence...</p>;
  return (
    <section className="popup-section">
      <h3>VOC evidence</h3>
      <p className="post-meta">
        {evidence.voc_type_label} ({evidence.voc_type_code})
      </p>
      {evidence.excerpts.length === 0 ? (
        <p className="popup-placeholder">No extractive excerpt -- no named organization appears in this post.</p>
      ) : (
        <ul className="voc-excerpt-list">
          {evidence.excerpts.map((excerpt) => (
            <li key={excerpt}>
              <blockquote>{excerpt}</blockquote>
            </li>
          ))}
        </ul>
      )}
      {evidence.counterparties.map((row) => (
        <p key={row.counterparty_entity_name} className="voc-counterparty">
          {row.counterparty_entity_name} -- {row.relationship_label}
        </p>
      ))}
    </section>
  );
}

function KeymanPanel({
  postId,
  accessToken,
  keymen,
  canExtract,
  onExtracted,
}: {
  postId: string;
  accessToken: string;
  keymen: Keyman[] | null;
  canExtract: boolean;
  onExtracted: () => void;
}) {
  const [related, setRelated] = useState<RelatedNode[] | null>(null);
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const [extracting, setExtracting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSelect(person: Keyman) {
    setSelectedName(person.person_name);
    setRelated(null);
    try {
      const result = await fetchRelatedKeymen(accessToken, person.person_id);
      setRelated(result.related);
    } catch {
      setRelated([]);
    }
  }

  async function handleExtract() {
    setExtracting(true);
    setError(null);
    try {
      await extractPostKeymen(accessToken, postId);
      onExtracted();
    } catch (err) {
      setError(String(err));
    } finally {
      setExtracting(false);
    }
  }

  return (
    <section className="popup-section">
      <div className="lineage-home-header">
        <h3>Keyman</h3>
        {canExtract && (
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
                onClick={() => handleSelect(person)}
              >
                <strong>{person.person_name}</strong> ({person.person_side_code})
              </button>
              {person.affiliations.length > 0 && (
                <span className="keyman-affiliations">
                  {" -- "}
                  {person.affiliations.map((affiliation) => affiliation.organization_name).join(", ")}
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
              {related.map((node) => (
                <li key={`${node.node_type_code}:${node.node_id}`}>
                  {node.label ?? node.node_id} ({node.node_type_code})
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}

const TICKET_STATUS_OPTIONS = ["open", "in_progress", "closed"];

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
      setError(String(err));
    } finally {
      setDeriving(false);
    }
  }

  return (
    <section className="popup-section">
      <div className="lineage-home-header">
        <h3>이슈 티켓 (Issue tickets)</h3>
        {canExtract && (
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
              <span className="post-badge">{event.event_type}</span>
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
  onClose,
  onSelectPost,
}: {
  postId: string;
  accessToken: string;
  canExtract: boolean;
  graph: LineageGraph | null;
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

  function reloadKeymen() {
    fetchPostKeymen(accessToken, postId).then((r) => setKeymen(r.keymen)).catch(() => setKeymen([]));
    fetchPostAffiliateTree(accessToken, postId)
      .then((r) => setAffiliateTrees(r.trees))
      .catch(() => setAffiliateTrees([]));
    fetchPostVocEvidence(accessToken, postId).then(setVocEvidence).catch(() => setVocEvidence(null));
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
    fetchPost(accessToken, postId).then(setPost).catch((err) => setError(String(err)));
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

            <VocEvidenceSection evidence={vocEvidence} />

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
                    <AffiliateTreeNode key={node.entity_id ?? node.entity_name} node={node} />
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
            />

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

            <IssueTicketPanel postId={postId} accessToken={accessToken} canExtract={canExtract} />

            <ActivityPanel postId={postId} accessToken={accessToken} />

            <ChatPanel postId={postId} accessToken={accessToken} />
          </>
        )}
      </div>
    </div>
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
                <span className="post-badge">due {entry.due_date}</span>
              </button>
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
      <CalendarPanel accessToken={accessToken} onSelectPost={setSelectedPostId} />
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
          canExtract={canRebuild}
          graph={graph}
          onClose={() => setSelectedPostId(null)}
          onSelectPost={setSelectedPostId}
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
