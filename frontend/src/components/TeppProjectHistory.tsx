import { useEffect, useState } from "react";

import {
  BackendError,
  fetchTeppProjectHistory,
  type TeppProjectHistoryProjection,
} from "../api";
import { t, tf } from "../i18n";
import "./TeppProjectHistory.css";

function formatEventDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.valueOf())) return value;
  return parsed.toISOString().slice(0, 10);
}

function findingCopy(code: string): string {
  switch (code) {
    case "specification_change_and_handoff_before_focus":
      return t(
        "TEPP temporal association: explicit specification change and handoff precede the focus event; this is temporal association, not causality.",
      );
    case "specification_change_before_focus":
      return t("TEPP temporal association: an explicit specification change precedes the focus event.");
    case "handoff_before_focus":
      return t("TEPP temporal association: an explicit operational handoff precedes the focus event.");
    case "rebid_after_focus":
      return t("TEPP temporal association: an explicit rebid event follows the focus event.");
    default:
      return t("TEPP temporal association, not causality.");
  }
}

export function TeppProjectHistory({
  projection,
  onOpenPost,
}: {
  projection: TeppProjectHistoryProjection;
  onOpenPost: (postId: string) => void;
}) {
  const usesAvailabilityProxy = projection.events.some(
    (event) => event.availability_basis_code === "source_created_at_proxy",
  );
  const preferredFinding =
    projection.findings.find(
      (finding) => finding.finding_code === "specification_change_and_handoff_before_focus",
    ) ?? projection.findings[0];

  return (
    <section
      className="tepp-project-history"
      aria-labelledby={`tepp-project-history-${projection.focus_event_id}`}
    >
      <header className="tepp-project-history-header">
        <div>
          <p className="section-eyebrow">{t("TEPP-linked answer")}</p>
          <h3 id={`tepp-project-history-${projection.focus_event_id}`}>
            {t("Project event timeline")}
          </h3>
          <p className="tepp-project-name">{projection.project_name}</p>
        </div>
        <span className="tepp-project-history-badge">TEPP</span>
      </header>

      <p className="tepp-project-history-meta">
        {tf("{count} explicit participants", { count: String(projection.participant_count) })}
        {" · "}
        {formatEventDate(projection.history_span_start)} — {formatEventDate(projection.history_span_end)}
      </p>

      <ol className="tepp-project-timeline" aria-label={t("Project event timeline")}>
        {projection.events.map((event) => {
          const isFocus = event.event_id === projection.focus_event_id;
          return (
            <li
              key={event.event_id}
              className={isFocus ? "tepp-project-event tepp-project-event-focus" : "tepp-project-event"}
              aria-current={isFocus ? "step" : undefined}
            >
              <span className="tepp-project-event-marker" aria-hidden="true" />
              <time dateTime={event.occurred_at}>{formatEventDate(event.occurred_at)}</time>
              <strong>{event.event_title}</strong>
              <span className="tepp-project-event-kind">{event.event_type_code}</span>
              <button
                type="button"
                onClick={() => onOpenPost(event.source_post_id)}
                aria-label={tf("Open evidence: {title}", { title: event.event_title })}
              >
                {t("Open evidence")}
              </button>
            </li>
          );
        })}
      </ol>

      <div className="tepp-project-history-detail">
        <h4>{t("Event detail")}</h4>
        <p>{preferredFinding ? findingCopy(preferredFinding.finding_code) : t("No coded TEPP association is available for these explicit events.")}</p>
        <p className="tepp-project-history-boundary">
          {t("TEPP orders explicit evidence and does not infer a causal score or missing event.")}
        </p>
        {usesAvailabilityProxy ? (
          <p className="tepp-project-history-warning">
            {t(
              "The source-created time is an availability proxy until a separate system-availability clock is stored.",
            )}
          </p>
        ) : null}
      </div>
    </section>
  );
}

export function TeppProjectHistoryPanel({
  accessToken,
  postId,
  knowledgeCutoff,
  onOpenPost,
}: {
  accessToken: string;
  postId: string;
  knowledgeCutoff?: string;
  onOpenPost: (postId: string) => void;
}) {
  const [projection, setProjection] = useState<TeppProjectHistoryProjection | null>(null);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setProjection(null);
    setUnavailable(false);
    fetchTeppProjectHistory(accessToken, postId, knowledgeCutoff)
      .then((result) => {
        if (!cancelled) setProjection(result);
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setUnavailable(error instanceof BackendError && error.status === 503);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [accessToken, knowledgeCutoff, postId]);

  if (unavailable) {
    return (
      <section className="popup-section" aria-label={t("TEPP project history")}>
        <h3>{t("Project event timeline")}</h3>
        <p className="popup-placeholder">
          {t("TEPP project history is not available; no local timeline substitute was invented.")}
        </p>
      </section>
    );
  }
  if (!projection) {
    return (
      <section className="popup-section" aria-label={t("TEPP project history")}>
        <h3>{t("Project event timeline")}</h3>
        <p>{t("Loading TEPP project history...")}</p>
      </section>
    );
  }
  return <TeppProjectHistory projection={projection} onOpenPost={onOpenPost} />;
}
