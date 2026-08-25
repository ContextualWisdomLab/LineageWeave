/** Return whether selecting a post requires discarding the currently focused graph. */
export function focusedGraphMustReset(currentPostId: string | null, nextPostId: string): boolean {
  return currentPostId !== nextPostId;
}
