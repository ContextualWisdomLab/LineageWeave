import { PostBody } from "../PostBody";

export type CutoffKnownBodyProps = {
  /** Title current at the run cutoff. */
  title: string;
  /** Body current at the run cutoff. */
  body: string;
  /** When that revision was written. */
  writtenAt: string;
  /** Analysis-run knowledge cutoff used for as_of. */
  cutoff: string;
};

function clockDate(iso: string): string {
  return iso.slice(0, 10);
}

/**
 * Shows the title/body the analysis run knew.
 *
 * Next action: read this text, then compare it with the live body
 * below before treating the live rewrite as reconstructed evidence.
 */
export function CutoffKnownBody({
  title,
  body,
  writtenAt,
  cutoff,
}: CutoffKnownBodyProps) {
  return (
    <section className="cutoff-known-body" aria-label="Body this run knew">
      <h3>Body this run knew</h3>
      <p className="post-meta">
        {title} · written {clockDate(writtenAt)}, known at cutoff{" "}
        {clockDate(cutoff)}. Compare this text with the live body below.
      </p>
      <PostBody body={body} />
    </section>
  );
}
