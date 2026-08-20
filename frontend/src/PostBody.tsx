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

function isStructuredTableRow(unit: PostContentUnit): boolean {
  return (
    unit.unit_label === "tr" ||
    unit.unit_label === "w:tr" ||
    unit.unit_label === "markdown_tr" ||
    unit.unit_kind_code === "table_row"
  );
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
  let textOrdinal = 0;
  const sourceTextSegments = splitPostBody(body).filter(
    (segment): segment is Extract<PostBodySegment, { kind: "text" }> => segment.kind === "text",
  );
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
    const sourceText = sourceTextSegments[textOrdinal++];
    const persistedIndent =
      unit.indent_level > 0 &&
      (unit.indent_source_code === "explicit" || unit.indent_source_code === "llm")
        ? unit.indent_level
        : undefined;
    rendered.push(
      renderSegment(
        {
          kind: "text",
          text: unit.unit_text,
          ...(unit.unit_label === "footnote" || sourceText?.role === "footnote"
            ? { role: "footnote" as const }
            : {}),
          ...(persistedIndent ?? sourceText?.indentLevel
            ? { indentLevel: persistedIndent ?? sourceText?.indentLevel }
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
  const hasPersistedStructuralUnits = structureUnits.length > 0;
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
        return renderSegment(segment, index, content);
      })}
    </div>
  );
}
