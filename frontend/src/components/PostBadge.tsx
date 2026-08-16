export type PostBadgeProps = {
  children: string;
};

/**
 * Marks a list row with a compact status the operator can act on.
 *
 * Next action: read the mark, then open the row it labels.
 */
export function PostBadge({ children }: PostBadgeProps) {
  return <span className="post-badge">{children}</span>;
}
