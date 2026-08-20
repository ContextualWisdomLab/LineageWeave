import {
  splitMarkdownTableBody,
  splitPostBody,
  type MarkdownBodyBlock,
  type PostBodySegment,
} from "./postBodyDisplay";
import { t } from "./i18n";
import type { PostContentUnit, PostImageContent } from "./api";
import type { ReactNode } from "react";

function renderSegment(segment: PostBodySegment, index: number, imageContent?: PostImageContent) {
  switch (segment.kind) {
    case "text":
      return (
        <p
          key={`post-body-text-${index}`}
          className={`post-body-text${segment.role === "footnote" ? " post-body-footnote" : ""}`}
          data-content-kind={segment.role ?? "text"}
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
            alt={t("Embedded image")}
          />
          {imageContent?.caption ? <figcaption>{imageContent.caption}</figcaption> : null}
          {imageContent?.extracted_text ? (
            <details className="post-image-text">
              <summary>{t("Text detected in image")}</summary>
              {renderExtractedText(imageContent.extracted_text)}
            </details>
          ) : null}
          {imageContent?.regions?.length ? (
            <details className="post-image-regions">
              <summary>{t("Image regions")}</summary>
              <ol>
                {imageContent.regions.map((region) => (
                  <li key={region.region_index}>
                    {region.caption ? <p>{region.caption}</p> : null}
                    {region.extracted_text ? (
                      <div className="post-image-region-text">
                        {renderExtractedText(region.extracted_text)}
                      </div>
                    ) : region.caption ? null : (
                      t("Unknown")
                    )}
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

function isStructuredTableRow(unit: PostContentUnit): boolean {
  return unit.unit_label === "tr" || unit.unit_label === "w:tr" || unit.unit_label === "markdown_tr";
}

function renderStructuredUnits(
  body: string,
  structureUnits: PostContentUnit[],
  imageContent: PostImageContent[],
): ReactNode[] {
  const sourceImages = splitPostBody(body).filter(
    (segment): segment is Extract<PostBodySegment, { kind: "image" }> => segment.kind === "image",
  );
  const rendered: ReactNode[] = [];
  let imageOrdinal = 0;
  let index = 0;
  while (index < structureUnits.length) {
    const unit = structureUnits[index];
    if (unit.unit_kind_code === "image") {
      const sourceImage = sourceImages[imageOrdinal++];
      const content = imageContent.find((item) => item.unit_index === unit.unit_index);
      rendered.push(
        sourceImage
          ? renderSegment(sourceImage, index, content)
          : renderSegment({ kind: "text", text: unit.unit_text }, index, content),
      );
      index += 1;
      continue;
    }
    if (isStructuredTableRow(unit)) {
      const rows: PostContentUnit[] = [];
      while (index < structureUnits.length && isStructuredTableRow(structureUnits[index])) {
        rows.push(structureUnits[index]);
        index += 1;
      }
      rendered.push(
        <table className="post-body-table" key={`post-body-table-${index}`}>
          <tbody>
            {rows.map((row, rowIndex) => (
              <tr key={`post-body-table-row-${row.unit_index}-${rowIndex}`}>
                {row.unit_text.split(/\s*\|\s*/).map((cell, cellIndex) => (
                  <td key={`post-body-table-cell-${row.unit_index}-${cellIndex}`}>{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>,
      );
      continue;
    }
    rendered.push(
      renderSegment(
        {
          kind: "text",
          text: unit.unit_text,
          ...(unit.unit_label === "footnote" ? { role: "footnote" as const } : {}),
          ...(unit.indent_level > 0 &&
          (unit.indent_source_code === "explicit" || unit.indent_source_code === "llm")
            ? { indentLevel: unit.indent_level }
            : {}),
        },
        index,
      ),
    );
    index += 1;
  }
  return rendered;
}

function renderMarkdownBlocks(blocks: MarkdownBodyBlock[]): ReactNode[] {
  return blocks.map((block, blockIndex) => {
    if (block.kind === "prose") {
      return <p key={`post-body-markdown-prose-${blockIndex}`}>{block.text}</p>;
    }
    const [header, ...rows] = block.rows;
    return (
      <table className="post-body-table" key={`post-body-markdown-table-${blockIndex}`}>
        <thead>
          <tr>
            {header.map((cell, cellIndex) => (
              <th key={`post-body-markdown-header-${blockIndex}-${cellIndex}`} scope="col">
                {cell}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={`post-body-markdown-row-${blockIndex}-${rowIndex}`}>
              {row.map((cell, cellIndex) => (
                <td key={`post-body-markdown-cell-${blockIndex}-${rowIndex}-${cellIndex}`}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    );
  });
}

function renderExtractedText(text: string): ReactNode {
  const markdownBlocks = splitMarkdownTableBody(text);
  return markdownBlocks ? renderMarkdownBlocks(markdownBlocks) : <p>{text}</p>;
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
  const hasPersistedStructuralUnits = structureUnits.some(
    (unit) =>
      isStructuredTableRow(unit) ||
      unit.unit_label === "footnote" ||
      unit.indent_source_code === "explicit" ||
      unit.indent_source_code === "llm",
  );
  if (hasPersistedStructuralUnits) {
    return <div className="post-body">{renderStructuredUnits(body, structureUnits, imageContent)}</div>;
  }
  const markdownBlocks = !hasPersistedStructuralUnits ? splitMarkdownTableBody(body) : null;
  if (markdownBlocks) {
    return <div className="post-body">{renderMarkdownBlocks(markdownBlocks)}</div>;
  }
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
