import { useEffect, useState } from "react";
import { fetchOperationsDashboard, fetchVoiceTaxonomySummary, type OperationsDashboardResponse, type VoiceTaxonomySummary as VoiceSummary } from "../api";
import { t, tf, useLocale } from "../i18n";
import { VoiceTaxonomySummary } from "./VoiceTaxonomySummary";

function formatElapsed(seconds: number): string {
  const days = Math.floor(seconds / 86_400);
  const hours = Math.floor((seconds % 86_400) / 3_600);
  const minutes = Math.floor((seconds % 3_600) / 60);
  return tf("{days}d {hours}h {minutes}m {seconds}s", { days, hours, minutes, seconds: seconds % 60 });
}

const dimensionLabels = {
  business_unit: "Business unit",
  process_unit: "PU",
  team: "Team",
  person: "Person",
} as const;

const topicStateLabels = {
  active: "Active",
  dormant: "Dormant",
  reactivated: "Reactivated",
} as const;

const topicEventLabels = { birth: "Started", split: "Split", merge: "Merged", retirement: "Ended" } as const;

const caseKindLabels: Record<string, string> = {
  claim_investigation: "Claim investigation",
  rebid_handover: "Rebid and handover",
  external_information: "External information",
  repeat_issue: "Recurring issue",
};

const factTypeLabels: Record<string, string> = {
  order: "Affected order",
  specification_change: "Specification change",
  originating_order: "Originating order",
  sales_pool: "Sales pool",
  discussion: "Discussion",
  counterparty: "Counterparty",
  our_owner: "Our owner",
  decision: "Decision",
  external_relation: "Business relationship",
  issue_pattern: "Recurring pattern",
  improvement_action: "Improvement action",
};

const lifecycleLabels: Record<string, string> = {
  claim_investigation: "Claim investigation",
  rebid_response: "Rebid response",
  handover_gap: "Handover gap",
};

const lifecycleStatusLabels: Record<string, string> = {
  open: "In progress",
  resolved: "Completed",
  evidence_missing: "Timing evidence needed",
};

const milestoneLabels: Record<string, string> = {
  claim_received: "Claim received",
  cause_confirmed: "Cause confirmed",
  rebid_started: "Rebid started",
  response_submitted: "Response submitted",
  handover_started: "Handover started",
  handover_completed: "Handover completed",
};

const timeAxisLabels: Record<string, string> = {
  event_occurred_at: "Event date",
  created_at: "Record creation date",
};

const relationTargetLabels: Record<string, string> = {
  order: "Order",
  project: "Project",
  sales: "Sales",
  business_management: "Business management",
};

const lifecycleNextActions: Record<string, string> = {
  open: "Open the start evidence and track the next observed event.",
  resolved: "Open the start and end evidence, then review the elapsed time.",
  evidence_missing: "Find and connect the required start and end evidence, then review the refreshed interval.",
};

function controlledLabel(code: string, fallback: string, labels: Record<string, string>): string {
  return t(labels[code] ?? fallback);
}

type Props = {
  accessToken: string;
  externalOnly?: boolean;
  onOpenPost: (postId: string) => void;
};

