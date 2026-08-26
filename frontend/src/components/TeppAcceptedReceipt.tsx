/** Provider acceptance evidence; it deliberately makes no measurement claim. */
export function TeppAcceptedReceipt() {
  return (
    <p className="post-meta" aria-label="Measurement request accepted">
      Measurement request accepted. Refresh this run to check whether results are ready.
    </p>
  );
}
