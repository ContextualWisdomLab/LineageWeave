import "./api";

declare module "./api" {
  interface LineageGraphEdge {
    /** Exact persisted channel evidence; an absent key means unavailable, not zero. */
    channel_scores?: Partial<
      Record<"temporal" | "secondary_key" | "text" | "llm", number>
    >;
  }
}
