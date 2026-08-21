/**
 * Split a raw `post_body` into text and in-place data-URI images.
 *
 * The popup used to dump the source string, so a buyer who opened a post
 * with an embedded invoice saw a base64 wall instead of the picture.
 * Only `data:image/...;base64,...` payloads are turned into images —
 * remote `http(s)` img tags are stripped, never fetched.
 */

export type PostBodySegment =
  | { kind: "text"; text: string; indentLevel?: number; role?: "footnote" }
  | { kind: "image"; src: string; mimeType: string; position: number };

export type MarkdownBodyBlock =
  | { kind: "prose"; text: string }
  | { kind: "table"; rows: string[][] };

const DATA_URI_IMG =
  /<img\b[^>]*\bsrc\s*=\s*["']data:(image\/[a-zA-Z0-9.+-]+);base64,([A-Za-z0-9+/=\s]+)["'][^>]*>/gi;

const HTML_TAG = /<\/?[a-zA-Z][^>]*>/g;
const BREAK_TAG = /<br\b[^>]*>/gi;
const BLOCK_TAG =
  /<\/?(?:article|blockquote|div|h[1-6]|li|oi|ol|p|section|table|tbody|td|tfoot|th|thead|tr|ul|w:p|w:tbl|w:tr|w:tc)\b[^>]*>/gi;
const WORD_INDENT_TAG = /<w:ind\b[^>]*\/?\s*>/gi;
const LIST_ITEM_START = /^\s*(?:[-*•·]\s+|[*†‡](?=\S)|(?:\d{1,3}|[A-Za-z가-힣])[.)]\s+|[①-⑳]\s+)/;
const FOOTNOTE_START = /^\s*[*†‡]+(?=\S)/;
const INDENT_MARKER = "\u0001lw-indent:";
const INDENT_MARKER_END = "\u0002";
const INDENT_MARKER_PATTERN = /lw-indent:(\d+)/g;
const NUMERIC_FOOTNOTE_MARKER = "\u0003lw-numeric-footnote\u0004";
const NUMERIC_SUPERSCRIPT = /<sup\b[^>]*>\s*(\d{1,3})\s*<\/sup>/gi;

function stripIndentMarkers(value: string): string {
  return value
    .replace(INDENT_MARKER_PATTERN, "")
    .split(String.fromCharCode(1))
    .join("")
    .split(String.fromCharCode(2))
    .join("");
}

import { t } from "./i18n";

export function decodeHtmlEntities(text: string): string {
  const decoder = document.createElement("textarea");
  let decoded = text;
  for (let pass = 0; pass < 3; pass += 1) {
    decoder.innerHTML = decoded;
    const next = decoder.value;
    if (next === decoded) break;
    decoded = next;
  }
  return decoded.replace(/\u00a0/g, " ");
}

