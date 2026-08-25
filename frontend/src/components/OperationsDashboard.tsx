import { useEffect, useState } from "react";
import { fetchOperationsDashboard, type OperationsDashboardResponse } from "../api";

function formatElapsed(seconds: number): string {
  const days = Math.floor(seconds / 86_400);
  const hours = Math.floor((seconds % 86_400) / 3_600);
  const minutes = Math.floor((seconds % 3_600) / 60);
  return `${days}일 ${hours}시간 ${minutes}분 ${seconds % 60}초`;
}

const dimensionLabels = {
  business_unit: "사업부",
  process_unit: "PU",
  team: "팀",
  person: "개인",
} as const;

const topicStateLabels = {
  active: "활성",
  dormant: "휴면",
  reactivated: "재활성",
} as const;

type Props = {
  accessToken: string;
  externalOnly?: boolean;
  onOpenPost: (postId: string) => void;
};

/** Shows quantified operational cases and opens their cited source posts. */
export function OperationsDashboard({ accessToken, externalOnly = false, onOpenPost }: Props) {
  const [data, setData] = useState<OperationsDashboardResponse | null>(null);
  const [error, setError] = useState(false);
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const [submittedPeriod, setSubmittedPeriod] = useState<[string, string]>(["", ""]);
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    let active = true;
    setError(false);
    setData(null);
    fetchOperationsDashboard(accessToken, ...submittedPeriod, externalOnly)
      .then((value) => active && setData(value))
      .catch(() => active && setError(true));
    return () => { active = false; };
  }, [accessToken, externalOnly, submittedPeriod, retryCount]);

  return <>
    <form className="dashboard-period-form" onSubmit={(event) => {
      event.preventDefault();
      setSubmittedPeriod([periodStart, periodEnd]);
    }}>
      <label>시작일<input type="date" value={periodStart} max={periodEnd || undefined} onChange={(event) => setPeriodStart(event.target.value)} /></label>
      <label>종료일<input type="date" value={periodEnd} min={periodStart || undefined} onChange={(event) => setPeriodEnd(event.target.value)} /></label>
      <button type="submit" className="btn-secondary">기간 적용</button>
    </form>
    {error ? (
      <section className="operations-dashboard" aria-labelledby="dashboard-heading">
        <h2 id="dashboard-heading">운영 근거 Dashboard</h2>
        <p role="alert">Dashboard 근거를 불러오지 못했습니다.</p>
        <button type="button" className="btn-secondary" onClick={() => setRetryCount((count) => count + 1)}>다시 시도</button>
      </section>
    ) : data ? (
      <OperationsDashboardView data={data} externalOnly={externalOnly} onOpenPost={onOpenPost} />
    ) : (
      <p role="status">Dashboard 근거를 불러오는 중입니다.</p>
    )}
  </>;
}

