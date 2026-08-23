/**
 * Visible chip text: ``Demo Corp (DC)`` when a unique SKOS companion is present.
 */
export function organizationAliasCaption(
  displayName: string,
  organizationAlias?: string | null,
): string {
  const alias = (organizationAlias ?? "").trim();
  if (!alias) {
    return displayName;
  }
  return `${displayName} (${alias})`;
}
