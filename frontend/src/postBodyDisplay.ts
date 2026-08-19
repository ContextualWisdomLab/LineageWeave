/**
 * Split a raw `post_body` into text and in-place data-URI images.
 *
 * The popup used to dump the source string, so a buyer who opened a post
 * with an embedded invoice saw a base64 wall instead of the picture.
 * Parsing uses the same HTML rules as `chunk_by_dom`: attribute values
 * may contain `>`, comments are ignored, and only raster `data:image`
 * payloads become `<img>` nodes. Remote `http(s)` tags are never fetched.
 */

export type PostBodySegment =
  | { kind: "text"; text: string }
  | { kind: "image"; src: string; mimeType: string; position: number; alt: string };

const RASTER_IMAGE_MIME_TYPES = new Set([
  "image/png",
  "image/jpeg",
  "image/jpg",
  "image/gif",
  "image/webp",
  "image/avif",
]);

const SKIP_TAGS = new Set(["STYLE", "SCRIPT", "NOSCRIPT"]);

const UNDECODEABLE_IMAGE =
  "Embedded image could not be decoded. Re-export the source post and open it again.";

const REJECTED_IMAGE_TYPE =
  "Embedded image type is not displayed. Re-export as PNG or JPEG and open it again.";

const REMOTE_ONLY_IMAGE =
  "This post has no displayable text. Remote images were not loaded. Re-export the source with embedded pictures and open it again.";

const PNG_SIGNATURE = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];
const JPEG_PREFIX = [0xff, 0xd8, 0xff];

function looksLikeHtml(body: string): boolean {
  return /<[a-zA-Z!/?]/.test(body);
}

function normalizeVisibleText(text: string): string {
  return text.replace(/\u00a0/g, " ").replace(/\s+/g, " ").trim();
}

function startsWithBytes(data: Uint8Array, prefix: number[]): boolean {
  if (data.length < prefix.length) {
    return false;
  }
  return prefix.every((value, index) => data[index] === value);
}

function looksLikeRasterImage(mimeType: string, data: Uint8Array): boolean {
  if (data.length === 0) {
    return false;
  }
  if (mimeType === "image/png") {
    return startsWithBytes(data, PNG_SIGNATURE);
  }
  if (mimeType === "image/jpeg" || mimeType === "image/jpg") {
    return startsWithBytes(data, JPEG_PREFIX);
  }
  if (mimeType === "image/gif") {
    return (
      startsWithBytes(data, [0x47, 0x49, 0x46, 0x38, 0x37, 0x61]) ||
      startsWithBytes(data, [0x47, 0x49, 0x46, 0x38, 0x39, 0x61])
    );
  }
  if (mimeType === "image/webp") {
    return (
      data.length >= 12 &&
      startsWithBytes(data, [0x52, 0x49, 0x46, 0x46]) &&
      data[8] === 0x57 &&
      data[9] === 0x45 &&
      data[10] === 0x42 &&
      data[11] === 0x50
    );
  }
  if (mimeType === "image/avif") {
    if (data.length < 12 || data[4] !== 0x66 || data[5] !== 0x74 || data[6] !== 0x79 || data[7] !== 0x70) {
      return false;
    }
    const brand = String.fromCharCode(...data.slice(8, 16));
    return brand.includes("avif") || brand.includes("avis") || brand.includes("mif1");
  }
  return false;
}

function bytesFromStrictBase64(raw: string): Uint8Array | null {
  if (raw.length === 0 || raw.length % 4 !== 0 || !/^[A-Za-z0-9+/]+={0,2}$/.test(raw)) {
    return null;
  }
  try {
    const binary = atob(raw);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) {
      bytes[index] = binary.charCodeAt(index);
    }
    return bytes;
  } catch {
    return null;
  }
}

