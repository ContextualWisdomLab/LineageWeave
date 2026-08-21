import { splitPostBody, type PostBodySegment } from "./postBodyDisplay";
import { t } from "./i18n";
import type { PostContentUnit, PostImageContent } from "./api";
import type { ReactNode } from "react";

function parsePipeDelimitedTable(text: string): string[][] | null {
  const rows = text
    .split(/\r?\n/)
    .map((row) => {
      const cells = row.split("|").map((cell) => cell.trim());
      if (cells[0] === "") cells.shift();
      if (cells[cells.length - 1] === "") cells.pop();
      return cells;
    })
    .filter((row) => !row.every((cell) => /^:?-{3,}:?$/.test(cell)))
    .filter((row) => row.length > 1 && row.some(Boolean));
  if (rows.length < 2 || rows.some((row) => row.length !== rows[0].length)) return null;
  if (rows[0].length < 2) return null;
  return rows;
}

function renderImageText(text: string) {
  const rows = parsePipeDelimitedTable(text);
  if (!rows) return <p>{text}</p>;
  return (
    <table className="post-body-table post-image-text-table">
      <tbody>
        {rows.map((row, rowIndex) => (
          <tr key={`post-image-text-row-${rowIndex}`}>
            {row.map((cell, cellIndex) => (
              <td key={`post-image-text-cell-${rowIndex}-${cellIndex}`}>{cell}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function buyerSafeImageCaption(caption: string | null | undefined): string | undefined {
  const cleaned = caption?.replace(/\s+/g, " ").trim();
  if (!cleaned) return undefined;
  if (
    /^(?:this post is an image(?:\s*[.!?]|.*(?:ask questions|read its text).*)|이 글의 이미지입니다(?:\s*[.!?]|.*(?:Keyman\s*(?:을|를)\s*추출|질문해.*텍스트를\s*읽으세요|이미지\s*안의\s*텍스트를\s*읽으세요).*)|(?:this image|이 이미지는).*(?:Keyman\s*(?:을|를)\s*추출|ask questions|read its text|질문해.*(?:읽으세요|추출하세요)|텍스트를\s*(?:읽으세요|추출하세요)).*)$/i.test(
      cleaned,
    )
  ) {
    return undefined;
  }
  return cleaned;
}

const SAFE_EMBEDDED_IMAGE_SOURCE =
  /^data:image\/(?:png|jpe?g|gif|webp|avif|bmp|x-icon|vnd\.microsoft\.icon);base64,[A-Za-z0-9+/]+={0,2}$/i;

function renderImageEvidence(
  index: number,
  imageContent?: PostImageContent,
  sourceImage?: Extract<PostBodySegment, { kind: "image" }>,
) {
  const caption = buyerSafeImageCaption(imageContent?.caption);
  const sourceImageSrc =
    sourceImage && SAFE_EMBEDDED_IMAGE_SOURCE.test(sourceImage.src) ? sourceImage.src : undefined;
  return (
    <figure key={`post-body-image-${index}`} className="post-embedded-image">
      {sourceImageSrc ? (
        <img src={sourceImageSrc} alt={caption || t("Embedded image")} />
      ) : null}
      {caption || !sourceImageSrc ? (
        <figcaption>{caption || t("Embedded image")}</figcaption>
      ) : null}
      {imageContent?.tags.length ? (
        <p className="post-image-tags">
          <strong>{t("Image tags")}:</strong> {imageContent.tags.join(", ")}
        </p>
      ) : null}
      {imageContent?.extracted_text ? (
        <details className="post-image-text">
          <summary>{t("Text detected in image")}</summary>
          {renderImageText(imageContent.extracted_text)}
        </details>
      ) : null}
      {imageContent?.regions?.length ? (
        <details className="post-image-regions">
          <summary>{t("Image regions")}</summary>
          <ol>
            {imageContent.regions.map((region) => (
              <li key={region.region_index}>
                <span>
                  {buyerSafeImageCaption(region.caption) || region.extracted_text || t("Unknown")}
                </span>
                {region.tags.length ? (
                  <small>
                    {t("Image tags")}: {region.tags.join(", ")}
                  </small>
                ) : null}
              </li>
            ))}
          </ol>
        </details>
      ) : null}
    </figure>
  );
}

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
      return renderImageEvidence(index, imageContent, segment);
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
    unit.unit_kind_code === "table_row"
  );
}

/**
 * Match a persisted unit to its source-rendering counterpart without relying
 * on ordinal position. A table row can occupy a persisted non-text unit while
 * its source display is still one text segment, so ordinal matching shifts
 * indentation for every later unresolved unit.
 */
function normalizedUnitText(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

/**
 * Return direct row counts for each source table in document order.
 *
 * Persisted rows do not currently carry a table identifier. The source body
 * is therefore the smallest trustworthy boundary for adjacent tables; when
 * its row count disagrees with persisted rows, the renderer falls back to the
 * old consecutive-row grouping instead of guessing.
 */
function sourceTableRowGroupSizes(body: string): number[] {
  const document = new DOMParser().parseFromString(body, "text/html");
  return Array.from(document.querySelectorAll("table"))
    .map((table) =>
      Array.from(table.children).reduce((count, child) => {
        const tagName = child.tagName.toLowerCase();
        if (tagName === "tr") return count + 1;
        if (tagName !== "thead" && tagName !== "tbody" && tagName !== "tfoot") return count;
        return count + Array.from(child.children).filter(
          (row) => row.tagName.toLowerCase() === "tr",
        ).length;
      }, 0),
    )
    .filter((rowCount) => rowCount > 0);
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
  const sourceTableGroups = sourceTableRowGroupSizes(body);
  const persistedTableRowCount = structureUnits.filter(isStructuredTableRow).length;
  const hasTrustworthyTableGroups =
    sourceTableGroups.length > 0 &&
    sourceTableGroups.reduce((total, rowCount) => total + rowCount, 0) === persistedTableRowCount;
  let tableGroupOrdinal = 0;
  const sourceTextSegments = splitPostBody(body).filter(
    (segment): segment is Extract<PostBodySegment, { kind: "text" }> => segment.kind === "text",
  );
  const consumedSourceText = new Set<number>();
  const sourceTextForUnit = (unitText: string) => {
    const expected = normalizedUnitText(unitText);
    const sourceIndex = sourceTextSegments.findIndex(
      (segment, candidateIndex) =>
        !consumedSourceText.has(candidateIndex) &&
        normalizedUnitText(segment.text) === expected,
    );
    if (sourceIndex < 0) return undefined;
    consumedSourceText.add(sourceIndex);
    return sourceTextSegments[sourceIndex];
  };
  let index = 0;
  while (index < structureUnits.length) {
    const unit = structureUnits[index];
    if (unit.unit_kind_code === "image") {
      const sourceImage = sourceImages[imageOrdinal++];
      const content = imageContent.find((item) => item.unit_index === unit.unit_index);
      rendered.push(
        sourceImage
          ? renderSegment(sourceImage, index, content)
          : renderImageEvidence(index, content),
      );
      index += 1;
      continue;
    }
    if (isStructuredTableRow(unit)) {
      const rows: PostContentUnit[] = [];
      const expectedRowCount = hasTrustworthyTableGroups
        ? sourceTableGroups[tableGroupOrdinal++]
        : undefined;
      while (
        index < structureUnits.length &&
        isStructuredTableRow(structureUnits[index]) &&
        (expectedRowCount === undefined || rows.length < expectedRowCount)
      ) {
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
    const sourceText = sourceTextForUnit(unit.unit_text);
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
