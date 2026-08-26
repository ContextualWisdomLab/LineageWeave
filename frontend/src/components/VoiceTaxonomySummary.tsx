import type { VoiceTaxonomySummary as Summary } from "../api";

const voiceLabels = {
  voc: "고객",
  vocc: "고객의 고객",
  voco: "경쟁사",
  vom: "시장",
  vop: "파트너",
} as const;

export function VoiceTaxonomySummary({ data }: { data: Summary }) {
  return (
    <section className="operations-dashboard" aria-labelledby="voice-summary-heading">
      <h2 id="voice-summary-heading">외부 목소리 분류 현황</h2>
      <p>전체 {data.total_eligible.toLocaleString()}건 중 근거를 확인한 분류를 비교합니다.</p>
      <dl className="dashboard-metrics-grid">
        <div><dt>원천 분류</dt><dd>{data.source_count.toLocaleString()}건</dd></div>
        <div><dt>의미 분류</dt><dd>{data.derived_count.toLocaleString()}건</dd></div>
        <div><dt>다중 소속</dt><dd>{data.multi_membership.toLocaleString()}건</dd></div>
        <div><dt>재검토 필요</dt><dd>{data.disagreement.toLocaleString()}건</dd></div>
        <div><dt>근거 대기</dt><dd>{data.unavailable.toLocaleString()}건</dd></div>
      </dl>
      <ul className="evidence-list">
        {data.category_memberships.map((category) => (
          <li key={category.voice_concept_code}>
            <strong>{voiceLabels[category.voice_concept_code]}</strong>{" "}
            {category.post_count.toLocaleString()}건 ({category.eligible_percentage.toFixed(1)}%)
          </li>
        ))}
      </ul>
      {data.counts_overlap ? <p>한 글이 여러 관계에 해당할 수 있으므로 항목별 건수는 중복될 수 있습니다.</p> : null}
      <p className="dashboard-next-action">불일치와 근거 대기 기록을 확인한 뒤 분류를 활용하세요.</p>
    </section>
  );
}