function isInsideHtmlComment(source: string, index: number): boolean {
  const lastOpen = source.lastIndexOf("<!--", index);
  if (lastOpen < 0) {
    return false;
  }
  const lastClose = source.indexOf("-->", lastOpen);
  return lastClose < 0 || lastClose > index;
}

function nextVisibleImgOffset(source: string, from: number): number {
  let search = from;
  const lower = source.toLowerCase();
  while (search < source.length) {
    const index = lower.indexOf("<img", search);
    if (index < 0) {
      return -1;
    }
    if (!isInsideHtmlComment(source, index)) {
      return index;
    }
    search = index + 4;
  }
  return -1;
}

function parseDataUriSrc(src: string): { mimeType: string; rawB64: string } | null {
  const match = /^data:(image\/[a-zA-Z0-9.+-]+);base64,([\s\S]*)$/i.exec(src.trim());
  if (!match) {
    return null;
  }
  return { mimeType: match[1].toLowerCase(), rawB64: match[2].replace(/\s+/g, "") };
}

function pushText(segments: PostBodySegment[], text: string): void {
  const normalized = normalizeVisibleText(text);
  if (normalized) {
    segments.push({ kind: "text", text: normalized });
  }
}

function walk(
  node: Node,
  source: string,
  segments: PostBodySegment[],
  cursor: { from: number },
  flags: { sawRemote: boolean; sawRejectedType: boolean; sawUndecodable: boolean },
): void {
  if (node.nodeType === Node.ELEMENT_NODE) {
    const element = node as Element;
    if (SKIP_TAGS.has(element.tagName)) {
      return;
    }
    if (element.tagName === "IMG") {
      const src = element.getAttribute("src") ?? "";
      const parsed = parseDataUriSrc(src);
      const position = nextVisibleImgOffset(source, cursor.from);
      if (position >= 0) {
        cursor.from = position + 4;
      }
      if (!parsed) {
        if (/^https?:/i.test(src) || src.startsWith("//")) {
          flags.sawRemote = true;
        }
        return;
      }
      if (!RASTER_IMAGE_MIME_TYPES.has(parsed.mimeType)) {
        flags.sawRejectedType = true;
        return;
      }
      const bytes = bytesFromStrictBase64(parsed.rawB64);
      if (bytes === null || !looksLikeRasterImage(parsed.mimeType, bytes)) {
        flags.sawUndecodable = true;
        pushText(segments, UNDECODEABLE_IMAGE);
        return;
      }
      const alt = (element.getAttribute("alt") ?? "").trim();
      segments.push({
        kind: "image",
        src: `data:${parsed.mimeType};base64,${parsed.rawB64}`,
        mimeType: parsed.mimeType,
        position: position >= 0 ? position : 0,
        alt,
      });
      return;
    }
    for (const child of Array.from(element.childNodes)) {
      walk(child, source, segments, cursor, flags);
    }
    return;
  }
  if (node.nodeType === Node.TEXT_NODE) {
    pushText(segments, node.textContent ?? "");
  }
}

/** Split raw post HTML into visible text and raster data-URI pictures. */
export function splitPostBody(body: string): PostBodySegment[] {
  if (!looksLikeHtml(body)) {
    return [{ kind: "text", text: body }];
  }
  const document = new DOMParser().parseFromString(body, "text/html");
  const segments: PostBodySegment[] = [];
  const flags = { sawRemote: false, sawRejectedType: false, sawUndecodable: false };
  const cursor = { from: 0 };
  for (const child of Array.from(document.body.childNodes)) {
    walk(child, body, segments, cursor, flags);
  }
  if (segments.length > 0) {
    return segments;
  }
  if (flags.sawUndecodable) {
    return [{ kind: "text", text: UNDECODEABLE_IMAGE }];
  }
  if (flags.sawRejectedType) {
    return [{ kind: "text", text: REJECTED_IMAGE_TYPE }];
  }
  if (flags.sawRemote) {
    return [{ kind: "text", text: REMOTE_ONLY_IMAGE }];
  }
  return [];
}
