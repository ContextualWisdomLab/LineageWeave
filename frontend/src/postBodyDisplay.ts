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
    const hasFootnoteLabel = [...tag.matchAll(
      /\b(?:class|role)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>"']+))/gi,
    )].some((attribute) =>
      /\b(?:footnotes?|endnotes?|msofootnotetext|msoendnotetext)\b/i.test(
        attribute[1] ?? attribute[2] ?? attribute[3] ?? "",
      ),
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
    const next = decoded.replace(/&(?:#[0-9]+|#x[0-9a-f]+|[a-z][a-z0-9]+);/gi, (entity) => {
      decoder.innerHTML = entity;
      return decoder.value;
    });
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

const SUPER_ASCII_TO_UNI: Record<string, string> = {
  "0": "⁰",
  "1": "¹",
  "2": "²",
  "3": "³",
  "4": "⁴",
  "5": "⁵",
  "6": "⁶",
  "7": "⁷",
  "8": "⁸",
  "9": "⁹",
  "+": "⁺",
  "-": "⁻",
  "=": "⁼",
  "(": "⁽",
  ")": "⁾",
  n: "ⁿ",
  N: "ⁿ",
  i: "ⁱ",
  I: "ⁱ",
};
const SUB_ASCII_TO_UNI: Record<string, string> = {
  "0": "₀",
  "1": "₁",
  "2": "₂",
  "3": "₃",
  "4": "₄",
  "5": "₅",
  "6": "₆",
  "7": "₇",
  "8": "₈",
  "9": "₉",
  "+": "₊",
  "-": "₋",
  "=": "₌",
  "(": "₍",
  ")": "₎",
  a: "ₐ",
  e: "ₑ",
  h: "ₕ",
  i: "ᵢ",
  k: "ₖ",
  l: "ₗ",
  m: "ₘ",
  n: "ₙ",
  o: "ₒ",
  p: "ₚ",
  s: "ₛ",
  t: "ₜ",
  x: "ₓ",
};
// Two ASCII keys can map to the same Unicode character (e.g. "n" and "N"
// both produce "ⁿ"). Building the reverse table naively lets the
// last-inserted ASCII key win, so decoding always yields one fixed case
// regardless of what was actually stored. Keep the first (lowercase, since
// it is listed first above) mapping instead, so round-tripping preserves case.
function buildUnicodeToAsciiTable(table: Record<string, string>): Record<string, string> {
  const reverse: Record<string, string> = {};
  for (const [ascii, uni] of Object.entries(table)) {
    if (!(uni in reverse)) reverse[uni] = ascii;
  }
  return reverse;
}
const SUPER_UNI_TO_ASCII = buildUnicodeToAsciiTable(SUPER_ASCII_TO_UNI);
const SUB_UNI_TO_ASCII = buildUnicodeToAsciiTable(SUB_ASCII_TO_UNI);
const CARET_EXPONENT =
  /(?<=[A-Za-z0-9µμ°ΩÅåÅ)])\^(?:\{([+-]?\d{1,3}|[nNiI])\}|([+-]?\d{1,3}|[nNiI]))/g;
