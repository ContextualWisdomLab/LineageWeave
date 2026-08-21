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

const DATA_URI_IMG =
  /<img\b[^>]*\bsrc\s*=\s*["']data:(image\/[a-zA-Z0-9.+-]+);base64,([A-Za-z0-9+/=\s]+)["'][^>]*>/gi;

const HTML_TAG = /<\/?[a-zA-Z][^>]*>/g;
const BREAK_TAG = /<br\b[^>]*>/gi;
const BLOCK_TAG =
  /<\/?(?:article|blockquote|div|h[1-6]|li|ol|p|section|table|tbody|td|tfoot|th|thead|tr|ul|w:p|w:tbl|w:tr|w:tc)\b[^>]*>/gi;
const WORD_INDENT_TAG = /<w:ind\b[^>]*\/?\s*>/gi;
const LIST_ITEM_START = /^\s*(?:[-*•·]\s+|[*†‡](?=\S)|(?:\d{1,3}|[A-Za-z가-힣])[.)]\s+|[①-⑳]\s+)/;
const FOOTNOTE_START = /^\s*[*†‡](?=\S)/;
const INDENT_MARKER = "\u0001lw-indent:";
const INDENT_MARKER_END = "\u0002";
const INDENT_MARKER_PATTERN = /lw-indent:(\d+)/g;
const FOOTNOTE_MARKER = "\u0001lw-footnote\u0002";
const FOOTNOTE_MARKER_PATTERN = new RegExp(FOOTNOTE_MARKER, "g");

function markFootnoteTags(markup: string): string {
  let footnoteDepth = 0;
  const openTags: Array<{ name: string; isFootnote: boolean }> = [];
  const voidTags = new Set(["area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "w:br"]);
  return markup.replace(HTML_TAG, (tag) => {
    const match = tag.match(/^<\s*(\/?)\s*([a-z][a-z0-9:-]*)\b/i);
    if (!match) return tag;
    const closing = Boolean(match[1]);
    const name = match[2].toLowerCase();
    const hasFootnoteLabel = [...tag.matchAll(/\b(?:class|role)\s*=\s*(["'])(.*?)\1/gi)].some(
      (attribute) =>
        /\b(?:footnotes?|endnotes?|msofootnotetext|msoendnotetext)\b/i.test(attribute[2]),
    );
    const isContainer =
      hasFootnoteLabel && (name === "div" || name === "ol" || name === "ul");
    const isWordParagraph =
      name === "p" && hasFootnoteLabel;
    const isOoxmlContainer = name === "w:footnote" || name === "w:endnote";

    if (closing) {
      const matchingIndex = openTags.map((entry) => entry.name).lastIndexOf(name);
      if (matchingIndex >= 0) {
        const closedTags = openTags.splice(matchingIndex);
        footnoteDepth = Math.max(
          0,
          footnoteDepth - closedTags.filter((entry) => entry.isFootnote).length,
        );
      }
      return tag;
    }
    const selfClosing = /\/\s*>$/.test(tag) || voidTags.has(name);
    const opensFootnote = isOoxmlContainer || isContainer;
    if (!selfClosing) {
      openTags.push({ name, isFootnote: opensFootnote });
    }
    if (opensFootnote) {
      if (!selfClosing) footnoteDepth += 1;
      return `${tag}${FOOTNOTE_MARKER}`;
    }
    if (
      isWordParagraph ||
      (footnoteDepth > 0 && (name === "li" || name === "p" || name === "w:p"))
    ) {
      return `${tag}${FOOTNOTE_MARKER}`;
    }
    return tag;
  });
}

function stripIndentMarkers(value: string): string {
  return value
    .replace(INDENT_MARKER_PATTERN, "")
    .replace(FOOTNOTE_MARKER_PATTERN, "")
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
  let width = name === "blockquote" || name === "ul" || name === "ol" ? 4 : 0;
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
  text = markFootnoteTags(text).replace(/<sup[^>]*>(.*?)<\/sup>/gi, "^$1");
  const withBoundaries = text
    .replace(BREAK_TAG, "\n")
    .replace(BLOCK_TAG, (tag) => {
      if (/^<\//.test(tag)) return "\n\n";
      return `\n\n${indentMarker(declaredIndentWidth(tag))}`;
    })
    .replace(WORD_INDENT_TAG, (tag) => indentMarker(declaredIndentWidth(tag)));
  const withoutTags = withBoundaries.replace(HTML_TAG, (tag) => {
    if (/^<\/?(?:a\b|w:)/i.test(tag)) return "";
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
  let pipeTableRows: string[] = [];
  const flush = () => {
    const paragraph = lines.join(" ").trimEnd();
    if (paragraph.trim()) paragraphs.push(paragraph);
    lines = [];
  };
  const flushPipeTableRows = () => {
    const hasSeparator = pipeTableRows.some((row) => {
      const cells = row.trim().replace(/^\|/, "").replace(/\|$/, "").split("|");
      return cells.length >= 2 && cells.every((cell) => /^\s*:?-{3,}:?\s*$/.test(cell));
    });
    if (pipeTableRows.length >= 2 && hasSeparator) {
      flush();
      paragraphs.push(pipeTableRows.map((row) => row.trim()).join("\n"));
    } else {
      lines.push(...pipeTableRows);
    }
    pipeTableRows = [];
  };

  for (const line of text.split("\n")) {
    const trimmed = line.trim();
    if (trimmed.includes("|") && !LIST_ITEM_START.test(line)) {
      const cells = trimmed.replace(/^\|/, "").replace(/\|$/, "").split("|");
      if (cells.length >= 2 && cells.some((cell) => cell.trim())) {
        pipeTableRows.push(line);
        continue;
      }
    }
    if (pipeTableRows.length > 0) flushPipeTableRows();
    if (!line.trim()) {
      flush();
      continue;
    }
    if (lines.length > 0 && LIST_ITEM_START.test(line)) flush();
    lines.push(lines.length === 0 ? line.replace(/[ \t]+$/g, "") : line.trim());
  }
  if (pipeTableRows.length > 0) flushPipeTableRows();
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
  const text = stripHtmlTags(raw);
  for (const paragraph of splitSemanticParagraphs(text)) {
    const isMarkedFootnote = paragraph.includes(FOOTNOTE_MARKER);
    const indentLevel = indentationLevel(paragraph, indentUnit);
    const normalized = stripIndentMarkers(paragraph)
      .replace(/^[ \t]+/, "")
      .replace(/[ \t]+$/gm, "");
    if (normalized.trim()) {
      segments.push({
        kind: "text",
        text: normalized,
        ...(indentLevel > 0 ? { indentLevel } : {}),
        ...(isMarkedFootnote || FOOTNOTE_START.test(normalized)
          ? { role: "footnote" as const }
          : {}),
      });
    }
  }
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
    return [{ kind: "text", text: stripIndentMarkers(stripHtmlTags(body)) }];
  }
  return segments;
}