/** Shows quantified operational cases and opens their cited source posts. */
export function OperationsDashboard({ accessToken, externalOnly = false, onOpenPost }: Props) {
  useLocale();
  const [data, setData] = useState<OperationsDashboardResponse | null>(null);
  const [error, setError] = useState(false);
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const [submittedPeriod, setSubmittedPeriod] = useState<[string, string]>(["", ""]);
  const [retryCount, setRetryCount] = useState(0);
  const [voiceSummary, setVoiceSummary] = useState<VoiceSummary | null>(null);
  const [voiceSummaryError, setVoiceSummaryError] = useState(false);
  const [voiceRetryCount, setVoiceRetryCount] = useState(0);

  useEffect(() => {
    let active = true;
    setError(false);
    setData(null);
    fetchOperationsDashboard(accessToken, ...submittedPeriod, externalOnly)
      .then((value) => active && setData(value))
      .catch(() => active && setError(true));
    return () => { active = false; };
  }, [accessToken, externalOnly, submittedPeriod, retryCount]);

  useEffect(() => {
    let active = true;
    setVoiceSummary(null);
    setVoiceSummaryError(false);
    if (externalOnly) return () => { active = false; };
    fetchVoiceTaxonomySummary(accessToken, ...submittedPeriod)
      .then((value) => active && setVoiceSummary(value))
      .catch(() => active && setVoiceSummaryError(true));
    return () => { active = false; };
  }, [accessToken, externalOnly, submittedPeriod, voiceRetryCount]);

  return <>
    <form className="dashboard-period-form" onSubmit={(event) => {
      event.preventDefault();
      setSubmittedPeriod([periodStart, periodEnd]);
    }}>
      <label>{t("Start date")}<input type="date" value={periodStart} max={periodEnd || undefined} onChange={(event) => setPeriodStart(event.target.value)} /></label>
      <label>{t("End date")}<input type="date" value={periodEnd} min={periodStart || undefined} onChange={(event) => setPeriodEnd(event.target.value)} /></label>
      <button type="submit" className="btn-secondary">{t("Apply period")}</button>
    </form>
    {error ? (
      <section className="operations-dashboard" aria-labelledby="dashboard-heading">
        <h2 id="dashboard-heading">{t("Operations evidence dashboard")}</h2>
        <p role="alert">{t("Dashboard evidence could not be loaded.")}</p>
        <button type="button" className="btn-secondary" onClick={() => setRetryCount((count) => count + 1)}>{t("Retry")}</button>
      </section>
    ) : data ? (
      <OperationsDashboardView data={data} externalOnly={externalOnly} onOpenPost={onOpenPost} />
    ) : null}
    {!externalOnly && voiceSummary ? <VoiceTaxonomySummary data={voiceSummary} /> : null}
    {!externalOnly && voiceSummaryError ? (
      <section className="operations-dashboard" aria-labelledby="voice-summary-error-heading">
        <h2 id="voice-summary-error-heading">{t("Voice evidence overview")}</h2>
        <p role="alert">{t("Voice evidence could not be loaded.")}</p>
        <button type="button" className="btn-secondary" onClick={() => setVoiceRetryCount((count) => count + 1)}>{t("Retry voice evidence")}</button>
      </section>
    ) : null}
    {(!data && !error) || (!externalOnly && !voiceSummary && !voiceSummaryError) ? (
      <div role="status">
        {!data && !error ? <p>{t("Loading dashboard evidence...")}</p> : null}
        {!externalOnly && !voiceSummary && !voiceSummaryError ? <p>{t("Loading voice evidence...")}</p> : null}
      </div>
    ) : null}
  </>;
}