const ENCODED_CARET = /&(?:amp;)*(?:#0*94|#x0*5e);/gi;
const ENCODED_LT = String.raw`&(?:amp;)*(?:lt|#0*60|#x0*3c);`;
const ENCODED_GT = String.raw`&(?:amp;)*(?:gt|#0*62|#x0*3e);`;
const ENCODED_SCRIPT_TOKEN =
  `${ENCODED_LT}\\s*/?\\s*(?:sup|sub)(?=\\s|/|${ENCODED_GT})`;
const ENCODED_SCRIPT_PAIR = new RegExp(
  `${ENCODED_LT}(sup|sub)${ENCODED_GT}` +
    `((?:(?!${ENCODED_SCRIPT_TOKEN}).)*?)${ENCODED_LT}/\\1${ENCODED_GT}`,
  "gis",
);

function applyUnicodeScript(text: string, kind: "super" | "sub"): string {
  const table = kind === "super" ? SUPER_ASCII_TO_UNI : SUB_ASCII_TO_UNI;
  const values = new Set(Object.values(table));
  const compact = text.trim();
  if (!compact) return text;
  if ([...compact].every((ch) => ch in table || values.has(ch) || /\s/.test(ch))) {
    return [...text].map((ch) => table[ch] ?? ch).join("");
  }
  const prefix = kind === "super" ? "^" : "_";
  const leading = text.match(/^\s*/)?.[0] ?? "";
  const trailing = compact.length ? text.slice(leading.length + compact.length) : "";
  return `${leading}${prefix}${compact}${trailing}`;
}

function replaceHtmlScripts(text: string): string {
  return text
    .replace(/<sup\b[^>]*>(.*?)<\/sup>/gis, (_match, inner: string) =>
      applyUnicodeScript(decodeHtmlEntities(String(inner)).replace(/<[^>]+>/g, ""), "super"),
    )
    .replace(/<sub\b[^>]*>(.*?)<\/sub>/gis, (_match, inner: string) =>
      applyUnicodeScript(decodeHtmlEntities(String(inner)).replace(/<[^>]+>/g, ""), "sub"),
    );
}

function decodeScriptEntities(text: string): string {
  return text
    .replace(
      ENCODED_SCRIPT_PAIR,
      (_pair, kind: string, inner: string) =>
        `<${kind.toLowerCase()}>${inner}</${kind.toLowerCase()}>`,
    )
    .replace(ENCODED_CARET, (caret) => decodeHtmlEntities(caret));
}

export function normalizeScriptText(text: string): string {
  const withCarets = decodeScriptEntities(text).replace(
    CARET_EXPONENT,
    (_match, braced: string, bare: string) => applyUnicodeScript(braced || bare, "super"),
  );
  return replaceHtmlScripts(withCarets);
}

export type ScriptRun = { text: string; script?: "super" | "sub" };

export function splitScriptRuns(text: string): ScriptRun[] {
  const runs: ScriptRun[] = [];
  const push = (chunk: string, script?: "super" | "sub") => {
    if (!chunk) return;
    const last = runs[runs.length - 1];
    if (last && last.script === script) {
      last.text += chunk;
      return;
    }
    runs.push(script ? { text: chunk, script } : { text: chunk });
  };
  let index = 0;
  while (index < text.length) {
    const ch = text[index];
    if (ch in SUPER_UNI_TO_ASCII) {
      let ascii = SUPER_UNI_TO_ASCII[ch];
      index += 1;
      while (index < text.length && text[index] in SUPER_UNI_TO_ASCII) {
        ascii += SUPER_UNI_TO_ASCII[text[index]];
        index += 1;
      }
      push(ascii, "super");
      continue;
    }
    if (ch in SUB_UNI_TO_ASCII) {
      let ascii = SUB_UNI_TO_ASCII[ch];
      index += 1;
      while (index < text.length && text[index] in SUB_UNI_TO_ASCII) {
        ascii += SUB_UNI_TO_ASCII[text[index]];
        index += 1;
      }
      push(ascii, "sub");
      continue;
    }
    if (ch === "^" && index > 0 && /[A-Za-z0-9µμ°ΩÅåÅ)]/.test(text[index - 1])) {
      const rest = text.slice(index);
      const match = rest.match(/^\^(?:\{([+-]?\d{1,3}|[nNiI])\}|([+-]?\d{1,3}|[nNiI]))/);
      if (match) {
        push(match[1] || match[2] || "", "super");
        index += match[0].length;
        continue;
      }
    }
    push(ch);
    index += 1;
  }
  return runs;
}

function stripHtmlTags(text: string): string {
  const withScripts = normalizeScriptText(markFootnoteTags(text));
  let listDepth = 0;
  const withBoundaries = withScripts
    .replace(BREAK_TAG, "\n")
    .replace(BLOCK_TAG, (tag) => {
      const name = tag.match(/^<\/?\s*([a-z0-9:]+)/i)?.[1]?.toLowerCase() ?? "";
      const closing = /^<\//.test(tag);
      if (name === "ul" || name === "ol") {
        if (closing) listDepth = Math.max(0, listDepth - 1);
        else listDepth += 1;
        return "\n\n";
      }
      if (closing) return "\n\n";
      const nestedListIndent = !closing && listDepth > 0 ? Math.max(0, listDepth - 1) * 4 : 0;
      return `\n\n${indentMarker(declaredIndentWidth(tag) + nestedListIndent)}`;
    })
    .replace(WORD_INDENT_TAG, (tag) => indentMarker(declaredIndentWidth(tag)));
  const withoutTags = withBoundaries.replace(HTML_TAG, (tag) =>
    /^<\/?(?:a\b|w:)/i.test(tag) ? "" : " ",
  );
  return decodeHtmlEntities(withoutTags)
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
    if (trimmed.includes("|")) {
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
        ...(isMarkedFootnote ? { role: "footnote" as const } : {}),
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
