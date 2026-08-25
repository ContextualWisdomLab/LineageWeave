import { organizationAliasCaption } from "./organizationAliasCaption";

export type OrganizationAliasChipProps = {
  displayName: string;
  organizationAlias?: string | null;
  ariaLabel: string;
  onSelect: () => void;
};

/**
 * Opens the cataloged organization. The parenthetical is the other
 * corroborated SKOS label, never an invented abbreviation.
 *
 * Next action: click the chip to walk that organization.
 */
export function OrganizationAliasChip({
  displayName,
  organizationAlias,
  ariaLabel,
  onSelect,
}: OrganizationAliasChipProps) {
  return (
    <button type="button" className="keyman-select" aria-label={ariaLabel} onClick={onSelect}>
      {organizationAliasCaption(displayName, organizationAlias)}
    </button>
  );
}
