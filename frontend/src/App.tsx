import { useEffect, useState } from "react";
import { useAuth } from "react-oidc-context";
import {
  askLineageQa,
  fetchLineageGraph,
  fetchPost,
  fetchPostFiveW1H,
  fetchPostLineage,
  fetchPostSummary,
  fetchPosts,
  type FiveW1HSlot,
  type LineageGraph,
  type PostAiSummary,
  type PostDetail,
  type PostLineage,
  type PostSummary,
} from "./api";
import { EventLineagePanel } from "./components/EventLineagePanel";
import { FiveW1H } from "./components/FiveW1H";
import { GroundedQa } from "./components/GroundedQa";
import { OriginalSource } from "./components/OriginalSource";
import { PopupCloseButton } from "./components/PopupCloseButton";
import { RolesResponsibilities } from "./components/RolesResponsibilities";
import { WeeklyVoc } from "./components/WeeklyVoc";
import "./App.css";

function EventLineageScreen({
  postId,
  accessToken,
  graph,
  onClose,
  onSelectNode,
}: {
  postId: string;
  accessToken: string;
  graph: LineageGraph | null;
  onClose: () => void;
  onSelectNode: (postId: string) => void;
}) {
  const [post, setPost] = useState<PostDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<PostAiSummary | null>(null);
  const [summaryUnavailable, setSummaryUnavailable] = useState(false);
  const [lineage, setLineage] = useState<PostLineage | null>(null);
  const [slots, setSlots] = useState<FiveW1HSlot[] | null>(null);
  const [slotsError, setSlotsError] = useState<string | null>(null);

  useEffect(() => {
    setPost(null);
    setError(null);
    setSummary(null);
    setSummaryUnavailable(false);
    setLineage(null);
    setSlots(null);
    setSlotsError(null);
    fetchPost(accessToken, postId)
      .then(setPost)
      .catch((err) => setError(String(err)));
    fetchPostSummary(accessToken, postId)
      .then(setSummary)
      .catch(() => {
        setSummary(null);
        setSummaryUnavailable(true);
      });
    fetchPostLineage(accessToken, postId)
      .then(setLineage)
      .catch(() => setLineage({ post_id: postId, direct: [], indirect: [] }));
    fetchPostFiveW1H(accessToken, postId)
      .then((payload) => setSlots(payload.slots))
      .catch((err) => setSlotsError(String(err)));
  }, [postId, accessToken]);

  return (
    <div className="popup-backdrop" onClick={onClose}>
      <div className="popup-panel" onClick={(event) => event.stopPropagation()}>
        <PopupCloseButton onClose={onClose} label="Close" />
        {error ? <p className="error">{error}</p> : null}
        {!post && !error ? <p>Loading...</p> : null}
        {post ? (
          <>
            <h2>{post.post_title}</h2>
            <p className="post-meta">
              {post.voc_type_label ?? post.voc_type_code}
            </p>
            <OriginalSource body={post.post_body} />
            <EventLineagePanel
              lineage={lineage}
              graph={graph}
              postId={postId}
              onSelectNode={onSelectNode}
            />
            <FiveW1H slots={slots} error={slotsError} />
            <GroundedQa
              onAsk={(question) => askLineageQa(accessToken, postId, question)}
            />
            <RolesResponsibilities
              roles={summary?.roles_and_responsibilities ?? (summaryUnavailable ? [] : null)}
              unavailable={summaryUnavailable}
            />
          </>
        ) : null}
      </div>
    </div>
  );
}

function BuyerHome({ accessToken }: { accessToken: string }) {
  const [posts, setPosts] = useState<PostSummary[] | null>(null);
  const [graph, setGraph] = useState<LineageGraph | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedPostId, setSelectedPostId] = useState<string | null>(null);

  useEffect(() => {
    fetchPosts(accessToken).then(setPosts).catch((err) => setError(String(err)));
    fetchLineageGraph(accessToken).then(setGraph).catch(() => setGraph({ nodes: [], edges: [] }));
  }, [accessToken]);

  return (
    <>
      <WeeklyVoc items={posts} error={error} onOpenItem={setSelectedPostId} />
      {selectedPostId ? (
        <EventLineageScreen
          postId={selectedPostId}
          accessToken={accessToken}
          graph={graph}
          onClose={() => setSelectedPostId(null)}
          onSelectNode={setSelectedPostId}
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
