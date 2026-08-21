import { useState, type ReactNode } from "react";
import { splitPostBody, type PostBodySegment } from "./postBodyDisplay";
import { t } from "./i18n";
import type { PostContentUnit, PostImageContent, PostImageRegion } from "./api";

function parsePipeDelimitedTable(text: string): string[][] | null {
  const parsedRows = text
    .split(/\r?\n/)
    .map((row) => {
      const cells = row.split(/(?<!\\)\|/).map((cell) => cell.trim().replace(/\\\|/g, "|"));
      if (cells[0] === "") cells.shift();
      if (cells[cells.length - 1] === "") cells.pop();
      return cells;
    });
  if (!parsedRows.some((row) => row.every((cell) => /^:?-{3,}:?$/.test(cell)))) return null;
  const rows = parsedRows
    .filter((row) => !row.every((cell) => /^:?-{3,}:?$/.test(cell)))
    .filter((row) => row.length > 1 && row.some(Boolean));
  if (rows.length < 2 || rows.some((row) => row.length !== rows[0].length)) return null;
  if (rows[0].length < 2) return null;
  return rows;
}

function renderImageText(text: string) {
  const rows = parsePipeDelimitedTable(text);
  if (!rows) return <p>{text}</p>;
  const [header, ...bodyRows] = rows;
  return (
    <table className="post-body-table post-image-text-table">
      <thead>
        <tr>
          {header.map((cell, cellIndex) => (
            <th key={`post-image-text-header-${cellIndex}`} scope="col">
              {cell}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {bodyRows.map((row, rowIndex) => (
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

const SAFE_EMBEDDED_IMAGE_SOURCE =
  /^data:image\/(?:png|jpe?g|gif|webp|avif|bmp|x-icon|vnd\.microsoft\.icon);base64,[A-Za-z0-9+/]+={0,2}$/i;
const RATIO_EPSILON = 1e-9;

function hasPersistedOverlayBox(region: PostImageRegion): boolean {
  const { x_ratio, y_ratio, width_ratio, height_ratio } = region;
  if (![x_ratio, y_ratio, width_ratio, height_ratio].every((value) => Number.isFinite(value))) {
    return false;
  }
  if (x_ratio < 0 || y_ratio < 0 || width_ratio <= 0 || height_ratio <= 0) {
    return false;
  }
  return x_ratio + width_ratio <= 1 + RATIO_EPSILON && y_ratio + height_ratio <= 1 + RATIO_EPSILON;
}

function regionBuyerLabel(region: PostImageRegion): string {
  return region.caption || region.extracted_text || t("Unknown");
}

function ImageEvidenceFigure({
  imageContent,
  sourceImage,
}: {
  imageContent?: PostImageContent;
  sourceImage?: Extract<PostBodySegment, { kind: "image" }>;
}) {
  const [selectedRegionIndex, setSelectedRegionIndex] = useState<number | null>(null);
  const regions = imageContent?.regions ?? [];
  const sourceImageSrc =
    sourceImage && SAFE_EMBEDDED_IMAGE_SOURCE.test(sourceImage.src) ? sourceImage.src : undefined;
  const overlayRegions = sourceImageSrc ? regions.filter(hasPersistedOverlayBox) : [];
  const selectedRegion = overlayRegions.find((region) => region.region_index === selectedRegionIndex);

  return (
    <figure className="post-embedded-image">
      {sourceImageSrc ? (
        <div className="post-embedded-image-frame">
          <img src={sourceImageSrc} alt={imageContent?.caption || t("Embedded image")} />
          {overlayRegions.length ? (
            <div className="post-image-region-overlays" role="group" aria-label={t("Image regions")}>
              {overlayRegions.map((region) => {
                const label = regionBuyerLabel(region);
                const pressed = selectedRegionIndex === region.region_index;
                return (
                  <button
                    type="button"
                    key={region.region_index}
                    className="post-image-region-overlay"
                    data-region-index={region.region_index}
                    aria-pressed={pressed}
                    aria-label={`${t("Image region")}: ${label}`}
                    style={{
                      left: `${region.x_ratio * 100}%`,
                      top: `${region.y_ratio * 100}%`,
                      width: `${region.width_ratio * 100}%`,
                      height: `${region.height_ratio * 100}%`,
                    }}
                    onClick={() =>
                      setSelectedRegionIndex((current) =>
                        current === region.region_index ? null : region.region_index,
                      )
                    }
                  />
                );
              })}
            </div>
          ) : null}
        </div>
      ) : null}
      {imageContent?.caption || !sourceImageSrc ? (
        <figcaption>{imageContent?.caption || t("Embedded image")}</figcaption>
      ) : null}
      {selectedRegion ? (
        <p className="post-image-current-region" aria-live="polite">
          {t("Current image region")}: {regionBuyerLabel(selectedRegion)}
        </p>
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
      {regions.length ? (
        <details className="post-image-regions">
          <summary>{t("Image regions")}</summary>
          <ol>
            {regions.map((region) => (
              <li key={region.region_index}>
                {region.caption ? <p>{region.caption}</p> : null}
                {region.extracted_text && parsePipeDelimitedTable(region.extracted_text) ? (
                  <div className="post-image-region-text">
                    {renderImageText(region.extracted_text)}
                  </div>
                ) : !region.caption && region.extracted_text ? (
                  <p>{region.extracted_text}</p>
                ) : !region.caption ? (
                  t("Unknown")
                ) : null}
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

const MAX_RENDERABLE_INDENT_LEVEL = 64;

function safeIndentLevel(value: unknown): number | undefined {
  if (
    typeof value !== "number" ||
    !Number.isFinite(value) ||
    value <= 0 ||
    value > MAX_RENDERABLE_INDENT_LEVEL
  ) {
    return undefined;
  }
  return value;
}

function renderSegment(segment: PostBodySegment, index: number, imageContent?: PostImageContent) {
  switch (segment.kind) {
    case "text": {
      const indentLevel = safeIndentLevel(segment.indentLevel);
      return (
        <p
          key={`post-body-text-${index}`}
          className={`post-body-text${segment.role === "footnote" ? " post-body-footnote" : ""}`}
          data-content-kind={segment.role ?? "text"}
          data-indent-level={indentLevel ?? 0}
          style={indentLevel ? { paddingInlineStart: `${indentLevel}em` } : undefined}
        >
          {segment.text}
        </p>
      );
    }
    case "image":
      return (
        <ImageEvidenceFigure
          key={`post-body-image-${index}-${imageContent?.unit_index ?? "unknown"}-${imageContent?.caption ?? ""}-${segment.src}`}
          imageContent={imageContent}
          sourceImage={segment}
        />
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
    unit.unit_kind_code === "table_row"
  );
}

function structuredTableCells(unit: PostContentUnit): string[] {
  return unit.unit_text.split(/\s*\|\s*/);
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
        sourceImage ? (
          renderSegment(sourceImage, index, content)
        ) : (
          <ImageEvidenceFigure key={`post-body-image-${index}`} imageContent={content} />
        ),
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
      for (const row of rows) {
        for (const cell of structuredTableCells(row)) {
          sourceTextForUnit(cell);
        }
      }
      rendered.push(
        <table className="post-body-table" key={`post-body-table-${index}`}>
          <tbody>
            {rows.map((row, rowIndex) => (
              <tr key={`post-body-table-row-${row.unit_index}-${rowIndex}`}>
                {structuredTableCells(row).map((cell, cellIndex) => (
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
    const candidateIndent = safeIndentLevel(unit.indent_level);
    const persistedIndent =
      candidateIndent &&
      (unit.indent_source_code === "explicit" || unit.indent_source_code === "llm")
        ? candidateIndent
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
        return renderSegment(segment, index, content);
      })}
    </div>
  );
}
