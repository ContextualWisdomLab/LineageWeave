/**
 * Split a raw `post_body` into text and in-place data-URI images.
 *
 * The popup used to dump the source string, so a buyer who opened a post
 * with an embedded invoice saw a base64 wall instead of the picture.
 * Only `data:image/...;base64,...` payloads are turned into images —
 * remote `http(s)` img tags are stripped, never fetched.
 */

export type PostBodySegment =
  | { kind: "text"; text: string }
  | { kind: "image"; src: string; mimeType: string; position: number };

const DATA_URI_IMG =
  /<img\b[^>]*\bsrc\s*=\s*["']data:(image\/[a-zA-Z0-9.+-]+);base64,([A-Za-z0-9+/=\s]+)["'][^>]*>/gi;

const HTML_TAG = /<\/?[a-zA-Z][^>]*>/g;
const BREAK_TAG = /<br\s*\/?\s*>/gi;
const BLOCK_TAG =
  /<\/?(?:article|blockquote|div|h[1-6]|li|ol|p|section|table|tbody|td|tfoot|th|thead|tr|ul)\b[^>]*>/gi;

import { t } from "./i18n";

function stripHtmlTags(text: string): string {
  const withBoundaries = text.replace(BREAK_TAG, "\n").replace(BLOCK_TAG, "\n\n");
  const withoutTags = withBoundaries.replace(HTML_TAG, " ");
  const decoder = document.createElement("textarea");
  let decoded = withoutTags;
  for (let pass = 0; pass < 3; pass += 1) {
    decoder.innerHTML = decoded;
    const next = decoder.value;
    if (next === decoded) {
      break;
    }
    decoded = next;
  }
  return decoded
    .replace(/[^\S\n]+/g, " ")
    .replace(/\n[ \t]*/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
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

function pushText(segments: PostBodySegment[], raw: string): void {
  const text = stripHtmlTags(raw);
  for (const paragraph of text.split(/\n{2,}/)) {
    const normalized = paragraph.trim();
    if (normalized) {
      segments.push({ kind: "text", text: normalized });
    }
  }
}

export function splitPostBody(body: string): PostBodySegment[] {
  const segments: PostBodySegment[] = [];
  const pattern = new RegExp(DATA_URI_IMG.source, "gi");
  let lastIndex = 0;
  let match = pattern.exec(body);
  while (match !== null) {
    pushText(segments, body.slice(lastIndex, match.index));
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
  pushText(segments, body.slice(lastIndex));
  if (segments.length === 0) {
    return [{ kind: "text", text: stripHtmlTags(body) }];
  }
  return segments;
}
