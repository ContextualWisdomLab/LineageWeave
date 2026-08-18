import { splitPostBody } from "../postBodyDisplay";

export const ATTACHMENTS_EMPTY = "이 사건의 첨부파일이 아직 없습니다";

export type AttachmentsProps = {
  body: string | null;
};

export function Attachments({ body }: AttachmentsProps) {
  const images = body === null ? null : splitPostBody(body).filter((segment) => segment.kind === "image");
  return (
    <section className="popup-section" aria-label="첨부파일">
      <h3>첨부파일</h3>
      {images === null ? <p>Loading attachments...</p> : null}
      {images && images.length === 0 ? <p className="popup-placeholder">{ATTACHMENTS_EMPTY}</p> : null}
      {images && images.length > 0
        ? images.map((segment, index) =>
            segment.kind === "image" ? (
              <figure key={`${segment.position}:${index}`} className="post-embedded-image">
                <img
                  src={segment.src}
                  alt={segment.alt || `Embedded image at character offset ${segment.position}`}
                />
              </figure>
            ) : null,
          )
        : null}
    </section>
  );
}
