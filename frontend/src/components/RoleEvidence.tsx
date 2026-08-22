import type { ReactNode } from "react";
import { isGenericTeamActor } from "./roleEvidenceUtils";

export type RoleEvidenceProps = {
  actorContent: ReactNode;
  actorName: string;
  actorTypeCode: string;
  actorTypeLabel: string;
  responsibility: string;
  affiliationName: string | null;
  affiliationCatalogId?: string | null;
  affiliationLabel: string;
  affiliationAriaLabel: string;
  unresolvedLabel: string;
  /** ADR 0141: specific reason the affiliation has no catalog link (tie,
   * no live enrichment client, checked-but-not-corroborated, no entry).
   * Replaces the generic unresolvedLabel when present; falls back to it
   * (today's behavior) when null -- e.g. on a historical row written
   * before the reason was tracked. */
  affiliationUnresolvedReasonLabel?: string | null;
  /** ADR 0141: same idea for the actor itself, when the actor's own
   * catalog link (not the affiliation) is unresolved. Unlike the
   * affiliation case there is no prior generic label to fall back to --
   * this note simply doesn't render when the reason is unknown. */
  actorUnresolvedReasonLabel?: string | null;
  genericUnitNote: string;
  onSelectAffiliation?: (entityId: string, entityName: string) => void;
  /** Other R&R rows affiliated with this one, nested as a sub-list so the
   * relationship reads as a tree instead of flat bullets that each repeat
   * the same "· 소속: X" text. */
  children?: ReactNode;
};

export function RoleEvidence({
  actorContent,
  actorName,
  actorTypeCode,
  actorTypeLabel,
  responsibility,
  affiliationName,
  affiliationCatalogId,
  affiliationLabel,
  affiliationAriaLabel,
  unresolvedLabel,
  affiliationUnresolvedReasonLabel,
  actorUnresolvedReasonLabel,
  genericUnitNote,
  onSelectAffiliation,
  children,
}: RoleEvidenceProps) {
  const genericTeam = isGenericTeamActor(actorTypeCode, actorName);
  const canOpenAffiliation = Boolean(affiliationCatalogId && onSelectAffiliation && affiliationName);
  // The actor's own catalog link being unresolved is the rarer, more
  // actionable signal -- reuse the existing warning border for it. An
  // unresolved *affiliation* stays unflagged here: it's common enough in
  // this dataset that bordering every such row would be alert fatigue,
  // not a useful signal (see docs/product-technical-gap-baseline.md).
  const showsUnresolvedActorBorder = genericTeam || Boolean(actorUnresolvedReasonLabel);

  return (
    <li className={showsUnresolvedActorBorder ? "ontology-role ontology-role-unresolved" : "ontology-role"}>
      <span className={`actor-type-badge actor-type-${actorTypeCode}`}>{actorTypeLabel}</span>{" "}
      {actorContent}
      {actorUnresolvedReasonLabel ? (
        <span className="ontology-role-resolution"> ({actorUnresolvedReasonLabel})</span>
      ) : null}
      {affiliationName ? (
        <span className="rr-affiliation">
          {` · ${affiliationLabel}: `}
          {canOpenAffiliation ? (
            <button
              type="button"
              className="keyman-select ontology-affiliation-link"
              aria-label={affiliationAriaLabel}
              onClick={() => onSelectAffiliation?.(affiliationCatalogId as string, affiliationName)}
            >
              {affiliationName}
            </button>
          ) : (
            <>
              {affiliationName}{" "}
              <span className="ontology-role-resolution">
                ({affiliationUnresolvedReasonLabel ?? unresolvedLabel})
              </span>
            </>
          )}
        </span>
      ) : null}
      {genericTeam ? <span className="ontology-role-note"> · {genericUnitNote}</span> : null}
      {`: ${responsibility}`}
      {children}
    </li>
  );
}
