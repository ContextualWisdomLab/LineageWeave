/**
 * Split a raw `post_body` into text and in-place data-URI images.
 *
 * The popup used to dump the source string, so a buyer who opened a post
 * with an embedded invoice saw a base64 wall instead of the picture.
 * Only `data:image/...;base64,...` payloads are turned into images —
 * remote `http(s)` img tags are stripped, never fetched. A tag-only body
 * never falls back to the raw source string.
 */

export type PostBodySegment =
  | { kind: "text"; text: string }
  | { kind: "image"; src: string; mimeType: string; position: number };

export const UNDECODEABLE_IMAGE =
  "Embedded image could not be decoded. Re-export the source post and open it again.";

export const REMOTE_IMAGE_SKIPPED =
  "This post linked a remote image that was not loaded. Re-export the source with the picture embedded and open it again.";

export const IMAGE_NOT_READ_HERE =
  "Image from this post. Text inside the picture is not read on this screen.";

const IMG_TAG = /<img\b[^>]*>/gi;

const SRC_ATTR = /\bsrc\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))/i;

const DATA_URI =
  /^data:(image\/[a-zA-Z0-9.+-]+)(?:;[\w.+-]+=[^;,]*)*;base64,([A-Za-z0-9+/=\s]+)$/i;

const HTML_TAG = /<\/?[a-zA-Z][^>]*>/g;

const REMOTE_SRC = /^https?:\/\//i;

function stripHtmlTags(text: string): string {
  return text.replace(HTML_TAG, " ").replace(/\s+/g, " ").trim();
}

function decodeBase64(raw: string): Uint8Array | null {
  if (raw.length === 0 || raw.length % 4 !== 0 || !/^[A-Za-z0-9+/]+=*$/.test(raw)) {
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

function looksLikeImage(mimeType: string, bytes: Uint8Array): boolean {
  const mime = mimeType.toLowerCase();
  if (mime === "image/png") {
    return (
      bytes.length >= 8 &&
      bytes[0] === 0x89 &&
      bytes[1] === 0x50 &&
      bytes[2] === 0x4e &&
      bytes[3] === 0x47
    );
  }
  if (mime === "image/jpeg" || mime === "image/jpg") {
    return bytes.length >= 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff;
  }
  if (mime === "image/gif") {
    return bytes.length >= 6 && bytes[0] === 0x47 && bytes[1] === 0x49 && bytes[2] === 0x46;
  }
  if (mime === "image/webp") {
    return (
      bytes.length >= 12 &&
      bytes[0] === 0x52 &&
      bytes[1] === 0x49 &&
      bytes[2] === 0x46 &&
      bytes[3] === 0x46 &&
      bytes[8] === 0x57 &&
      bytes[9] === 0x45 &&
      bytes[10] === 0x42 &&
      bytes[11] === 0x50
    );
  }
  if (mime === "image/svg+xml") {
    const text = new TextDecoder().decode(bytes).trimStart().toLowerCase();
    return text.startsWith("<svg") || text.startsWith("<?xml");
  }
  return bytes.length > 0;
}

function pushText(segments: PostBodySegment[], raw: string): void {
  const text = stripHtmlTags(raw);
  if (text) {
    segments.push({ kind: "text", text });
  }
}

function srcFromImgTag(tag: string): string | null {
  const match = SRC_ATTR.exec(tag);
  if (!match) {
    return null;
  }
  return match[1] ?? match[2] ?? match[3] ?? null;
}

export function splitPostBody(body: string): PostBodySegment[] {
  const segments: PostBodySegment[] = [];
  const pattern = new RegExp(IMG_TAG.source, "gi");
  let lastIndex = 0;
  let match = pattern.exec(body);
  let sawRemoteImage = false;
  let sawUndecodableImage = false;

  while (match !== null) {
    pushText(segments, body.slice(lastIndex, match.index));
    const src = srcFromImgTag(match[0]);
    if (src && REMOTE_SRC.test(src)) {
      sawRemoteImage = true;
    } else if (src) {
      const data = DATA_URI.exec(src.trim());
      if (data) {
        const mimeType = data[1];
        const rawB64 = data[2].replace(/\s+/g, "");
        const bytes = decodeBase64(rawB64);
        if (bytes && looksLikeImage(mimeType, bytes)) {
          segments.push({
            kind: "image",
            src: `data:${mimeType};base64,${rawB64}`,
            mimeType,
            position: match.index,
          });
        } else {
          sawUndecodableImage = true;
          segments.push({ kind: "text", text: UNDECODEABLE_IMAGE });
        }
      } else if (/^data:image\//i.test(src)) {
        sawUndecodableImage = true;
        segments.push({ kind: "text", text: UNDECODEABLE_IMAGE });
      }
    }
    lastIndex = match.index + match[0].length;
    match = pattern.exec(body);
  }
  pushText(segments, body.slice(lastIndex));

  if (segments.length > 0) {
    return segments;
  }
  if (sawRemoteImage) {
    return [{ kind: "text", text: REMOTE_IMAGE_SKIPPED }];
  }
  if (sawUndecodableImage) {
    return [{ kind: "text", text: UNDECODEABLE_IMAGE }];
  }
  return [{ kind: "text", text: body }];
}