/** Renders a completed Dashboard response for runtime and Storybook scenes. */
export function OperationsDashboardView({ data, externalOnly = false, onOpenPost }: { data: OperationsDashboardResponse; externalOnly?: boolean; onOpenPost: (postId: string) => void }) {
  useLocale();
  const cases = externalOnly ? data.cases.filter((item) => item.case_kind_code === "external_information") : data.cases;
  const observedProjectEvents = Object.entries(
    cases.reduce<Record<string, typeof cases>>((groups, item) => {
      const projects = item.project_names ?? (item.project_name ? [item.project_name] : []);
      projects.forEach((project) => (groups[project] ??= []).push(item));
      return groups;
    }, {}),
  );
  return (
    <section className="operations-dashboard" aria-labelledby="dashboard-heading">
      <header className="operations-dashboard-heading">
        <div><p className="dashboard-eyebrow">{data.period_label}</p><h2 id="dashboard-heading">{t(externalOnly ? "External information" : "Operations evidence dashboard")}</h2></div>
        <p>{t("Select a value, then open its source post to confirm the next action.")}</p>
      </header>
      <dl className="dashboard-metrics">
        {!externalOnly ? <div><dt>{t("All posts")}</dt><dd>{data.total_post_count}</dd></div> : null}
        {!externalOnly ? <div><dt>{t("Cited case events")}</dt><dd>{data.total_event_count}</dd></div> : null}
        <div><dt>{t("External information")}</dt><dd>{tf(externalOnly ? "{count} posts" : "{count} posts · {percent}%", { count: data.external_post_count, percent: data.external_percent.toFixed(1) })}</dd></div>
        {!externalOnly ? <div><dt>{t("Awaiting analysis")}</dt><dd>{data.pending_analysis_count}</dd></div> : null}
        {!externalOnly ? <div><dt>{t("Analysis failed")}</dt><dd>{data.failed_analysis_count}</dd></div> : null}
      </dl>
      {!externalOnly ? (
        <section className="dashboard-case-metrics" aria-labelledby="case-metrics-heading">
          <h3 id="case-metrics-heading">{t("Status by work type")}</h3>
          <dl className="dashboard-metrics">
            {data.case_metrics.map((metric) => (
              <div key={metric.case_kind_code}>
                <dt>{controlledLabel(metric.case_kind_code, metric.case_kind_label, caseKindLabels)}</dt>
                <dd>{tf("{events} case events · {posts} posts", { events: metric.event_count, posts: metric.post_count })}</dd>
              </div>
            ))}
          </dl>
        </section>
      ) : null}
      {!externalOnly ? (
        <section className="dashboard-lifecycle-summary" aria-labelledby="lifecycle-summary-heading">
          <h3 id="lifecycle-summary-heading">{t("Observed processing intervals")}</h3>
          <p>{t("Compare elapsed time for items with observed start and end events.")}</p>
          <dl className="dashboard-lifecycle-metrics">
            {data.lifecycle_metrics.map((metric) => (
              <div key={metric.lifecycle_kind_code}>
                <dt>{controlledLabel(metric.lifecycle_kind_code, metric.lifecycle_kind_label, lifecycleLabels)}</dt>
                <dd>{tf("{open} in progress · {resolved} completed · {missing} need timing evidence", { open: metric.open_case_count, resolved: metric.resolved_case_count, missing: metric.evidence_missing_case_count })}</dd>
              </div>
            ))}
          </dl>
        </section>
      ) : null}
      {!externalOnly ? (
        <TopicContextInfluence data={data} onOpenPost={onOpenPost} />
      ) : null}
      {!externalOnly && observedProjectEvents.length ? (
        <section className="dashboard-journeys" aria-labelledby="project-observed-events-heading">
          <h3 id="project-observed-events-heading">{t("Observed events by project")}</h3>
          {observedProjectEvents.map(([project, events]) => (
            <div key={project} className="dashboard-journey">
              <h4>{project}</h4>
              <ol>
                {[...(events ?? [])].sort((left, right) => left.occurred_at.localeCompare(right.occurred_at)).map((event) => (
                  <li key={`${event.post_id}-${event.case_kind_code}`}>
                    <button type="button" onClick={() => onOpenPost(event.post_id)}>
                      <time dateTime={event.occurred_at}>{event.occurred_at.slice(0, 10)}</time>
                      <span>{controlledLabel(event.case_kind_code, event.case_kind_label, caseKindLabels)}</span>
                    </button>
                  </li>
                ))}
              </ol>
            </div>
          ))}
        </section>
      ) : null}
      <div className="dashboard-case-grid">
        {cases.map((item) => (
          <article key={`${item.post_id}-${item.case_kind_code}`} className="dashboard-case-card">
            <div className="dashboard-case-title"><span>{controlledLabel(item.case_kind_code, item.case_kind_label, caseKindLabels)}</span><strong>{item.project_name ?? t("Finding a related project")}</strong></div>
            <h3>{item.summary_text}</h3>
            <blockquote>{item.evidence_text}</blockquote>
            {item.lifecycles.length ? (
              <section className="dashboard-case-lifecycles" aria-label={t("Observed processing intervals")}>
                {item.lifecycles.map((lifecycle) => (
                  <article key={lifecycle.lifecycle_kind_code} className="dashboard-lifecycle-row">
                    <header><h4>{controlledLabel(lifecycle.lifecycle_kind_code, lifecycle.lifecycle_kind_label, lifecycleLabels)}</h4><strong>{controlledLabel(lifecycle.status_code, lifecycle.status_label, lifecycleStatusLabels)}</strong></header>
                    {lifecycle.elapsed_seconds !== null ? <p>{t("Confirmed elapsed time")} <b>{formatElapsed(lifecycle.elapsed_seconds)}</b></p> : <p>{t("Elapsed time is calculated after both required start and end evidence are observed.")}</p>}
                    <ol>
                      {[lifecycle.start_milestone, lifecycle.end_milestone].filter((milestone) => milestone !== null).map((milestone) => (
                        <li key={milestone.milestone_type_code}>
                          <time dateTime={milestone.observed_at}>{milestone.observed_at}</time>
                          <span>{controlledLabel(milestone.milestone_type_code, milestone.milestone_type_label, milestoneLabels)} · {controlledLabel(milestone.time_axis_code, milestone.time_axis_label, timeAxisLabels)}</span>
                          <button type="button" className="btn-link" onClick={() => onOpenPost(milestone.evidence_post_id)}>{tf("Open {label} evidence", { label: controlledLabel(milestone.milestone_type_code, milestone.milestone_type_label, milestoneLabels) })}</button>
                        </li>
                      ))}
                    </ol>
                    <p className="dashboard-next-action">{t("Next action")}: {t(lifecycleNextActions[lifecycle.status_code] ?? lifecycle.next_action_text)}</p>
                  </article>
                ))}
              </section>
            ) : null}
            <dl>{item.facts.map((fact) => { const label = controlledLabel(fact.fact_type_code, fact.fact_type_label, factTypeLabels); const targetLabel = fact.relation_target_kind_code ? controlledLabel(fact.relation_target_kind_code, fact.relation_target_kind_label ?? fact.relation_target_kind_code, relationTargetLabels) : null; return <div key={`${fact.fact_type_code}-${fact.value_text}`}><dt>{label}{targetLabel ? ` · ${targetLabel}` : ""}</dt><dd>{fact.value_text} <button type="button" className="btn-link" onClick={() => onOpenPost(fact.evidence_post_id)}>{tf("Open {label} evidence", { label })}</button></dd></div>; })}</dl>
            {item.missing_facts.length ? (
              <section className="dashboard-missing-facts" aria-label={t("Items requiring additional evidence")}>
                <h4>{t("Additional evidence needed")}</h4>
                <ul>{item.missing_facts.map((fact) => <li key={fact.fact_type_code}>{tf("{label}: Find and connect the related evidence, then review the refreshed result.", { label: controlledLabel(fact.fact_type_code, fact.fact_type_label, factTypeLabels) })}</li>)}</ul>
              </section>
            ) : null}
            <button type="button" className="btn-secondary" onClick={() => onOpenPost(item.evidence_post_id)}>{t("Open classification evidence")}</button>
          </article>
        ))}
      </div>
      {cases.length === 0 && (externalOnly || data.failed_analysis_count === 0) ? (
        <p role="status">{t(externalOnly ? "No external information was classified in this period. Check the period or your access scope." : data.pending_analysis_count > 0 ? "No evidence has completed analysis in this period. Process the awaiting items first." : "No evidence can be analyzed in this period. Check the period or your access scope.")}</p>
      ) : null}
      {!externalOnly && data.failed_analysis_count > 0 ? <p role="alert">{tf("Reprocess {count} failed analyses, then check again for missing evidence.", { count: data.failed_analysis_count })}</p> : null}
    </section>
  );
}

