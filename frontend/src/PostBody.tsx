import { useState } from "react";
import {
  IMAGE_NOT_READ_HERE,
  UNDECODEABLE_IMAGE,
  splitPostBody,
  type PostBodySegment,
} from "./postBodyDisplay";

function EmbeddedPostImage({ src, position }: { src: string; position: number }) {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return <p className="post-body-text">{UNDECODEABLE_IMAGE}</p>;
  }
  return (
    <figure className="post-embedded-image">
      <img
        src={src}
        alt={`Embedded image at character offset ${position}`}
        onError={() => setFailed(true)}
      />
      <figcaption>{IMAGE_NOT_READ_HERE}</figcaption>
    </figure>
  );
}

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
        <EmbeddedPostImage
          key={`post-body-image-${index}`}
          src={segment.src}
          position={segment.position}
        />
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
