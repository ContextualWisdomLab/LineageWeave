/** Leftover-map rank after IRT main effects (Gabriel singular values). */

export const LEFTOVER_RANK_ZERO_ACTION =
  "Leftover map has no leftover structure after IRT main effects. Open this post.";
export const LEFTOVER_RANK_STRUCTURE_ACTION =
  "Leftover map rank {rank} after IRT main effects. Open this post.";

export function formatLeftoverMapRank(rank: number | null | undefined): string | null {
  if (rank == null || !Number.isInteger(rank) || rank < 0) {
    return null;
  }
  return `rank ${rank}`;
}

export function leftoverMapRankNextAction(rank: number | null | undefined): string | null {
  if (rank == null || !Number.isInteger(rank) || rank < 0) {
    return null;
  }
  if (rank === 0) {
    return LEFTOVER_RANK_ZERO_ACTION;
  }
  return LEFTOVER_RANK_STRUCTURE_ACTION.replace("{rank}", String(rank));
}
