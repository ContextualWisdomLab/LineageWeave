import type { VoiceTaxonomySummary as Summary } from "../api";
import { t, tf } from "../i18n";

const voiceLabels = {
  voc: "Voice of Customer",
  vocc: "Voice of Customer's customer",
  voco: "Voice of Competitor",
  vom: "Voice of Market",
  vop: "Voice of Partner",
} as const;

export function VoiceTaxonomySummary({ data }: { data: Summary }) {
  return (
    <section className="operations-dashboard" aria-labelledby="voice-summary-heading">
      <h2 id="voice-summary-heading">{t("External voice overview")}</h2>
      <p>{tf("Compare evidence across {count} visible records.", { count: data.total_eligible.toLocaleString() })}</p>
      <dl className="dashboard-metrics-grid">
        <div><dt>{t("Recorded evidence")}</dt><dd>{data.source_count.toLocaleString()}</dd></div>
        <div><dt>{t("Stored semantic evidence")}</dt><dd>{data.derived_count.toLocaleString()}</dd></div>
        <div><dt>{t("Multiple roles observed")}</dt><dd>{data.multi_membership.toLocaleString()}</dd></div>
        <div><dt>{t("Needs review")}</dt><dd>{data.disagreement.toLocaleString()}</dd></div>
        <div><dt>{t("No evidence found")}</dt><dd>{data.unavailable.toLocaleString()}</dd></div>
      </dl>
      <ul className="evidence-list">
        {data.category_memberships.map((category) => (
          <li key={category.voice_concept_code}>
            <strong>{t(voiceLabels[category.voice_concept_code])}</strong>{" "}
            {category.post_count.toLocaleString()} ({category.eligible_percentage.toFixed(1)}%)
          </li>
        ))}
      </ul>
      {data.counts_overlap ? <p>{t("One record may support several relationships, so category counts can overlap.")}</p> : null}
      <p className="dashboard-next-action">{t("Review disagreements and records without evidence before using these relationships.")}</p>
    </section>
  );
}
