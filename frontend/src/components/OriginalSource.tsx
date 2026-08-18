import { PostBody } from "../PostBody";

export type OriginalSourceProps = {
  body: string | null;
  error?: string | null;
};

export function OriginalSource({ body, error }: OriginalSourceProps) {
  return (
    <section className="popup-section" aria-label="원문">
      <h3>원문</h3>
      {error ? <p className="error">{error}</p> : null}
      {body === null && !error ? <p>Loading source...</p> : null}
      {body !== null ? <PostBody body={body} /> : null}
    </section>
  );
}
