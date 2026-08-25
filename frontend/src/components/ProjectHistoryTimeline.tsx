import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";

import { useLocale } from "../i18n";
import {
  type ProjectHistoryEvent,
  type ProjectHistoryProjection,
  projectHistoryEventTypeLabel,
  projectHistoryText,
  projectHistoryTransitionLabel,
} from "../projectHistory";
import "./ProjectHistoryTimeline.css";

function formatDate(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.valueOf()) ? value : parsed.toISOString().slice(0, 10);
}

function minimumPathScore(event: ProjectHistoryEvent): number | null {
  if (event.related_prior_paths.length === 0) return null;
  return Math.min(...event.related_prior_paths.map((path) => path.minimum_fused_score));
}

function initialEventId(events: ProjectHistoryEvent[], focusEventId: string | null): string {
  return (
    events.find((event) => event.event_id === focusEventId)?.event_id ??
    events[0]?.event_id ??
    ""
  );
}

export function ProjectHistoryTimeline({
  projection,
  onOpenPost,
}: {
  projection: ProjectHistoryProjection;
  onOpenPost: (postId: string) => void;
}) {
  const locale = useLocale();
  const instanceId = useId();
  const panelId = `${instanceId}-project-history-panel`;
  const headingId = `${instanceId}-project-history-heading`;
  const [selectedEventId, setSelectedEventId] = useState(() =>
    initialEventId(projection.events, projection.focus_event_id),
  );
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const eventById = new Map(projection.events.map((event) => [event.event_id, event]));
  const selectedEvent =
    eventById.get(selectedEventId) ??
    eventById.get(initialEventId(projection.events, projection.focus_event_id)) ??
    null;
  const selectedIndex = selectedEvent
    ? projection.events.findIndex((event) => event.event_id === selectedEvent.event_id)
    : -1;
  const selectedTabId = selectedIndex >= 0 ? `${instanceId}-project-history-tab-${selectedIndex}` : undefined;

  useEffect(() => {
    setSelectedEventId(initialEventId(projection.events, projection.focus_event_id));
  }, [projection.normalized_project_key, projection.focus_event_id, projection.events]);

  function selectAt(index: number) {
    const bounded = Math.max(0, Math.min(index, projection.events.length - 1));
    const event = projection.events[bounded];
    if (!event) return;
    setSelectedEventId(event.event_id);
    tabRefs.current[bounded]?.focus();
  }

  function handleTabKey(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let target: number | null = null;
    switch (event.key) {
      case "ArrowLeft":
      case "ArrowUp":
        target = index === 0 ? projection.events.length - 1 : index - 1;
        break;
      case "ArrowRight":
      case "ArrowDown":
        target = index === projection.events.length - 1 ? 0 : index + 1;
        break;
      case "Home":
        target = 0;
        break;
      case "End":
        target = projection.events.length - 1;
        break;
      default:
        return;
    }
    event.preventDefault();
    selectAt(target);
  }

  return (
    <section className="project-history" aria-labelledby={headingId}>
      <header className="project-history-header">
        <div>
          <p className="section-eyebrow">{projection.project_name}</p>
          <h3 id={headingId}>{projectHistoryText(locale, "heading")}</h3>
        </div>
        <p className="project-history-counts">
          {projectHistoryText(locale, "summaryCounts", {
            events: projection.event_count,
            actors: projection.distinct_observed_actor_count,
          })}
        </p>
      </header>

      <p className="project-history-time-basis">{projectHistoryText(locale, "documentTime")}</p>
      {projection.truncated ? (
        <p className="project-history-warning" role="status">
          {projectHistoryText(locale, "truncated")}
        </p>
      ) : null}

      <div
        className="project-history-tabs"
        role="tablist"
        aria-label={projectHistoryText(locale, "heading")}
      >
        {projection.events.map((event, index) => {
          const selected = event.event_id === selectedEvent?.event_id;
          const current = event.event_id === projection.focus_event_id;
          const tabId = `${instanceId}-project-history-tab-${index}`;
          return (
            <button
              id={tabId}
              key={event.event_id}
              ref={(node: HTMLButtonElement | null) => {
                tabRefs.current[index] = node;
              }}
              type="button"
              role="tab"
              className={current ? "project-history-tab project-history-tab-current" : "project-history-tab"}
              aria-selected={selected}
              aria-current={current ? "step" : undefined}
              aria-controls={panelId}
              tabIndex={selected ? 0 : -1}
              onClick={() => setSelectedEventId(event.event_id)}
              onKeyDown={(keyboardEvent: KeyboardEvent<HTMLButtonElement>) =>
                handleTabKey(keyboardEvent, index)
              }
            >
              <span className="project-history-marker" aria-hidden="true" />
              <time dateTime={event.occurred_at}>{formatDate(event.occurred_at)}</time>
              <strong>{event.event_title}</strong>
              <span>{projectHistoryEventTypeLabel(locale, event.event_type_code)}</span>
            </button>
          );
        })}
      </div>

      {selectedEvent ? (
        <div
          id={panelId}
          className="project-history-detail"
          role="tabpanel"
          aria-labelledby={selectedTabId}
        >
          <div className="project-history-detail-heading">
            <div>
              <p className="section-eyebrow">{projectHistoryText(locale, "eventDetail")}</p>
              <h4>{selectedEvent.event_title}</h4>
            </div>
            <button
              type="button"
              onClick={() => onOpenPost(selectedEvent.source_post_id)}
              aria-label={projectHistoryText(locale, "openSourceRecord", {
                title: selectedEvent.event_title,
              })}
            >
              {projectHistoryText(locale, "openSourceRecord", {
                title: selectedEvent.event_title,
              })}
            </button>
          </div>

          <dl className="project-history-facts">
            <div>
              <dt>{projectHistoryText(locale, "eventDate")}</dt>
              <dd>{formatDate(selectedEvent.occurred_at)}</dd>
            </div>
            <div>
              <dt>{projectHistoryText(locale, "eventType")}</dt>
              <dd>{projectHistoryEventTypeLabel(locale, selectedEvent.event_type_code)}</dd>
            </div>
            {selectedEvent.responsibility_transition_code ? (
              <div>
                <dt>{projectHistoryText(locale, "columnTransition")}</dt>
                <dd
                  className={`project-history-transition project-history-transition-${selectedEvent.responsibility_transition_code}`}
                >
                  {projectHistoryTransitionLabel(
                    locale,
                    selectedEvent.responsibility_transition_code,
                  )}
                </dd>
              </div>
            ) : null}
          </dl>

          <section aria-labelledby={`${panelId}-responsibilities`}>
            <h5 id={`${panelId}-responsibilities`}>
              {projectHistoryText(locale, "responsibilityEvidence")}
            </h5>
            {selectedEvent.observed_responsibilities.length > 0 ? (
              <ul className="project-history-responsibilities">
                {selectedEvent.observed_responsibilities.map((responsibility) => (
                  <li key={`${responsibility.actor_key}:${responsibility.responsibility}`}>
                    <strong>{responsibility.actor_name}</strong>
                    {responsibility.affiliated_organization_name
                      ? ` · ${responsibility.affiliated_organization_name}`
                      : ""}
                    <span>{responsibility.responsibility}</span>
                    <span className="project-history-truth">
                      {projectHistoryText(locale, "observed")}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p>{projectHistoryText(locale, "noResponsibilityEvidence")}</p>
            )}
          </section>

          <section aria-labelledby={`${panelId}-paths`}>
            <h5 id={`${panelId}-paths`}>{projectHistoryText(locale, "priorHistory")}</h5>
            {selectedEvent.related_prior_paths.length > 0 ? (
              <ul className="project-history-paths">
                {selectedEvent.related_prior_paths.map((path) => (
                  <li key={`${path.source_event_id}:${path.target_event_id}`}>
                    <p>
                      {path.event_ids
                        .map((eventId) => eventById.get(eventId)?.event_title ?? eventId)
                        .join(" → ")}
                    </p>
                    <span>{path.minimum_fused_score.toFixed(3)}</span>
                    <span className="project-history-truth">
                      {projectHistoryText(locale, "inferred")}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p>{projectHistoryText(locale, "noPriorHistory")}</p>
            )}
            <p className="project-history-boundary">
              {projectHistoryText(locale, "inferredBoundary")}
            </p>
          </section>

          {selectedEvent.project_matches.length > 0 ? (
            <section aria-labelledby={`${panelId}-project-evidence`}>
              <h5 id={`${panelId}-project-evidence`}>
                {projectHistoryText(locale, "projectEvidence")}
              </h5>
              <ul>
                {selectedEvent.project_matches.map((match) => (
                  <li key={`${match.match_kind_code}:${match.matched_value}:${match.provenance}`}>
                    <strong>{match.matched_value}</strong> · {match.provenance} ·{" "}
                    {projectHistoryText(locale, match.truth_status_code)}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>
      ) : null}

      <details className="project-history-exact-values">
        <summary>{projectHistoryText(locale, "exactValues")}</summary>
        <div className="project-history-table-scroll">
          <table aria-label={projectHistoryText(locale, "exactTableLabel")}>
            <thead>
              <tr>
                <th scope="col">{projectHistoryText(locale, "columnDate")}</th>
                <th scope="col">{projectHistoryText(locale, "columnEvent")}</th>
                <th scope="col">{projectHistoryText(locale, "columnType")}</th>
                <th scope="col">{projectHistoryText(locale, "columnTransition")}</th>
                <th scope="col">{projectHistoryText(locale, "columnActors")}</th>
                <th scope="col">{projectHistoryText(locale, "columnPathScore")}</th>
              </tr>
            </thead>
            <tbody>
              {projection.events.map((event) => {
                const pathScore = minimumPathScore(event);
                return (
                  <tr key={`exact:${event.event_id}`}>
                    <td>{formatDate(event.occurred_at)}</td>
                    <th scope="row">{event.event_title}</th>
                    <td>{projectHistoryEventTypeLabel(locale, event.event_type_code)}</td>
                    <td>
                      {projectHistoryTransitionLabel(locale, event.responsibility_transition_code)}
                    </td>
                    <td>
                      {event.observed_responsibilities.length > 0
                        ? event.observed_responsibilities.map((row) => row.actor_name).join(", ")
                        : projectHistoryText(locale, "notApplicable")}
                    </td>
                    <td>
                      {pathScore === null
                        ? projectHistoryText(locale, "notApplicable")
                        : pathScore.toFixed(3)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  );
}
