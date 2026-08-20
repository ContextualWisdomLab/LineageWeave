import "./api";

declare module "./api" {
  interface LineageChannelEvidence {
    /** Stable public signal code; missing signals are absent, never zero-filled. */
    signal_code: "temporal" | "secondary_key" | "text" | "llm";
    signal_label: string;
    score: number;
    weight: number;
    contribution: number;
    rank: number;
  }

  interface LineageGraphEdge {
    /** Backward-compatible exact score map. */
    channel_scores?: Partial<
      Record<"temporal" | "secondary_key" | "text" | "llm", number>
    >;
    /** Ranked, auditable evidence from the persisted reconstruction run. */
    channel_evidence?: LineageChannelEvidence[];
    reconstruction_version?: string | null;
    reconstructed_at?: string | null;
  }
}
