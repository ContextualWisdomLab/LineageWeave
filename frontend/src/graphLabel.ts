/**
 * On-graph label wrapping for Event Lineage and Knowledge Graph.
 *
 * SVG `<text>` does not wrap. Character-cap ellipsis (`…`) hid titles longer
 * than 24–34 characters. Wrap instead so every character stays on the graph.
 * A token longer than the wrap budget stays on its own line; the layout
 * grows the reserved box rather than chopping the token.
 */

export const CHAR_W = 7;
export const LINE_H = 14;
export const LINEAGE_LABEL_CHARS = 26;
export const KNOWLEDGE_LABEL_CHARS = 22;
export const LABEL_OFFSET_X = 16;
export const DATE_LINE_H = 12;
export const KIND_LINE_H = 12;

/**
 * Split `value` into wrapped lines that preserve every character.
 * Never ellipsizes. Space-separated tokens wrap at `maxChars`; a single
 * over-long token stays intact. Scripts without spaces wrap by character
 * budget so CJK titles still occupy more than one line instead of overflowing.
 */
export function wrapLabel(value: string, maxChars: number): string[] {
  const normalized = value.replace(/\s+/g, " ").trim();
  if (!normalized) return [value];
  const budget = Math.max(1, maxChars);
  if (!/\s/.test(normalized)) {
    if (normalized.length <= budget) return [normalized];
    const chunks: string[] = [];
    for (let index = 0; index < normalized.length; index += budget) {
      chunks.push(normalized.slice(index, index + budget));
    }
    return chunks;
  }
  const lines: string[] = [];
  let current = "";
  for (const word of normalized.split(" ")) {
    if (!current) {
      current = word;
      continue;
    }
    if (`${current} ${word}`.length <= budget) {
      current = `${current} ${word}`;
    } else {
      lines.push(current);
      current = word;
    }
  }
  if (current) lines.push(current);
  return lines;
}

/** Width and height of an Event Lineage title plus date and kind lines. */
export function lineageLabelMetrics(label: string): {
  labelLines: string[];
  labelWidth: number;
  labelHeight: number;
} {
  const labelLines = wrapLabel(label, LINEAGE_LABEL_CHARS);
  const longest = Math.max(...labelLines.map((line) => line.length), 1);
  return {
    labelLines,
    labelWidth: LABEL_OFFSET_X + longest * CHAR_W,
    labelHeight: labelLines.length * LINE_H + DATE_LINE_H + KIND_LINE_H,
  };
}
