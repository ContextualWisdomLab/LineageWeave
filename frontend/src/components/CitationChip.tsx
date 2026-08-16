export type CitationChipProps = {
  postId: string;
  postTitle: string;
  onOpenEvidence: (postId: string) => void;
};

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
