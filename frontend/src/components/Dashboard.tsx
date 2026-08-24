import { useCallback, useEffect, useRef, useState } from "react";
import {
  fetchPeriodReportIndex,
  fetchPeriodReports,
  fetchRankings,
  type PeriodGroupReport,
  type RankingList,
  type ReportMember,
} from "../api";
import { ExceptionAlert } from "./SummaryStatus";
import { productExceptionCopy } from "../productExceptionCopy";
import { t, tf } from "../i18n";

const PROJECT_GROUPING_KIND = "project";
const MAX_PROJECTS = 6;
const MAX_POSTS = 8;

function dedupeMembersByHighestTheta(reports: PeriodGroupReport[]): ReportMember[] {
  const best = new Map<string, ReportMember>();
  for (const report of reports) {
    for (const member of report.members) {
      const current = best.get(member.post_id);
      if (!current || member.theta_eap > current.theta_eap) {
        best.set(member.post_id, member);
      }
    }
  }
  return Array.from(best.values());
}

/**
 * The `/` landing page: a news-portal front page ranking posts and
 * projects by real fast-mlsirm-calibrated theta (ADR 0003/0145), never
 * an invented weight. Falls back to RankWeave's fused post ranking
 * (ADR 0024) when no project period report has been calibrated yet.
 *
 * Next action on every card: open the ranked post.
 */
