/**
 * Reproducibility-digest helpers for an analysis-run detail.
 *
 * The home list stays aggregates-only. Detail shows a 12-character
 * prefix so assistive technology hears `Code` / `Config` values, then
 * a disclosure button reveals the full digest (WCAG 2.2 SC 1.4.13;
 * WAI-ARIA APG Disclosure). Native `title` tooltips are pointer-only
 * and must not be the only way to verify a digest against the API.
 */

/** Git-style prefix length shown before the operator opens the full digest. */
export const ANALYSIS_RUN_DIGEST_PREFIX_LENGTH = 12;

/** Which digest the disclosure button reveals. */
export type AnalysisRunDigestKind = "code" | "config";

/**
 * Visible prefix used on the disclosure button.
 *
 * @param digest - Full code revision SHA or configuration SHA-256.
 * @returns The first 12 characters, or the whole string when shorter.
 */
export function analysisRunDigestPrefix(digest: string): string {
  return digest.slice(0, ANALYSIS_RUN_DIGEST_PREFIX_LENGTH);
}

/**
 * Visible label for a digest kind. Keep this as the button contents so
 * `aria-label` does not replace the prefix (AccName 1.1).
 *
 * @param kind - Code revision or configuration digest.
 * @returns `Code` or `Config`.
 */
export function analysisRunDigestKindLabel(kind: AnalysisRunDigestKind): string {
  switch (kind) {
    case "code":
      return "Code";
    case "config":
      return "Config";
    default: {
      const _exhaustive: never = kind;
      return _exhaustive;
    }
  }
}

/**
 * Button text the operator hears and sees. The full digest is not part
 * of the name; it appears only after activation.
 *
 * @param kind - Code revision or configuration digest.
 * @param digest - Full digest string from the run payload.
 * @returns For example `Code abcdef012345`.
 */
export function analysisRunDigestButtonLabel(
  kind: AnalysisRunDigestKind,
  digest: string,
): string {
  return `${analysisRunDigestKindLabel(kind)} ${analysisRunDigestPrefix(digest)}`;
}

/**
 * Next action shown above the prefixes. True for keyboard, pointer, and
 * assistive technology — unlike “Hover a prefix”.
 */
export function analysisRunDigestNextAction(): string {
  return "Activate a prefix to read the full digest and match the API payload.";
}