function lengthToIndentUnits(value: string): number {
  const match = value
    .trim()
    .replace(/["']+$/, "")
    .match(/^([+-]?(?:\d+\.?\d*|\.\d+))(px|pt|em|rem|in|cm|mm|%)?$/i);
  if (!match) return 0;
  const amount = Number(match[1]);
  if (!Number.isFinite(amount) || amount <= 0) return 0;
  const pixels = amount *
    ({ px: 1, pt: 96 / 72, em: 16, rem: 16, in: 96, cm: 96 / 2.54, mm: 96 / 25.4, "%": 16 / 100 }[
      (match[2] ?? "px").toLowerCase() as "px" | "pt" | "em" | "rem" | "in" | "cm" | "mm" | "%"
    ] ?? 1);
  return Math.max(0, Math.round(pixels / 8));
}

function declaredIndentWidth(tag: string): number {
  const name = tag.match(/^<\/?\s*([a-z0-9:]+)/i)?.[1]?.toLowerCase() ?? "";
  let width = name === "blockquote" || name === "ul" || name === "ol" || name === "oi" ? 4 : 0;
  const style = tag.match(/\bstyle\s*=\s*(["'])(.*?)\1/i)?.[2] ?? "";
  for (const match of style.matchAll(
    /(?:^|;)\s*(?:margin-left|padding-left|padding-inline-start|text-indent)\s*:\s*([^;]+)/gi,
  )) {
    width += lengthToIndentUnits(match[1]);
  }
  for (const match of style.matchAll(/(?:^|;)\s*(?:margin|padding)\s*:\s*([^;]+)/gi)) {
    const parts = match[1].trim().split(/\s+/);
    const left = parts.length >= 4 ? parts[3] : parts.length >= 2 ? parts[1] : parts[0];
    width += lengthToIndentUnits(left);
  }
  for (const match of tag.matchAll(
    /\b(?:w:)?(?:left|start|firstline)\s*=\s*["'](-?\d+)["']/gi,
  )) {
    width += Math.max(0, Math.round(Number(match[1]) / 120));
  }
  return width;
}

function indentMarker(width: number): string {
  return width > 0 ? `${INDENT_MARKER}${width}${INDENT_MARKER_END}` : "";
}

function stripHtmlTags(text: string): string {
  text = text.replace(/<sup[^>]*>(.*?)<\/sup>/gi, "^$1");
  let listDepth = 0;
  const withBoundaries = text
    .replace(BREAK_TAG, "\n")
    .replace(BLOCK_TAG, (tag) => {
      const closing = /^<\//.test(tag);
      const listContainer = /^<\s*\/?\s*(?:ul|ol|oi)\b/i.test(tag);
      if (closing) {
        if (listContainer) listDepth = Math.max(0, listDepth - 1);
        return "\n\n";
      }
      if (listContainer) {
        listDepth += 1;
        return "\n\n";
      }
      if (/^<\s*li\b/i.test(tag)) {
        return `\n\n${indentMarker(Math.max(listDepth * 4, declaredIndentWidth(tag)))}`;
      }
      return `\n\n${indentMarker(declaredIndentWidth(tag))}`;
    })
    .replace(WORD_INDENT_TAG, (tag) => indentMarker(declaredIndentWidth(tag)));
  const withoutTags = withBoundaries.replace(HTML_TAG, (tag) => {
    if (/^<\/?w:/i.test(tag) || /^<\/?sup\b/i.test(tag)) return "";
    return " ";
  });
  const decoded = decodeHtmlEntities(withoutTags);
  return decoded
    .split("\n")
    .map((line) => {
      if (!line.trim()) return "";
      const leading = line.match(/^[^\S\n]*/)?.[0] ?? "";
      return `${leading}${line
        .slice(leading.length)
        .replace(/[^\S\n]+/g, " ")}`;
    })
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .replace(/^\n+|\n+$/g, "");
}

function splitSemanticParagraphs(text: string): string[] {
  const paragraphs: string[] = [];
  let lines: string[] = [];
  const flush = () => {
    const paragraph = lines.join(" ").trimEnd();
    if (paragraph.trim()) paragraphs.push(paragraph);
    lines = [];
  };

  for (const line of text.split("\n")) {
    if (!line.trim()) {
      flush();
      continue;
    }
    if (lines.length > 0 && LIST_ITEM_START.test(line)) flush();
    lines.push(lines.length === 0 ? line.replace(/[ \t]+$/g, "") : line.trim());
  }
  flush();
  return paragraphs;
}

function indentationWidth(line: string): number {
  let width = 0;
  for (const character of line) {
    if (character === " " || character === "\u00a0") width += 1;
    else if (character === "\t") width += 4;
    else break;
  }
  return width;
}

function greatestCommonDivisor(left: number, right: number): number {
  let a = left;
  let b = right;
  while (b !== 0) {
    [a, b] = [b, a % b];
  }
  return a;
}

export function inferIndentationUnit(text: string): number {
  const sourceWidths = text
    .split("\n")
    .filter((line) => line.trim())
    .map(indentationWidth)
    .filter((width) => width > 0)
    .reduce(greatestCommonDivisor, 0);
  const declaredWidths = [...text.matchAll(INDENT_MARKER_PATTERN)].map((match) => Number(match[1]));
  return [...(sourceWidths > 0 ? [sourceWidths] : []), ...declaredWidths].reduce(
    greatestCommonDivisor,
    0,
  );
}

function indentationLevel(text: string, unit: number): number {
  const declaredWidth = [...text.matchAll(INDENT_MARKER_PATTERN)].reduce(
    (total, match) => total + Number(match[1]),
    0,
  );
  const withoutMarkers = stripIndentMarkers(text);
  const firstLine = withoutMarkers.split("\n").find((line) => line.trim()) ?? "";
  const width = indentationWidth(firstLine);
  const explicitLevel = Math.max(
    unit > 0 && width > 0 ? Math.round(width / unit) : 0,
    unit > 0 && declaredWidth > 0 ? Math.round(declaredWidth / unit) : 0,
  );
  return explicitLevel;
}

function isDecodableBase64(raw: string): boolean {
  if (raw.length === 0) {
    return false;
  }
  try {
    atob(raw);
    return true;
  } catch {
    return false;
  }
}

function pushText(segments: PostBodySegment[], raw: string, indentUnit: number): void {
  const text = stripHtmlTags(
    raw.replace(NUMERIC_SUPERSCRIPT, `${NUMERIC_FOOTNOTE_MARKER}$1`),
  );
  for (const paragraph of splitSemanticParagraphs(text)) {
    const hasNumericSuperscriptMarker = paragraph.includes(NUMERIC_FOOTNOTE_MARKER);
    const indentLevel = indentationLevel(paragraph, indentUnit);
    const normalized = stripIndentMarkers(paragraph.replaceAll(NUMERIC_FOOTNOTE_MARKER, ""))
      .replace(/^[ \t]+/, "")
      .replace(/[ \t]+$/gm, "");
    if (normalized.trim()) {
      segments.push({
        kind: "text",
        text: normalized,
        ...(indentLevel > 0 ? { indentLevel } : {}),
        ...(hasNumericSuperscriptMarker || FOOTNOTE_START.test(normalized)
          ? { role: "footnote" as const }
          : {}),
      });
    }
  }
}

function markdownCells(line: string): string[] | null {
  const value = line.trim().replace(/^\|/, "").replace(/(?<!\\)\|$/, "");
  if (!value.includes("|")) return null;
  const cells = value.split(/(?<!\\)\|/).map((cell) => cell.trim().replace(/\\\|/g, "|"));
  return cells.length >= 2 && cells.every(Boolean) ? cells : null;
}

function isMarkdownSeparatorRow(cells: string[] | null): boolean {
  return Boolean(cells?.every((cell) => /^:?-{3,}:?$/.test(cell)));
}

/**
 * Split the narrow Markdown-table shape supported by the ingestion boundary.
 * The return value preserves prose and skips only the delimiter row.
 */
export function splitMarkdownTableBody(body: string): MarkdownBodyBlock[] | null {
  const lines = body.replace(/\r\n?/g, "\n").split("\n");
  const blocks: MarkdownBodyBlock[] = [];
  let prose: string[] = [];
  let foundTable = false;

  const flushProse = () => {
    const text = prose.join("\n").trim();
    if (text) blocks.push({ kind: "prose", text });
    prose = [];
  };

  let index = 0;
  while (index < lines.length) {
    const header = markdownCells(lines[index]);
    const separator = markdownCells(lines[index + 1] ?? "");
    if (!header || !isMarkdownSeparatorRow(separator)) {
      prose.push(lines[index]);
      index += 1;
      continue;
    }

    foundTable = true;
    flushProse();
    const rows = [header];
    index += 2;
    while (index < lines.length && lines[index].trim()) {
      const row = markdownCells(lines[index]);
      if (!row) break;
      rows.push(row);
      index += 1;
    }
    blocks.push({ kind: "table", rows });
  }

  flushProse();
  return foundTable ? blocks : null;
}

export function splitPostBody(body: string): PostBodySegment[] {
  const segments: PostBodySegment[] = [];
  const indentUnit = inferIndentationUnit(stripHtmlTags(body));
  const pattern = new RegExp(DATA_URI_IMG.source, "gi");
  let lastIndex = 0;
  let match = pattern.exec(body);
  while (match !== null) {
    pushText(segments, body.slice(lastIndex, match.index), indentUnit);
    const mimeType = match[1];
    const rawB64 = match[2].replace(/\s+/g, "");
    if (isDecodableBase64(rawB64)) {
      segments.push({
        kind: "image",
        src: `data:${mimeType};base64,${rawB64}`,
        mimeType,
        position: match.index,
      });
    } else {
      segments.push({
        kind: "text",
        text: t("Embedded image could not be decoded. Re-export the source post and open it again."),
      });
    }
    lastIndex = match.index + match[0].length;
    match = pattern.exec(body);
  }
  pushText(segments, body.slice(lastIndex), indentUnit);
  if (segments.length === 0) {
    return [{ kind: "text", text: stripHtmlTags(body) }];
  }
  return segments;
}
