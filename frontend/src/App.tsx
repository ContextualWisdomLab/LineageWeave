import { useEffect, useState } from "react";
import { useAuth } from "react-oidc-context";
import {
  askCubee,
  attachOntologyObject,
  fetchCalendar,
  fetchKeymenCatalog,
  fetchLineageGraph,
  fetchMe,
  fetchOrgmetraUnits,
  fetchPost,
  fetchPostFiveW1H,
  fetchPostKeymen,
  fetchPostLineage,
  fetchPostTickets,
  fetchPosts,
  searchBoard,
  type CalendarEntry,
  type CurrentUser,
  type FiveW1HSlot,
  type IssueTicket,
  type Keyman,
  type LineageGraph,
  type OrgmetraUnit,
  type PostDetail,
  type PostLineage,
  type PostSummary,
  type UnverifiedCandidate,
} from "./api";
import { AskCubee } from "./components/AskCubee";
import { Attachments } from "./components/Attachments";
import { Board } from "./components/Board";
import { BuyerNav, type BuyerDestination } from "./components/BuyerNav";
import { CommitmentsPanel } from "./components/CommitmentsPanel";
import { CustomerMaster } from "./components/CustomerMaster";
import { EventLineagePanel } from "./components/EventLineagePanel";
import { FiveW1H } from "./components/FiveW1H";
import { GroundedQa } from "./components/GroundedQa";
import { KeymenPanel } from "./components/KeymenPanel";
import { OriginalSource } from "./components/OriginalSource";
import { PopupCloseButton } from "./components/PopupCloseButton";
import "./App.css";

function PostEventScreen({
  postId,
  accessToken,
  graph,
  onClose,
  onSelectNode,
  onOpenAskCubee,
  onPromoteCandidate,
}: {
  postId: string;
  accessToken: string;
  graph: LineageGraph | null;
  onClose: () => void;
  onSelectNode: (postId: string) => void;
  onOpenAskCubee: (postId: string) => void;
  onPromoteCandidate: (candidate: UnverifiedCandidate) => void;
}) {
  const [post, setPost] = useState<PostDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lineage, setLineage] = useState<PostLineage | null>(null);
  const [slots, setSlots] = useState<FiveW1HSlot[] | null>(null);
  const [slotsError, setSlotsError] = useState<string | null>(null);
  const [keymen, setKeymen] = useState<Keyman[] | null>(null);
  const [tickets, setTickets] = useState<IssueTicket[] | null>(null);

  useEffect(() => {
    setPost(null);
    setError(null);
    setLineage(null);
    setSlots(null);
    setSlotsError(null);
    setKeymen(null);
    setTickets(null);
    fetchPost(accessToken, postId)
      .then(setPost)
      .catch((err) => setError(String(err)));
    fetchPostLineage(accessToken, postId)
      .then(setLineage)
      .catch(() => setLineage({ post_id: postId, direct: [], indirect: [] }));
    fetchPostFiveW1H(accessToken, postId)
      .then((payload) => setSlots(payload.slots))
      .catch((err) => setSlotsError(String(err)));
    fetchPostKeymen(accessToken, postId)
      .then((payload) => setKeymen(payload.keymen))
      .catch(() => setKeymen([]));
    fetchPostTickets(accessToken, postId)
      .then((payload) => setTickets(payload.tickets))
      .catch(() => setTickets([]));
  }, [postId, accessToken]);

  return (
    <div className="popup-backdrop" onClick={onClose}>
      <div className="popup-panel newspaper-print" onClick={(event) => event.stopPropagation()}>
        <PopupCloseButton onClose={onClose} label="Close" />
        {error ? <p className="error">{error}</p> : null}
        {!post && !error ? <p>Loading...</p> : null}
        {post ? (
          <>
            <h2>{post.post_title}</h2>
            <p className="post-meta">{post.voc_type_label ?? post.voc_type_code}</p>
            <OriginalSource body={post.post_body} />
            <FiveW1H slots={slots} error={slotsError} />
            <KeymenPanel keymen={keymen} />
            <CommitmentsPanel tickets={tickets} />
            <Attachments body={post.post_body} />
            <EventLineagePanel
              lineage={lineage}
              graph={graph}
              postId={postId}
              onSelectNode={onSelectNode}
            />
            <GroundedQa
              onAsk={(question) => askCubee(accessToken, question, postId)}
              onPromoteCandidate={onPromoteCandidate}
            />
            <p>
              <button type="button" onClick={() => onOpenAskCubee(postId)}>
                Ask Cubee에서 열기
              </button>
            </p>
          </>
        ) : null}
      </div>
    </div>
  );
}

