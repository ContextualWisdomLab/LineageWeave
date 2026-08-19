import { splitPostBody, type PostBodySegment } from "./postBodyDisplay";
import { t } from "./i18n";
import type { PostContentUnit, PostImageContent } from "./api";

function renderSegment(segment: PostBodySegment, index: number, imageContent?: PostImageContent) {
  switch (segment.kind) {
    case "text":
      return (
        <p
          key={`post-body-text-${index}`}
          className="post-body-text"
          data-indent-level={segment.indentLevel ?? 0}
          style={
            segment.indentLevel
              ? { paddingInlineStart: `${segment.indentLevel}em` }
              : undefined
          }
        >
          {segment.text}
        </p>
      );
    case "image":
      return (
        <figure key={`post-body-image-${index}`} className="post-embedded-image">
          <img
            src={segment.src}
            alt={`${t("Embedded image at character offset")} ${segment.position}`}
          />
          {imageContent?.caption ? <figcaption>{imageContent.caption}</figcaption> : null}
          {imageContent?.extracted_text ? (
            <details className="post-image-text">
              <summary>{t("Text detected in image")}</summary>
              <p>{imageContent.extracted_text}</p>
            </details>
          ) : null}
          {imageContent?.regions?.length ? (
            <details className="post-image-regions">
              <summary>{t("Image regions")}</summary>
              <ol>
                {imageContent.regions.map((region) => (
                  <li key={region.region_index}>
                    {region.caption || region.extracted_text || t("Unknown")}
                  </li>
                ))}
              </ol>
            </details>
          ) : null}
        </figure>
      );
    default: {
      const _exhaustive: never = segment;
      throw new Error(`unexpected post body segment: ${JSON.stringify(_exhaustive)}`);
    }
  }
}

export function PostBody({
  body,
  imageContent = [],
  structureUnits = [],
}: {
  body: string;
  imageContent?: PostImageContent[];
  structureUnits?: PostContentUnit[];
}) {
  let imageOrdinal = 0;
  let textOrdinal = 0;
  const textUnits = structureUnits.filter((unit) => unit.unit_kind_code !== "image");
  return (
    <div className="post-body">
      {splitPostBody(body).map((segment, index) => {
        const content = segment.kind === "image" ? imageContent[imageOrdinal++] : undefined;
        if (segment.kind !== "text") return renderSegment(segment, index, content);
        const structure = textUnits[textOrdinal++];
        const authoritativeStructure =
          structure?.indent_source_code === "explicit" || structure?.indent_source_code === "llm";
        return renderSegment(
          authoritativeStructure
            ? { ...segment, indentLevel: structure.indent_level || undefined }
            : segment,
          index,
          content,
        );
      })}
    </div>
  );
}
