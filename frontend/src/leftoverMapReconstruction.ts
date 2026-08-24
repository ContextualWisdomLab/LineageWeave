/** Two-axis leftover-map reconstruction ``R̂_c = ξ_{1:2} · ζ_{1:2}``. */

export const LEFTOVER_RECONSTRUCTION_ACTION =
  "Two leftover-map axes reconstruct centered leftover R̂ {reconstruction} after IRT main effects. Open this post.";

export function formatLeftoverMapReconstruction(
  reconstruction: number | null | undefined,
): string | null {
  if (reconstruction == null || !Number.isFinite(reconstruction)) {
    return null;
  }
  const magnitude = Math.abs(reconstruction).toFixed(2);
  if (reconstruction > 0) {
    return `R̂ +${magnitude}`;
  }
  if (reconstruction < 0) {
    return `R̂ \u2212${magnitude}`;
  }
  return `R̂ ${magnitude}`;
}
