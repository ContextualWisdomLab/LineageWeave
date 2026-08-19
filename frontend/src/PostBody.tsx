import { splitPostBody, type PostBodySegment } from "./postBodyDisplay";

function renderSegment(segment: PostBodySegment, index: number) {
  switch (segment.kind) {
    case "text":
      return (
        <p key={`post-body-text-${index}`} className="post-body-text">
          {segment.text}
        </p>
      );
    case "image":
      return (
        <figure key={`post-body-image-${index}`} className="post-embedded-image">
          <img
            src={segment.src}
            alt={
              segment.alt ||
              `Embedded image at character offset ${segment.position}`
            }
          />
          <figcaption>
            Image from this post. Extract Keyman or ask a question to read text
            inside it.
          </figcaption>
        </figure>
      );
    default: {
      const _exhaustive: never = segment;
      throw new Error(`unexpected post body segment: ${JSON.stringify(_exhaustive)}`);
    }
  }
}

export function PostBody({ body }: { body: string }) {
  return <div className="post-body">{splitPostBody(body).map(renderSegment)}</div>;
}
