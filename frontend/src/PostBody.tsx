import {
  decodeHtmlEntities,
  splitPostBody,
  splitScriptRuns,
  normalizeScriptText,
  type PostBodySegment,
} from "./postBodyDisplay";
import { t } from "./i18n";
import type { PostContentUnit, PostImageContent, PostImageRegion } from "./api";
import { Fragment, type ReactNode } from "react";

function renderStyledText(text: string): ReactNode {
  return splitScriptRuns(text).map((run, index) => {
    if (run.script === "super") {
      return <sup key={`post-body-sup-${index}`}>{run.text}</sup>;
    }
    if (run.script === "sub") {
      return <sub key={`post-body-sub-${index}`}>{run.text}</sub>;
    }
    return <Fragment key={`post-body-text-run-${index}`}>{run.text}</Fragment>;
  });
}

function parsePipeDelimitedTable(text: string, requireSeparator = true): string[][] | null {
  const rawRows = text
    .split(/\r?\n/)
    .map((row) => {
      const cells = row.split("|").map((cell) => cell.trim());
      if (cells[0] === "") cells.shift();
      if (cells[cells.length - 1] === "") cells.pop();
      return cells;
    });
  const separatorIndex = rawRows.findIndex(
    (row) => row.length > 1 && row.every((cell) => /^:?-{3,}:?$/.test(cell)),
  );
  if (requireSeparator && separatorIndex !== 1) return null;
  const rows = rawRows
    .filter((_row, rowIndex) => rowIndex !== separatorIndex)
    .filter((row) => row.length > 1 && row.some(Boolean));
  if (rows.length < 2 || rows.some((row) => row.length !== rows[0].length)) return null;
  if (rows[0].length < 2) return null;
  return rows;
}

function renderPipeTable(
  text: string,
  className: string,
  keyPrefix: string,
  requireSeparator = true,
): ReactNode | null {
  const rows = parsePipeDelimitedTable(text, requireSeparator);
  if (!rows) return null;
  return (
    <table
      key={`${keyPrefix}-table`}
      className={className}
      data-content-kind="table"
    >
      <tbody>
        {rows.map((row, rowIndex) => (
          <tr key={`${keyPrefix}-row-${rowIndex}`}>
            {row.map((cell, cellIndex) => (
              <td key={`${keyPrefix}-cell-${rowIndex}-${cellIndex}`}>{renderStyledText(cell)}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function renderImageText(text: string) {
  return (
    renderPipeTable(text, "post-body-table post-image-text-table", "post-image-text", false) ?? (
      <p>{renderStyledText(text)}</p>
    )
  );
}

const SAFE_EMBEDDED_IMAGE_SOURCE =
  /^data:image\/(?:png|jpe?g|gif|webp|avif|bmp|x-icon|vnd\.microsoft\.icon);base64,[A-Za-z0-9+/]+={0,2}$/i;

function formatImageRegionLocation(region: PostImageRegion): string | null {
  const values = [region.x_ratio, region.y_ratio, region.width_ratio, region.height_ratio];
  const right = region.x_ratio + region.width_ratio;
  const bottom = region.y_ratio + region.height_ratio;
  if (
    values.some((value) => !Number.isFinite(value) || value < 0 || value > 1) ||
    right > 1 + Number.EPSILON * 4 ||
    bottom > 1 + Number.EPSILON * 4
  ) {
    return null;
  }
  const percent = (value: number) => `${Math.round(value * 100)}%`;
  return `${t("Region location")}: ${percent(region.x_ratio)}, ${percent(region.y_ratio)} – ${percent(right)}, ${percent(bottom)}`;
}

function renderImageEvidence(
  index: number,
  imageContent?: PostImageContent,
  sourceImage?: Extract<PostBodySegment, { kind: "image" }>,
) {
  const sourceImageSrc =
    sourceImage && SAFE_EMBEDDED_IMAGE_SOURCE.test(sourceImage.src) ? sourceImage.src : undefined;
  const imageCaption = imageContent?.caption?.trim() || "";
  const imageExtractedText = imageContent?.extracted_text?.trim() || "";
  return (
    <figure key={`post-body-image-${index}`} className="post-embedded-image">
      {sourceImageSrc ? (
        <img src={sourceImageSrc} alt={imageCaption || t("Embedded image")} />
      ) : null}
      {imageCaption || !sourceImageSrc ? (
        <figcaption>{imageCaption || t("Embedded image")}</figcaption>
      ) : null}
      {imageContent?.tags.length ? (
        <p className="post-image-tags">
          <strong>{t("Image tags")}:</strong> {imageContent.tags.join(", ")}
        </p>
      ) : null}
      {imageExtractedText ? (
        <details className="post-image-text">
          <summary>{t("Text detected in image")}</summary>
          {renderImageText(imageExtractedText)}
        </details>
      ) : null}
      {imageContent?.regions?.length ? (
        <details className="post-image-regions" open>
          <summary>{t("Image regions")}</summary>
          <ol>
            {imageContent.regions.map((region) => {
              const location = formatImageRegionLocation(region);
              const caption = region.caption?.trim() || "";
              const extractedText = region.extracted_text?.trim() || "";
              return (
                <li key={region.region_index}>
                  {caption ? <span>{caption}</span> : null}
                  {extractedText && extractedText !== caption ? (
                    <small>{t("Text detected in image")}: {extractedText}</small>
                  ) : null}
                  {!caption && !extractedText ? <span>{t("Unknown")}</span> : null}
                  {region.tags.length ? (
                    <small>
                      {t("Image tags")}: {region.tags.join(", ")}
                    </small>
                  ) : null}
                  {location ? (
                    <small className="post-image-region-location">{location}</small>
                  ) : null}
                </li>
              );
            })}
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
          {renderStyledText(segment.text)}
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

function renderTextSegment(segment: Extract<PostBodySegment, { kind: "text" }>, index: number) {
  return (
    renderPipeTable(segment.text, "post-body-table post-markdown-table", `post-markdown-${index}`) ??
    renderSegment(segment, index)
  );
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
function displayUnitText(value: string): string {
  return decodeHtmlEntities(normalizeScriptText(value));
}

function normalizedUnitText(value: string): string {
  return displayUnitText(value).replace(/\s+/g, " ").trim();
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
                  <td key={`post-body-table-cell-${row.unit_index}-${cellIndex}`}>
                    {renderStyledText(displayUnitText(cell))}
                  </td>
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
      renderTextSegment(
        {
          kind: "text",
          text: displayUnitText(unit.unit_text),
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
        return renderTextSegment(segment, index);
      })}
    </div>
  );
}
