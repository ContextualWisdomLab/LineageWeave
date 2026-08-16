import { useEffect, useState } from "react";
import {
  BackendError,
  fetchAnalysisRun,
  fetchAnalysisRuns,
  type AnalysisRun,
} from "./api";
import {
  analysisRunCaption,
  analysisRunCorpusHint,
  analysisRunEmptyPostsHint,
  analysisRunNextAction,
  shortDigest,
} from "./analysisRunDisplay";

/**
 * Home-page Analysis runs list and authorized detail.
 *
 * Click a run to load cutoff, lifecycle, reproducibility prefixes, and
 * posts that existed at that cutoff. Hidden runs stay "not visible."
 */
export function AnalysisRunsPanel({
  accessToken,
  onSelectPost,
}: {
  accessToken: string;
  onSelectPost: (postId: string) => void;
}) {
  const [runs, setRuns] = useState<AnalysisRun[] | null>(null);
  const [selected, setSelected] = useState<AnalysisRun | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAnalysisRuns(accessToken)
      .then((payload) => setRuns(payload.analysis_runs))
      .catch((err) => setError(String(err)));
  }, [accessToken]);

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
      </div>
      {error && <p className="error">{error}</p>}
      {runs.length === 0 ? (
        <p className="popup-placeholder">
          No analysis runs visible to this account yet -- try `make seed`.
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
          {(shortDigest(selected.code_revision_sha) || shortDigest(selected.configuration_sha256)) && (
            <p className="post-meta">
              Use these digests to confirm this run matches the code and configuration you approved.
              {shortDigest(selected.code_revision_sha) && ` Revision ${shortDigest(selected.code_revision_sha)}`}
              {shortDigest(selected.configuration_sha256) && ` · Config ${shortDigest(selected.configuration_sha256)}`}
            </p>
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
              <ul aria-label="Posts in this analysis run">
                {selected.visible_posts.map((post) => (
                  <li key={post.post_id}>
                    <button
                      className="keyman-select"
                      aria-label={`Open run post: ${post.post_title}`}
                      onClick={() => onSelectPost(post.post_id)}
                    >
                      {post.post_title}
                    </button>
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
