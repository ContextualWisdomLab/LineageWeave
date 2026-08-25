/** Return whether an interactive descendant belongs in a modal focus order. */
export function isFocusableVisible(element: HTMLElement): boolean {
  if (element.closest('details:not([open]), [hidden], [aria-hidden="true"], [inert]')) return false;
  return (
    typeof element.checkVisibility !== "function" ||
    element.checkVisibility({ opacityProperty: true, visibilityProperty: true })
  );
}
