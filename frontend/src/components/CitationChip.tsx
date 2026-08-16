export type CitationChipProps = {
  postId: string;
  postTitle: string;
  onOpenEvidence: (postId: string) => void;
};

/**
 * Opens the cited source post from a reconstruction caption.
 *
 * Next action: click the chip to read the evidence that grounded the claim.
 */
export function CitationChip({
  postId,
  postTitle,
  onOpenEvidence,
}: CitationChipProps) {
  return (
    <button
      type="button"
      className="citation-chip"
      aria-label={`Open evidence: ${postTitle}`}
      onClick={() => onOpenEvidence(postId)}
    >
      {postTitle}
    </button>
  );
}
