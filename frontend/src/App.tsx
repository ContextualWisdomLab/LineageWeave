import { useEffect, useState } from "react";
import { useAuth } from "react-oidc-context";
import { fetchPost, fetchPosts, type PostDetail, type PostSummary } from "./api";
import "./App.css";

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

  useEffect(() => {
    setPost(null);
    setError(null);
    fetchPost(accessToken, postId).then(setPost).catch((err) => setError(String(err)));
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
            {/* Event Lineage / Keyman / Knowledge Graph / LLM chat panels
                land in Phase 2-4 -- this popup shell is the attachment
                point (Figma frame SBpgot7uTvMxEaxUwvoc0S). */}
            <section className="popup-placeholder">
              Event Lineage, Keyman, and Knowledge Graph views arrive in a
              later phase.
            </section>
          </>
        )}
      </div>
    </div>
  );
}

function PostList({ accessToken }: { accessToken: string }) {
  const [posts, setPosts] = useState<PostSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedPostId, setSelectedPostId] = useState<string | null>(null);

  useEffect(() => {
    fetchPosts(accessToken).then(setPosts).catch((err) => setError(String(err)));
  }, [accessToken]);

  if (error) return <p className="error">{error}</p>;
  if (!posts) return <p>Loading posts...</p>;
  if (posts.length === 0) return <p>No posts visible to this account yet -- try `make seed`.</p>;

  return (
    <>
      <ul className="post-list">
        {posts.map((post) => (
          <li key={post.post_id}>
            <button className="post-list-item" onClick={() => setSelectedPostId(post.post_id)}>
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
