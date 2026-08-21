import { useState } from "react";

import { fetchProjectHistory } from "../api";
import { t, useLocale } from "../i18n";
import { projectHistoryText, type ProjectHistoryProjection } from "../projectHistory";
import { ProjectHistoryTimeline } from "./ProjectHistoryTimeline";

export function ProjectHistoryDisclosure({
  accessToken,
  projectKey,
  focusPostId,
  knowledgeCutoff,
  onOpenPost,
  onSearch,
}: {
  accessToken: string;
  projectKey: string;
  focusPostId: string;
  knowledgeCutoff?: string;
  onOpenPost: (postId: string) => void;
  onSearch?: (projectKey: string) => void;
}) {
  const locale = useLocale();
  const [opened, setOpened] = useState(false);
  const [loading, setLoading] = useState(false);
  const [projection, setProjection] = useState<ProjectHistoryProjection | null>(null);
  const [error, setError] = useState(false);

  function open() {
    if (opened) return;
    setOpened(true);
    setLoading(true);
    fetchProjectHistory(accessToken, { projectKey, focusPostId, knowledgeCutoff })
      .then((result) => {
        setProjection(result);
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });
  }

  return (
    <div className="project-history-disclosure">
      <button type="button" onClick={() => onSearch?.(projectKey)} disabled={!onSearch}>
        {t("Search related posts")}
      </button>
      <button type="button" onClick={open} disabled={opened}>
        {projectHistoryText(locale, "openProjectHistory")}
      </button>
      {error ? (
        <p role="alert">{projectHistoryText(locale, "historyUnavailable")}</p>
      ) : null}
      {!error && !loading && projection ? (
        <ProjectHistoryTimeline projection={projection} onOpenPost={onOpenPost} />
      ) : null}
    </div>
  );
}
