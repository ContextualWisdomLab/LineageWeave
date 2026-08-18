import type { Keyman } from "../api";

export const KEYMEN_EMPTY = "이 사건의 Keyman이 아직 없습니다";

export type KeymenPanelProps = {
  keymen: Keyman[] | null;
  error?: string | null;
};

export function KeymenPanel({ keymen, error }: KeymenPanelProps) {
  return (
    <section className="popup-section" aria-label="Keymen">
      <h3>Keymen</h3>
      {error ? <p className="error">{error}</p> : null}
      {keymen === null && !error ? <p>Loading Keymen...</p> : null}
      {keymen && keymen.length === 0 ? <p className="popup-placeholder">{KEYMEN_EMPTY}</p> : null}
      {keymen && keymen.length > 0 ? (
        <ul>
          {keymen.map((person) => (
            <li key={person.person_id}>
              <strong>{person.person_name}</strong>
              {person.person_side_label ? ` · ${person.person_side_label}` : ""}
              {person.affiliations[0] ? ` · ${person.affiliations[0].organization_name}` : ""}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