/** Renders a completed Dashboard response for runtime and Storybook scenes. */
export function OperationsDashboardView({ data, externalOnly = false, onOpenPost }: { data: OperationsDashboardResponse; externalOnly?: boolean; onOpenPost: (postId: string) => void }) {
  const cases = externalOnly ? data.cases.filter((item) => item.case_kind_code === "external_information") : data.cases;
  const journeys = Object.entries(
    cases.reduce<Record<string, typeof cases>>((groups, item) => {
      const projects = item.project_names ?? (item.project_name ? [item.project_name] : []);
      projects.forEach((project) => (groups[project] ??= []).push(item));
      return groups;
    }, {}),
  );
  return (
    <section className="operations-dashboard" aria-labelledby="dashboard-heading">
      <header className="operations-dashboard-heading">
        <div><p className="dashboard-eyebrow">{data.period_label}</p><h2 id="dashboard-heading">{externalOnly ? "외부 정보" : "운영 근거 Dashboard"}</h2></div>
        <p>수치를 선택하면 근거 글에서 다음 조치를 확인할 수 있습니다.</p>
      </header>
      <dl className="dashboard-metrics">
        {!externalOnly ? <div><dt>전체 글</dt><dd>{data.total_post_count}</dd></div> : null}
        {!externalOnly ? <div><dt>분류 Event</dt><dd>{data.total_event_count}</dd></div> : null}
        <div><dt>외부 정보</dt><dd>{data.external_post_count}건{externalOnly ? "" : ` · ${data.external_percent.toFixed(1)}%`}</dd></div>
        {!externalOnly ? <div><dt>분석 대기</dt><dd>{data.pending_analysis_count}</dd></div> : null}
        {!externalOnly ? <div><dt>분석 실패</dt><dd>{data.failed_analysis_count}</dd></div> : null}
      </dl>
      {!externalOnly ? (
        <section className="dashboard-case-metrics" aria-labelledby="case-metrics-heading">
          <h3 id="case-metrics-heading">업무 유형별 현황</h3>
          <dl className="dashboard-metrics">
            {data.case_metrics.map((metric) => (
              <div key={metric.case_kind_code}>
                <dt>{metric.case_kind_label}</dt>
                <dd>{metric.event_count} Event · {metric.post_count}글</dd>
              </div>
            ))}
          </dl>
        </section>
      ) : null}
      {!externalOnly ? (
        <section className="dashboard-lifecycle-summary" aria-labelledby="lifecycle-summary-heading">
          <h3 id="lifecycle-summary-heading">관측된 처리 구간</h3>
          <p>임의 지연 기준 없이, 시작·종료 Event가 모두 확인된 구간만 경과 시간을 계산합니다.</p>
          <dl className="dashboard-lifecycle-metrics">
            {data.lifecycle_metrics.map((metric) => (
              <div key={metric.lifecycle_kind_code}>
                <dt>{metric.lifecycle_kind_label}</dt>
                <dd>진행 중 {metric.open_case_count}건 · 종료 확인 {metric.resolved_case_count}건 · 측정 근거 부족 {metric.evidence_missing_case_count}건</dd>
              </div>
            ))}
          </dl>
        </section>
      ) : null}
      {!externalOnly ? (
        <TopicContextInfluence data={data} onOpenPost={onOpenPost} />
      ) : null}
      {!externalOnly && journeys.length ? (
        <section className="dashboard-journeys" aria-labelledby="project-journey-heading">
          <h3 id="project-journey-heading">프로젝트 여정</h3>
          {journeys.map(([project, events]) => (
            <div key={project} className="dashboard-journey">
              <h4>{project}</h4>
              <ol>
                {[...(events ?? [])].sort((left, right) => left.occurred_at.localeCompare(right.occurred_at)).map((event) => (
                  <li key={`${event.post_id}-${event.case_kind_code}`}>
                    <button type="button" onClick={() => onOpenPost(event.post_id)}>
                      <time dateTime={event.occurred_at}>{event.occurred_at.slice(0, 10)}</time>
                      <span>{event.case_kind_label}</span>
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
            <div className="dashboard-case-title"><span>{item.case_kind_label}</span><strong>{item.project_name ?? "프로젝트 연결 분석 중"}</strong></div>
            <h3>{item.summary_text}</h3>
            <blockquote>{item.evidence_text}</blockquote>
            {item.lifecycles.length ? (
              <section className="dashboard-case-lifecycles" aria-label="관측된 처리 구간">
                {item.lifecycles.map((lifecycle) => (
                  <article key={lifecycle.lifecycle_kind_code} className="dashboard-lifecycle-row">
                    <header><h4>{lifecycle.lifecycle_kind_label}</h4><strong>{lifecycle.status_label}</strong></header>
                    {lifecycle.elapsed_seconds !== null ? <p>확정 경과 시간 <b>{formatElapsed(lifecycle.elapsed_seconds)}</b></p> : <p>경과 시간은 종료 Event가 관측될 때 계산됩니다.</p>}
                    <ol>
                      {[lifecycle.start_milestone, lifecycle.end_milestone].filter((milestone) => milestone !== null).map((milestone) => (
                        <li key={milestone.milestone_type_code}>
                          <time dateTime={milestone.observed_at}>{milestone.observed_at}</time>
                          <span>{milestone.milestone_type_label} · {milestone.time_axis_label}</span>
                          <button type="button" className="btn-link" onClick={() => onOpenPost(milestone.evidence_post_id)}>{milestone.milestone_type_label} 근거 열기</button>
                        </li>
                      ))}
                    </ol>
                    <p className="dashboard-next-action">다음 조치: {lifecycle.next_action_text}</p>
                  </article>
                ))}
              </section>
            ) : null}
            <dl>{item.facts.map((fact) => <div key={`${fact.fact_type_code}-${fact.value_text}`}><dt>{fact.fact_type_label}{fact.relation_target_kind_label ? ` · ${fact.relation_target_kind_label}` : ""}</dt><dd>{fact.value_text} <button type="button" className="btn-link" onClick={() => onOpenPost(fact.evidence_post_id)}>{fact.fact_type_label} 근거 열기</button></dd></div>)}</dl>
            {item.missing_facts.length ? (
              <section className="dashboard-missing-facts" aria-label="추가 확인이 필요한 항목">
                <h4>추가 확인 필요</h4>
                <ul>{item.missing_facts.map((fact) => <li key={fact.fact_type_code}>{fact.fact_type_label}: 권한 범위 내 근거가 없습니다. 관련 원문을 연결하세요.</li>)}</ul>
              </section>
            ) : null}
            <button type="button" className="btn-secondary" onClick={() => onOpenPost(item.evidence_post_id)}>분류 근거 글 열기</button>
          </article>
        ))}
      </div>
      {cases.length === 0 && (externalOnly || data.failed_analysis_count === 0) ? (
        <p role="status">{externalOnly ? "선택 기간에 분류된 외부 정보가 없습니다. 기간이나 접근 범위를 확인하세요." : data.pending_analysis_count > 0 ? "선택 기간에 분석 완료된 근거가 없습니다. 분석 대기 건부터 처리하세요." : "선택 기간에 분석할 수 있는 근거가 없습니다. 기간이나 접근 범위를 확인하세요."}</p>
      ) : null}
      {!externalOnly && data.failed_analysis_count > 0 ? <p role="alert">분석 실패 {data.failed_analysis_count}건을 재처리한 뒤 근거 누락 여부를 다시 확인하세요.</p> : null}
    </section>
  );
}

/** Renders persisted ADR-0210 producer evidence without calculating a local score. */
export function TopicContextInfluence({ data, onOpenPost }: { data: OperationsDashboardResponse; onOpenPost: (postId: string) => void }) {
  const topicContext = data.topic_context;
  return (
    <section className="dashboard-topic-context" aria-labelledby="topic-context-heading">
      <header>
        <div><p className="dashboard-eyebrow">TEPP · fast-mlsirm</p><h3 id="topic-context-heading">시간 흐름별 Topic model influence</h3></div>
        <p>사업 가치가 아닌, 해당 글을 제외했을 때 Topic·조직 수준 모형이 변하는 정도입니다.</p>
      </header>
      {topicContext.status_code === "unavailable" ? (
        <div className="dashboard-topic-unavailable" role="status">
          <strong>Topic model influence를 아직 표시할 수 없습니다.</strong>
          <p>{topicContext.next_action}</p>
          <ul>{topicContext.required_contracts.map((contract) => (
            <li key={contract.authority}>{contract.authority} · <code>{contract.schema_version}</code> · {contract.state_code === "persisted" ? "저장 완료" : "승인 결과 없음"}</li>
          ))}</ul>
        </div>
      ) : (
        <>
          <p>{topicContext.next_action}</p>
          <div className="dashboard-topic-list">
            {topicContext.topics.map((topic) => (
              <details key={topic.topic_index} className="dashboard-topic" open>
                <summary>Topic {topic.topic_index + 1} · {topic.activity_intervals.map((interval) => topicStateLabels[interval.state_code]).join(" / ")}</summary>
                <ul className="dashboard-topic-timeline" aria-label={`Topic ${topic.topic_index + 1} 시간 상태`}>
                  {topic.activity_intervals.map((interval) => (
                    <li key={`${interval.valid_from}-${interval.state_code}`}>
                      <strong>{topicStateLabels[interval.state_code]}</strong> <time dateTime={interval.valid_from}>{interval.valid_from.slice(0, 10)}</time>–<time dateTime={interval.valid_to}>{interval.valid_to.slice(0, 10)}</time>
                    </li>
                  ))}
                </ul>
                {topic.lineage_events.length ? <ul className="dashboard-topic-lineage" aria-label={`Topic ${topic.topic_index + 1} lineage Event`}>
                  {topic.lineage_events.map((event) => <li key={`${event.event_time}-${event.event_code}-${event.target_topic_index ?? "none"}`}><time dateTime={event.event_time}>{event.event_time.slice(0, 10)}</time> · {event.event_code}{event.target_topic_index === null ? "" : ` → Topic ${event.target_topic_index + 1}`}</li>)}
                </ul> : null}
                {topic.contexts.map((context) => (
                  <section key={`${context.dimension_code}-${context.context_id}`} className="dashboard-topic-context-group" aria-labelledby={`topic-${topic.topic_index}-${context.dimension_code}-${context.context_id}`}>
                    <h4 id={`topic-${topic.topic_index}-${context.dimension_code}-${context.context_id}`}>{dimensionLabels[context.dimension_code]} · {context.context_label}</h4>
                    <div className="dashboard-topic-table-scroll" tabIndex={0} role="region" aria-label={`${context.context_label} model influence 표`}>
                      <table>
                        <caption>값이 같으면 동점이며, 순번이나 임의 가중치를 추가하지 않습니다.</caption>
                        <thead><tr><th scope="col">Event 발생일</th><th scope="col">상태</th><th scope="col">Model influence</th><th scope="col">불확실성</th><th scope="col">소속 근거</th><th scope="col">원문</th></tr></thead>
                        <tbody>{context.influences.map((influence) => (
                          <tr key={`${influence.post_id}-${influence.membership_evidence_sha256}`}>
                            <td><time dateTime={influence.occurred_at}>{influence.occurred_at.slice(0, 10)}</time></td>
                            <td>{topicStateLabels[influence.topic_state_code]}</td>
                            <td><data value={influence.model_influence}>{influence.model_influence}</data></td>
                            <td>{influence.uncertainty_lower_value}–{influence.uncertainty_upper_value} · {influence.uncertainty_method_code}</td>
                            <td>weight {influence.membership_weight} · <code>{influence.membership_evidence_sha256}</code></td>
                            <td><button type="button" className="btn-link" onClick={() => onOpenPost(influence.post_id)}>근거 글 열기</button></td>
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
              <summary>모형·실행 근거</summary>
              <dl>
                <div><dt>TEPP run</dt><dd><code>{topicContext.model_run.tepp_run_id}</code></dd></div>
                <div><dt>TEPP snapshot</dt><dd><code>{topicContext.model_run.tepp_snapshot_id}</code></dd></div>
                <div><dt>Snapshot</dt><dd><code>{topicContext.model_run.source_snapshot_sha256}</code></dd></div>
                <div><dt>Knowledge cutoff</dt><dd><time dateTime={topicContext.model_run.knowledge_cutoff}>{topicContext.model_run.knowledge_cutoff}</time></dd></div>
                <div><dt>Posterior draws</dt><dd>{topicContext.model_run.posterior_draw_count} · <code>{topicContext.model_run.posterior_draw_set_id}</code></dd></div>
                <div><dt>fast-mlsirm</dt><dd>{topicContext.model_run.fast_mlsirm_version} · {topicContext.model_run.compute_backend_code} · {topicContext.model_run.precision_code}</dd></div>
              </dl>
            </details>
          ) : null}
        </>
      )}
    </section>
  );
}
