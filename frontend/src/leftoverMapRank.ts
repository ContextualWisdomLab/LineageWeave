/** Leftover-map rank after IRT main effects (Gabriel singular values). */

export const LEFTOVER_RANK_ZERO_ACTION =
  "Leftover map has no leftover structure after IRT main effects. Open this post.";
export const LEFTOVER_RANK_STRUCTURE_ACTION =
  "Leftover map rank {rank} after IRT main effects. Open this post.";

export const LEFTOVER_MAP_COMPARE_RANK_LABEL = "Leftover map comparison rank";

export function formatLeftoverMapRank(rank: number | null | undefined): string | null {
  if (rank == null || !Number.isInteger(rank) || rank < 0) {
    return null;
  }
  return `rank ${rank}`;
}