export function Dashboard({
  accessToken,
  onSelectPost,
}: {
  accessToken: string;
  onSelectPost: (postId: string) => void;
}) {
  const [periodCode, setPeriodCode] = useState<string | null | undefined>(undefined);
  const [projectReports, setProjectReports] = useState<PeriodGroupReport[] | null>(null);
  const [projectsError, setProjectsError] = useState<string | null>(null);
  const [rankings, setRankings] = useState<RankingList | null>(null);
  const [rankingsError, setRankingsError] = useState<string | null>(null);
  const requestIdRef = useRef(0);

  const loadProjects = useCallback(async () => {
    const requestId = ++requestIdRef.current;
    setProjectsError(null);
    try {
      const index = await fetchPeriodReportIndex(accessToken, PROJECT_GROUPING_KIND);
      if (requestId !== requestIdRef.current) return;
      const latest = index.periods[0]?.period_code ?? null;
      setPeriodCode(latest);
      if (!latest) {
        setProjectReports([]);
        return;
      }
      const reports = await fetchPeriodReports(accessToken, PROJECT_GROUPING_KIND, latest);
      if (requestId !== requestIdRef.current) return;
      setProjectReports(reports.reports);
    } catch (err) {
      if (requestId !== requestIdRef.current) return;
      setPeriodCode(null);
      setProjectReports([]);
      setProjectsError(productExceptionCopy(err, t("Important projects")).title);
    }
  }, [accessToken]);

  const loadRankings = useCallback(async () => {
    setRankingsError(null);
    try {
      const ranking = await fetchRankings(accessToken);
      setRankings(ranking);
    } catch (err) {
      setRankingsError(productExceptionCopy(err, t("Important posts")).title);
    }
  }, [accessToken]);

  useEffect(() => {
    void loadProjects();
  }, [loadProjects]);

  useEffect(() => {
    void loadRankings();
  }, [loadRankings]);

  const loading = periodCode === undefined;
  const importantProjects = (projectReports ?? [])
    .slice()
    .sort((left, right) => right.mean_theta - left.mean_theta)
    .slice(0, MAX_PROJECTS);
  const calibratedPosts = dedupeMembersByHighestTheta(projectReports ?? [])
    .sort((left, right) => right.theta_eap - left.theta_eap)
    .slice(0, MAX_POSTS);
  const usingFallbackRanking = calibratedPosts.length === 0;
  const fallbackPosts = usingFallbackRanking ? (rankings?.rankings ?? []).slice(0, MAX_POSTS) : [];

  return (
    <section className="dashboard-surface" aria-labelledby="dashboard-title">
      <header className="dashboard-masthead">
        <div>
          <p className="post-meta">{t("Dashboard")}</p>
          <h2 id="dashboard-title">{t("Important posts and projects")}</h2>
          <p>
            {periodCode
              ? tf("Ranked by fast-mlsirm calibration for {period}. No score on this page is invented.", {
                  period: periodCode,
                })
              : t("Ranking source: fast-mlsirm calibration where available, RankWeave fusion otherwise. No score on this page is invented.")}
          </p>
        </div>
      </header>

      <section className="dashboard-rail" aria-labelledby="dashboard-projects-heading">
        <h3 id="dashboard-projects-heading">{t("Important projects")}</h3>
        {loading ? <p role="status">{t("Loading calibrated projects...")}</p> : null}
        {projectsError ? (
          <ExceptionAlert title={projectsError} retryLabel={t("Retry")} onRetry={() => void loadProjects()} />
        ) : null}
        {!loading && !projectsError && importantProjects.length === 0 ? (
          <p className="popup-placeholder">
            {t("No calibrated project reports yet. Ask an administrator to run a period-report rebuild.")}
          </p>
        ) : null}
        {importantProjects.length > 0 ? (
          <ol className="dashboard-project-list" aria-label={t("Important projects")}>
            {importantProjects.map((project, index) => {
              const topMember = project.members
                .slice()
                .sort((left, right) => right.theta_eap - left.theta_eap)[0];
              return (
                <li key={project.grouping_key} className="dashboard-project-card">
                  <button
                    type="button"
                    className="dashboard-card-button"
                    disabled={!topMember}
                    aria-label={tf("Open project: {label}", {
                      label: project.grouping_label ?? project.grouping_key,
                    })}
                    onClick={() => topMember && onSelectPost(topMember.post_id)}
                  >
                    <span className="dashboard-rank">{index + 1}</span>
                    <span className="dashboard-card-title">{project.grouping_label ?? project.grouping_key}</span>
                    <span className="post-badge">
                      {tf("fast-mlsirm θ {theta}", { theta: project.mean_theta.toFixed(2) })}
                    </span>
                    <span className="post-badge">{tf("{count} posts", { count: project.post_count })}</span>
                  </button>
                </li>
              );
            })}
          </ol>
        ) : null}
      </section>

      <section className="dashboard-grid-section" aria-labelledby="dashboard-posts-heading">
        <h3 id="dashboard-posts-heading">{t("Important posts")}</h3>
        {rankingsError && usingFallbackRanking ? (
          <ExceptionAlert title={rankingsError} retryLabel={t("Retry")} onRetry={() => void loadRankings()} />
        ) : null}
        {!loading && calibratedPosts.length === 0 && fallbackPosts.length === 0 && !rankingsError ? (
          <p className="popup-placeholder">
            {t("No posts have been evaluated yet. Evaluate a post to surface it here.")}
          </p>
        ) : null}
        {calibratedPosts.length > 0 ? (
          <ol className="dashboard-post-grid" aria-label={t("Important posts")}>
            {calibratedPosts.map((post, index) => (
              <li key={post.post_id} className="dashboard-post-card">
                <button
                  type="button"
                  className="dashboard-card-button"
                  aria-label={tf("Open post: {title}", { title: post.post_title })}
                  onClick={() => onSelectPost(post.post_id)}
                >
                  <span className="dashboard-rank">{index + 1}</span>
                  <span className="dashboard-card-title">{post.post_title}</span>
                  <span className="post-badge">
                    {tf("fast-mlsirm θ {theta}", { theta: post.theta_eap.toFixed(2) })}
                  </span>
                </button>
              </li>
            ))}
          </ol>
        ) : fallbackPosts.length > 0 ? (
          <ol className="dashboard-post-grid" aria-label={t("Important posts")}>
            {fallbackPosts.map((post) => (
              <li key={post.post_id} className="dashboard-post-card">
                <button
                  type="button"
                  className="dashboard-card-button"
                  aria-label={tf("Open post: {title}", { title: post.post_title })}
                  onClick={() => onSelectPost(post.post_id)}
                >
                  <span className="dashboard-rank">{post.fused_rank}</span>
                  <span className="dashboard-card-title">{post.post_title}</span>
                  <span className="post-badge">{t("RankWeave fusion")}</span>
                </button>
              </li>
            ))}
          </ol>
        ) : null}
      </section>
    </section>
  );
}
