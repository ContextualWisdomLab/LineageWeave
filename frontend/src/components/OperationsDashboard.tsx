import { useEffect, useState } from "react";
import { fetchOperationsDashboard, type OperationsDashboardResponse } from "../api";

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
    fetchOperationsDashboard(accessToken, ...submittedPeriod)
      .then((value) => active && setData(value))
      .catch(() => active && setError(true));
    return () => { active = false; };
  }, [accessToken, submittedPeriod, retryCount]);

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
        <div><dt>전체 글</dt><dd>{data.total_post_count}</dd></div>
        <div><dt>분류 Event</dt><dd>{data.total_event_count}</dd></div>
        <div><dt>외부 정보</dt><dd>{data.external_post_count}건 · {data.external_percent.toFixed(1)}%</dd></div>
        <div><dt>분석 대기</dt><dd>{data.pending_analysis_count}</dd></div>
        <div><dt>분석 실패</dt><dd>{data.failed_analysis_count}</dd></div>
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
            <dl>{item.facts.map((fact) => <div key={`${fact.fact_type_code}-${fact.value_text}`}><dt>{fact.fact_type_label}</dt><dd>{fact.value_text} <button type="button" className="btn-link" onClick={() => onOpenPost(fact.evidence_post_id)}>{fact.fact_type_label} 근거 열기</button></dd></div>)}</dl>
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
      {cases.length === 0 && data.failed_analysis_count === 0 ? (
        <p role="status">{data.pending_analysis_count > 0 ? "선택 기간에 분석 완료된 근거가 없습니다. 분석 대기 건부터 처리하세요." : "선택 기간에 분석할 수 있는 근거가 없습니다. 기간이나 접근 범위를 확인하세요."}</p>
      ) : null}
      {data.failed_analysis_count > 0 ? <p role="alert">분석 실패 {data.failed_analysis_count}건을 재처리한 뒤 근거 누락 여부를 다시 확인하세요.</p> : null}
    </section>
  );
}
