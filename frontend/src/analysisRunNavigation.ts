/** Immutable analysis-run clock context carried across post navigation. */
export type AnalysisRunNavigationContext = {
  knowledgeCutoff: string;
  visiblePosts: Array<{ post_id: string; live_after_cutoff?: boolean }>;
};

/** Resolve the selected target's own write-clock flag under the originating run cutoff. */
export function analysisRunTargetClock(
  context: AnalysisRunNavigationContext,
  postId: string,
): { liveAfterCutoff: boolean; knowledgeCutoff: string } {
  const target = context.visiblePosts.find((post) => post.post_id === postId);
  return {
    liveAfterCutoff: Boolean(target?.live_after_cutoff),
    knowledgeCutoff: context.knowledgeCutoff,
  };
}