function BuyerHome({ accessToken }: { accessToken: string }) {
  const [destination, setDestination] = useState<BuyerDestination>("board");
  const [posts, setPosts] = useState<PostSummary[] | null>(null);
  const [graph, setGraph] = useState<LineageGraph | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedPostId, setSelectedPostId] = useState<string | null>(null);
  const [askPostId, setAskPostId] = useState<string | null>(null);
  const [askLineage, setAskLineage] = useState<PostLineage | null>(null);
  const [me, setMe] = useState<CurrentUser | null>(null);
  const [orgUnits, setOrgUnits] = useState<OrgmetraUnit[] | null>(null);
  const [orgAvailable, setOrgAvailable] = useState(false);
  const [catalogKeymen, setCatalogKeymen] = useState<Keyman[] | null>(null);
  const [commitments, setCommitments] = useState<CalendarEntry[] | null>(null);
  const [pendingAttach, setPendingAttach] = useState<UnverifiedCandidate | null>(null);
  const [attachError, setAttachError] = useState<string | null>(null);
  const [attachBusy, setAttachBusy] = useState(false);

  useEffect(() => {
    fetchPosts(accessToken).then(setPosts).catch((err) => setError(String(err)));
    fetchLineageGraph(accessToken).then(setGraph).catch(() => setGraph({ nodes: [], edges: [] }));
  }, [accessToken]);

  useEffect(() => {
    if (destination !== "customers") {
      return;
    }
    fetchMe(accessToken).then(setMe).catch(() => setMe(null));
    fetchOrgmetraUnits(accessToken, "corporate")
      .then((payload) => {
        setOrgAvailable(payload.available);
        setOrgUnits(payload.units);
      })
      .catch(() => {
        setOrgAvailable(false);
        setOrgUnits([]);
      });
    fetchKeymenCatalog(accessToken)
      .then((payload) => setCatalogKeymen(payload.keymen))
      .catch(() => setCatalogKeymen([]));
    fetchCalendar(accessToken)
      .then((payload) => setCommitments(payload.commitments))
      .catch(() => setCommitments([]));
  }, [destination, accessToken]);

  useEffect(() => {
    if (destination !== "ask" || !askPostId) {
      return;
    }
    fetchPostLineage(accessToken, askPostId)
      .then(setAskLineage)
      .catch(() => setAskLineage({ post_id: askPostId, direct: [], indirect: [] }));
  }, [destination, askPostId, accessToken]);

  const askTitle = posts?.find((post) => post.post_id === askPostId)?.post_title ?? null;

  return (
    <>
      <BuyerNav destination={destination} onChange={setDestination} />
      {destination === "board" ? (
        <Board
          items={posts}
          error={error}
          onOpenItem={setSelectedPostId}
          onSearch={async (query) => {
            const result = await searchBoard(accessToken, query);
            return result.posts;
          }}
        />
      ) : null}
      {destination === "customers" ? (
        <CustomerMaster
          me={me}
          orgmetraAvailable={orgAvailable}
          units={orgUnits}
          keymen={catalogKeymen}
          commitments={commitments}
          pendingAttach={pendingAttach}
          attachError={attachError}
          attachBusy={attachBusy}
          onAttachPending={
            pendingAttach
              ? async () => {
                  setAttachBusy(true);
                  setAttachError(null);
                  try {
                    const result = await attachOntologyObject(accessToken, pendingAttach.label);
                    if (result.attached) {
                      setPendingAttach(null);
                    } else {
                      setAttachError(result.empty_next_action);
                    }
                  } catch (err) {
                    setAttachError(String(err));
                  } finally {
                    setAttachBusy(false);
                  }
                }
              : undefined
          }
        />
      ) : null}
      {destination === "ask" ? (
        <AskCubee
          postId={askPostId}
          postTitle={askTitle}
          lineage={askLineage}
          graph={graph}
          onAsk={(question) => askCubee(accessToken, question, askPostId)}
          onSelectNode={(postId) => {
            setAskPostId(postId);
            setSelectedPostId(postId);
          }}
          onPromoteCandidate={(candidate) => {
            setPendingAttach(candidate);
            setAttachError(null);
            setDestination("customers");
          }}
        />
      ) : null}
      {selectedPostId && destination !== "ask" ? (
        <PostEventScreen
          postId={selectedPostId}
          accessToken={accessToken}
          graph={graph}
          onClose={() => setSelectedPostId(null)}
          onSelectNode={setSelectedPostId}
          onOpenAskCubee={(postId) => {
            setAskPostId(postId);
            setSelectedPostId(null);
            setDestination("ask");
          }}
          onPromoteCandidate={(candidate) => {
            setPendingAttach(candidate);
            setAttachError(null);
            setSelectedPostId(null);
            setDestination("customers");
          }}
        />
      ) : null}
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
      <BuyerHome accessToken={accessToken} />
    </main>
  );
}
