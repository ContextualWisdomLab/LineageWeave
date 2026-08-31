import type {
  WorkerFunctionConstructPayload,
  WorkerFunctionConstructCatalogPayload,
  WorkerFunctionProfilePayload,
} from "../api";
import { workerFunctionPsychologyText } from "../workerFunctionPsychologyI18n";

/** One psychological demand slot inside a worker-function profile. */
export interface WorkerFunctionPsychologySlot {
  heading: string;
  constructs: WorkerFunctionConstructPayload[];
}

function slotLabelFor(label: string): string {
  return label
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

/** Rendered demand profile for one DOT/FJA worker function (ADR 0251). */
export function WorkerFunctionPsychology({
  profile,
  catalog,
  loading = false,
}: {
  profile: WorkerFunctionProfilePayload | null;
  catalog: WorkerFunctionConstructCatalogPayload | null;
  loading?: boolean;
}) {
  const profileSlots: WorkerFunctionPsychologySlot[] = profile
    ? [
        { heading: "Cognitive demands", constructs: profile.cognitive_demands },
        { heading: "Mental workload", constructs: profile.mental_workload_demands },
        { heading: "Affective demands", constructs: profile.affective_demands },
        { heading: "Emotional labor", constructs: profile.emotional_labor_demands },
        { heading: "Behavioral manifestations", constructs: profile.behavioral_manifestations },
        { heading: "Psychomotor behaviors", constructs: profile.psychomotor_behaviors },
      ]
    : [];

  const catalogGroups = catalog
    ? [
        { heading: "Cognitive", constructs: catalog.constructs.cognitive ?? [] },
        { heading: "Affective", constructs: catalog.constructs.affective ?? [] },
        { heading: "Behavioral", constructs: catalog.constructs.behavioral ?? [] },
      ]
    : [];

  return (
    <section className="popup-section" aria-labelledby="worker-psychology-heading">
      <h3 id="worker-psychology-heading">{workerFunctionPsychologyText("Work psychology")}</h3>
      {loading ? (
        <p role="status" className="popup-placeholder">
          {workerFunctionPsychologyText("Work psychology details are not ready. Select a worker function or try again after the catalog finishes loading.")}
        </p>
      ) : null}
      {!loading && profile ? (
        <>
          <p className="post-meta">
            <strong>{profile.function_label}</strong>{" "}
            <span className="post-badge">
              {profile.function_domain} · rank {profile.function_rank}
            </span>
          </p>
          <div className="worker-psychology-slots">
            {profileSlots.map((slot) => (
              <details className="semantic-provenance" key={slot.heading} open>
                <summary>{slot.heading}</summary>
                <ul className="post-evidence-list">
                  {slot.constructs.map((construct) => (
                    <li key={construct.iri}>
                      <strong>{construct.label}</strong>{" "}
                      <span className="post-badge">{slotLabelFor(construct.dimension)}</span>
                      <p>{construct.definition}</p>
                      <p className="post-meta">
                        {workerFunctionPsychologyText("Reference")}: {construct.theoretical_basis}
                      </p>
                    </li>
                  ))}
                  {slot.constructs.length === 0 ? (
                    <li>
                      <span className="post-badge">
                        {workerFunctionPsychologyText("Select a worker function to review its I/O psychology demand profile.")}
                      </span>
                    </li>
                  ) : null}
                </ul>
              </details>
            ))}
          </div>
        </>
      ) : null}
      {catalogGroups.length > 0 ? (
        <>
          <h4>{workerFunctionPsychologyText("Catalog dimensions")}</h4>
          <ul className="post-evidence-list" aria-label={workerFunctionPsychologyText("Catalog dimensions")}>
            {catalogGroups.map((group) => (
              <li key={group.heading}>
                <strong>{group.heading}</strong>{" "}
                <span className="post-badge">{group.constructs.length}</span>
                <ul className="post-evidence-list">
                  {group.constructs.slice(0, 12).map((construct) => (
                    <li key={construct.iri}>
                      <a className="citation-chip" href={construct.iri} target="_blank" rel="noreferrer">
                        {construct.label}
                      </a>
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}
