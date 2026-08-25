interface TeppAcceptedReceiptProps {
  remoteRunId: string;
}

/** Provider acceptance evidence; it deliberately makes no measurement claim. */
export function TeppAcceptedReceipt({ remoteRunId }: TeppAcceptedReceiptProps) {
  return (
    <p className="post-meta" aria-label="TEPP accepted receipt">
      TEPP accepted remote run {remoteRunId}. Use this identifier when reconciling provider
      evidence.
    </p>
  );
}
