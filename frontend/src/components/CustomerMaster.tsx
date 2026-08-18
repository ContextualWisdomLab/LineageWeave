import type { CurrentUser, Keyman, OrgmetraUnit, UnverifiedCandidate } from "../api";

export const CUSTOMERS_EMPTY = "이 범위의 조직 단위를 아직 받을 수 없습니다";
export const MASTER_KEYMEN_EMPTY = "Keyman이 아직 없습니다";

export type CustomerMasterProps = {
  me: CurrentUser | null;
  orgmetraAvailable: boolean;
  units: OrgmetraUnit[] | null;
  keymen: Keyman[] | null;
  pendingAttach?: UnverifiedCandidate | null;
  attachError?: string | null;
  attachBusy?: boolean;
  onAttachPending?: () => void;
};

export function CustomerMaster({
  me,
  orgmetraAvailable,
  units,
  keymen,
  pendingAttach = null,
  attachError = null,
  attachBusy = false,
  onAttachPending,
}: CustomerMasterProps) {
  const tenant = me?.corporate_entities?.[0]?.entity_name ?? me?.display_name ?? null;
  return (
    <section className="popup-section lineage-home" aria-label="고객 마스터">
      <h2>고객 마스터</h2>
      <p className="post-meta" aria-label="Tenant identity">
        {tenant ? `Tenant · ${tenant}` : "Tenant identity from Keyverse when wired."} Corp / PU
        are Keyverse attributes on this login. This demo uses the existing OIDC login. No
        second login form.
      </p>
      {pendingAttach ? (
        <section className="popup-section" aria-label="온톨로지에 붙이기">
          <h3>온톨로지에 붙이기</h3>
          <p>
            {pendingAttach.status_label} · {pendingAttach.label}
          </p>
          {onAttachPending ? (
            <button type="button" onClick={onAttachPending} disabled={attachBusy}>
              온톨로지에 붙이기
            </button>
          ) : null}
          {attachError ? <p className="popup-placeholder">{attachError}</p> : null}
        </section>
      ) : null}
      <section className="popup-section" aria-label="고객">
        <h3>고객</h3>
        {!orgmetraAvailable || (units && units.length === 0) ? (
          <p className="popup-placeholder">{CUSTOMERS_EMPTY}</p>
        ) : null}
        {units && units.length > 0 ? (
          <ul>
            {units.map((unit) => (
              <li key={unit.unit_id}>
                {unit.unit_label} · {unit.grain_code}
              </li>
            ))}
          </ul>
        ) : null}
      </section>
      <section className="popup-section" aria-label="Keymen">
        <h3>Keymen</h3>
        {keymen && keymen.length === 0 ? <p className="popup-placeholder">{MASTER_KEYMEN_EMPTY}</p> : null}
        {keymen && keymen.length > 0 ? (
          <ul>
            {keymen.map((person) => (
              <li key={person.person_id}>{person.person_name}</li>
            ))}
          </ul>
        ) : null}
      </section>
    </section>
  );
}
