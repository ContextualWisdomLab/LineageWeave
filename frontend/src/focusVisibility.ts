/** Return whether an interactive descendant belongs in a modal focus order. */
export function isFocusableVisible(element: HTMLElement): boolean {
  const collapsedDetails = element.closest("details:not([open])");
  if (collapsedDetails && collapsedDetails.querySelector(":scope > summary") !== element) return false;
  if (element.closest('[hidden], [aria-hidden="true"], [inert]')) return false;
  return (
    typeof element.checkVisibility !== "function" ||
    element.checkVisibility({
      opacityProperty: true,
      visibilityProperty: true,
      checkOpacity: true,
      checkVisibilityCSS: true,
    })
  );
}
