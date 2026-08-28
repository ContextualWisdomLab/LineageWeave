import type { VoiceTaxonomySummary as Summary } from "../api";
import { t, tf } from "../i18n";

const voiceLabels = {
  voc: "Voice of Customer",
  vocc: "Voice of Customer's customer",
  voco: "Voice of Competitor",
  vom: "Voice of Market",
  vop: "Voice of Partner",
  vos: "Voice of Supplier",
  voe: "Voice of Employee",
  vob: "Voice of Business",
  vor: "Voice of Regulator",
  voi: "Voice of Investor",
  voso: "Voice of Society",
  vops: "Voice of Process",
} as const;

export function VoiceTaxonomySummary({ data }: { data: Summary }) {
  return (
    <section className="operations-dashboard" aria-labelledby="voice-summary-heading">
      <h2 id="voice-summary-heading">{t("Voice evidence overview")}</h2>
      <p>{tf("Compare voice classifications across {count} visible records.", { count: data.total_eligible.toLocaleString() })}</p>
      <dl className="dashboard-metrics-grid">
        <div><dt>{t("Recorded evidence")}</dt><dd>{data.source_count.toLocaleString()}</dd></div>
        <div><dt>{t("Additional classified records")}</dt><dd>{data.derived_count.toLocaleString()}</dd></div>
        <div><dt>{t("Records in multiple voice categories")}</dt><dd>{data.multi_membership.toLocaleString()}</dd></div>
        <div><dt>{t("Needs review")}</dt><dd>{data.disagreement.toLocaleString()}</dd></div>
        <div><dt>{t("Records without voice evidence")}</dt><dd>{data.unavailable.toLocaleString()}</dd></div>
      </dl>
      <ul className="evidence-list">
        {data.category_memberships.map((category) => (
          <li key={category.voice_concept_code}>
            <strong>{t(voiceLabels[category.voice_concept_code])}</strong>{" "}
            {category.post_count.toLocaleString()} ({category.eligible_percentage.toFixed(1)}%)
          </li>
        ))}
      </ul>
      {data.counts_overlap ? <p>{t("One record may support several voice categories, so category counts can overlap.")}</p> : null}
      <p className="dashboard-next-action">{t("Review disagreements and records without voice evidence before using these classifications.")}</p>
    </section>
  );
}
