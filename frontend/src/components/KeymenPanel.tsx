import type { Keyman } from "../api";

export const KEYMEN_EMPTY = "이 사건의 Keyman이 아직 없습니다";

export type KeymenPanelProps = {
  keymen: Keyman[] | null;
  error?: string | null;
};

function peopleOnSide(keymen: Keyman[], sideCode: "our_side" | "counterparty"): Keyman[] {
  return keymen.filter((person) => person.person_side_code === sideCode);
}

function SideList({ heading, people }: { heading: string; people: Keyman[] }) {
  return (
    <section className="popup-section" aria-label={heading}>
      <h4>{heading}</h4>
      {people.length === 0 ? (
        <p className="popup-placeholder">{KEYMEN_EMPTY}</p>
      ) : (
        <ul>
          {people.map((person) => (
            <li key={person.person_id}>
              <strong>{person.person_name}</strong>
              {person.affiliations[0] ? ` · ${person.affiliations[0].organization_name}` : ""}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function KeymenPanel({ keymen, error }: KeymenPanelProps) {
  return (
    <section className="popup-section" aria-label="Keymen">
      <h3>Keymen</h3>
      {error ? <p className="error">{error}</p> : null}
      {keymen === null && !error ? <p>Loading Keymen...</p> : null}
      {keymen && keymen.length === 0 ? <p className="popup-placeholder">{KEYMEN_EMPTY}</p> : null}
      {keymen && keymen.length > 0 ? (
        <>
          <SideList heading="Our side" people={peopleOnSide(keymen, "our_side")} />
          <SideList heading="Counterparty" people={peopleOnSide(keymen, "counterparty")} />
        </>
      ) : null}
    </section>
  );
}