/** Renders persisted ADR-0210 producer evidence without calculating a local score. */
export function TopicContextInfluence({ data, onOpenPost }: { data: OperationsDashboardResponse; onOpenPost: (postId: string) => void }) {
  const topicContext = data.topic_context;
  return (
    <section className="dashboard-topic-context" aria-labelledby="topic-context-heading">
      <header>
        <div><p className="dashboard-eyebrow">{t("Post influence")}</p><h3 id="topic-context-heading">{t("Important posts over time")}</h3></div>
        <p>{t("Compare how topic trends and organization-level results change when a post is excluded.")}</p>
      </header>
      {topicContext.status_code === "unavailable" ? (
        <div className="dashboard-topic-unavailable" role="status">
          <strong>{t("Post influence is not available yet.")}</strong>
          <p>{t("Confirm event dates and organization memberships for the selected posts, then run the analysis again.")}</p>
        </div>
      ) : (
        <>
          <p>{t("Compare each post's influence and uncertainty, then open its source evidence.")}</p>
          <div className="dashboard-topic-list">
            {topicContext.topics.map((topic) => (
              <details key={topic.topic_index} className="dashboard-topic" open>
                <summary>{tf("Topic {number}", { number: topic.topic_index + 1 })} · {topic.activity_intervals.map((interval) => t(topicStateLabels[interval.state_code])).join(" / ")}</summary>
                <ul className="dashboard-topic-timeline" aria-label={tf("Topic {number} status over time", { number: topic.topic_index + 1 })}>
                  {topic.activity_intervals.map((interval) => (
                    <li key={`${interval.valid_from}-${interval.state_code}`}>
                      <strong>{t(topicStateLabels[interval.state_code])}</strong> <time dateTime={interval.valid_from}>{interval.valid_from.slice(0, 10)}</time>–<time dateTime={interval.valid_to}>{interval.valid_to.slice(0, 10)}</time>
                    </li>
                  ))}
                </ul>
                {topic.lineage_events.length ? <ul className="dashboard-topic-lineage" aria-label={tf("Topic {number} change history", { number: topic.topic_index + 1 })}>
                  {topic.lineage_events.map((event) => <li key={`${event.event_time}-${event.event_code}-${event.target_topic_index ?? "none"}`}><time dateTime={event.event_time}>{event.event_time.slice(0, 10)}</time> · {t(topicEventLabels[event.event_code])}{event.target_topic_index === null ? "" : ` → ${tf("Topic {number}", { number: event.target_topic_index + 1 })}`} <button type="button" className="btn-link" onClick={() => onOpenPost(event.evidence_post_id)}>{t("Open event evidence")}</button></li>)}
                </ul> : null}
                {topic.contexts.map((context) => (
                  <section key={`${context.dimension_code}-${context.context_id}`} className="dashboard-topic-context-group" aria-labelledby={`topic-${topic.topic_index}-${context.dimension_code}-${context.context_id}`}>
                    <h4 id={`topic-${topic.topic_index}-${context.dimension_code}-${context.context_id}`}>{t(dimensionLabels[context.dimension_code])} · {context.context_label}</h4>
                    <div className="dashboard-topic-table-scroll" tabIndex={0} role="region" aria-label={tf("{label} influence table", { label: context.context_label })}>
                      <table>
                        <caption>{t("Compare influence and uncertainty together; identical values are ties.")}</caption>
                        <thead><tr><th scope="col">{t("Event date")}</th><th scope="col">{t("Status")}</th><th scope="col">{t("Influence")}</th><th scope="col">{t("Uncertainty")}</th><th scope="col">{t("Membership value")}</th><th scope="col">{t("Evidence")}</th></tr></thead>
                        <tbody>{context.influences.map((influence) => (
                          <tr key={`${influence.post_id}-${influence.membership_evidence_post_id}`}>
                            <td><time dateTime={influence.occurred_at}>{influence.occurred_at.slice(0, 10)}</time></td>
                            <td>{t(topicStateLabels[influence.topic_state_code])}</td>
                            <td><data value={influence.model_influence}>{influence.model_influence}</data></td>
                            <td>{influence.uncertainty_lower_value}–{influence.uncertainty_upper_value}</td>
                            <td>{influence.membership_weight}</td>
                            <td><button type="button" className="btn-link" onClick={() => onOpenPost(influence.membership_evidence_post_id)}>{t("Open membership evidence")}</button> <button type="button" className="btn-link" onClick={() => onOpenPost(influence.post_id)}>{t("Open influential post")}</button></td>
                          </tr>
                        ))}</tbody>
                      </table>
                    </div>
                  </section>
                ))}
              </details>
            ))}
          </div>
          {topicContext.model_run ? (
            <details className="dashboard-topic-provenance">
              <summary>{t("Review analysis basis")}</summary>
              <dl>
                <div><dt>{t("Knowledge cutoff")}</dt><dd><time dateTime={topicContext.model_run.knowledge_cutoff}>{topicContext.model_run.knowledge_cutoff}</time></dd></div>
                <div><dt>{t("Topic count")}</dt><dd>{topicContext.model_run.topic_count}</dd></div>
              </dl>
            </details>
          ) : null}
        </>
      )}
    </section>
  );
}
