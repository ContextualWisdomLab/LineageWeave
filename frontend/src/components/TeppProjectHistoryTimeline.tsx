import { useEffect, useState, type CSSProperties } from "react";

import {
  fetchPostProjectHistory,
  type TeppProjectHistory,
  type TeppProjectHistoryEnvelope,
} from "../api";
import { t, tf, useLocale } from "../i18n";
import "./TeppProjectHistoryTimeline.css";

const EVENT_LABELS: Record<string, string> = {
  contract_awarded: "Contract award",
  specification_changed: "Specification change",
  delivered: "Delivery",
  operational_handoff: "Operational handoff",
  voc_received: "VOC event",
  rebid_started: "Rebid started",
  event_observed: "Project event",
};

const FINDING_SUMMARY_KEYS: Record<string, string> = {
  contract_award_before_focus:
    "An explicit contract-award event precedes the focus event. This is a temporal association, not a causal conclusion.",
  specification_change_before_focus:
    "An explicit specification-change event precedes the focus event. This is a temporal association, not a causal conclusion.",
};

function dateLabel(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  const year = String(date.getUTCFullYear()).slice(-2);
  const month = String(date.getUTCMonth() + 1).padStart(2, "0");
  return `'${year}.${month}`;
}

export function TeppProjectHistoryTimeline({
  history,
  onOpenPost,
}: {
  history: TeppProjectHistory;
  onOpenPost: (postId: string) => void;
}) {
  useLocale();
  const finding = history.findings[0];
  const focusEvent = history.events.find((event) => event.event_id === history.focus_event_id);
  const listStyle = {
    "--tepp-event-count": Math.max(1, history.events.length),
  } as CSSProperties;

  return (
    <section className="tepp-project-history" role="region" aria-label={t("TEPP project history")}>
      <div className="tepp-project-history__header">
        <div>
          <p className="section-eyebrow">{t("TEPP-connected answer")}</p>
          <h3>{t("Project event timeline")}</h3>
          <p>
            {tf("Connect explicit events for {project} in chronological order within the knowledge cutoff.", {
              project: history.project_name,
            })}
          </p>
        </div>
        <span className="post-badge">TEPP · v{history.contract_version}</span>
      </div>

      <ol className="tepp-project-history__timeline" style={listStyle}>
        {history.events.map((event) => {
          const focused = event.event_id === history.focus_event_id;
          return (
            <li
              key={event.event_id}
              className={focused ? "tepp-project-history__event is-focus" : "tepp-project-history__event"}
            >
              <time dateTime={event.occurred_at}>{dateLabel(event.occurred_at)}</time>
              <button
                type="button"
                aria-label={`Open evidence: ${event.event_title}`}
                aria-current={focused ? "step" : undefined}
                onClick={() => onOpenPost(event.source_post_id)}
              >
                <span className="tepp-project-history__dot" aria-hidden="true" />
                <strong>{t(EVENT_LABELS[event.event_type_code] ?? event.event_type_code)}</strong>
                <span>{event.event_title}</span>
              </button>
            </li>
          );
        })}
      </ol>

      <div className="tepp-project-history__detail">
        <h4>{t("Event details")}</h4>
        <p>
          {t("Current event:")} {" "}
          <strong>
            {focusEvent
              ? t(EVENT_LABELS[focusEvent.event_type_code] ?? focusEvent.event_title)
              : t("Unknown")}
          </strong>
          {" · "}
          {t("Participant history:")} {" "}
          {history.participant_count} {t("participants")}
        </p>
        {finding ? (
          <p>
            <strong>{t("TEPP finding:")}</strong>{" "}
            {t(FINDING_SUMMARY_KEYS[finding.finding_code] ?? finding.summary)}
          </p>
        ) : (
          <p>
            <strong>{t("TEPP finding:")}</strong>{" "}
            {t("Explicit events were ordered chronologically. No causal conclusion is generated.")}
          </p>
        )}
      </div>

      <p className="tepp-project-history__boundary">
        {t("TEPP explains temporal associations only. It does not generate missing events, participants, causal relationships, or psychometric scores.")}
      </p>
    </section>
  );
}

export function PostProjectHistory({
  accessToken,
  postId,
  onOpenPost,
}: {
  accessToken: string;
  postId: string;
  onOpenPost: (postId: string) => void;
}) {
  useLocale();
  const [envelope, setEnvelope] = useState<TeppProjectHistoryEnvelope | null>(null);

  useEffect(() => {
    let cancelled = false;
    setEnvelope(null);
    fetchPostProjectHistory(accessToken, postId)
      .then((result) => {
        if (!cancelled) setEnvelope(result);
      })
      .catch(() => {
        if (!cancelled) {
          setEnvelope({
            status: "tepp_unavailable",
            project_history: null,
            next_action: "TEPP project history is unavailable.",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [accessToken, postId]);

  if (envelope === null) {
    return <p className="popup-placeholder">{t("Loading TEPP project history.")}</p>;
  }
  if (!envelope.project_history) {
    return (
      <section
        className="popup-section tepp-project-history-status"
        aria-label={t("TEPP project history status")}
      >
        <h3>{t("Project event timeline")}</h3>
        <p>{envelope.next_action}</p>
      </section>
    );
  }
  return <TeppProjectHistoryTimeline history={envelope.project_history} onOpenPost={onOpenPost} />;
}
