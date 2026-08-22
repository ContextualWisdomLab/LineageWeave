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
  genericUnitNote,
  onSelectAffiliation,
  children,
}: RoleEvidenceProps) {
  const genericTeam = isGenericTeamActor(actorTypeCode, actorName);
  const canOpenAffiliation = Boolean(affiliationCatalogId && onSelectAffiliation && affiliationName);

  return (
    <li className={genericTeam ? "ontology-role ontology-role-unresolved" : "ontology-role"}>
      <span className={`actor-type-badge actor-type-${actorTypeCode}`}>{actorTypeLabel}</span>{" "}
      {actorContent}
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
              {affiliationName} <span className="ontology-role-resolution">({unresolvedLabel})</span>
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
