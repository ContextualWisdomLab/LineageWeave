import type { PostDetail, VoiceTaxonomySummary } from "./api";

type VoiceCode = VoiceTaxonomySummary["category_memberships"][number]["voice_concept_code"];

export const VOICE_LABELS = {
  voc: "Voice of Customer",
  vocc: "Voice of Customer's Customer",
  voco: "Voice of Competitor",
  vom: "Voice of Market",
  vop: "Voice of Partner",
  vos: "Voice of Supplier",
  voe: "Voice of Employee",
  vob: "Voice of Business",
  vor: "Voice of Regulator",
  voi: "Voice of Investor",
  voso: "Voice of Society",
  vops: "Voice of Process",
} as const satisfies Record<VoiceCode, string>;

export function postPrimaryVoiceLabel(
  post: Pick<PostDetail, "voice_types" | "voc_type_label" | "voc_type_code">,
  knowledgeCutoff?: string | null,
): string {
  return post.voice_types?.find((voice) => voice.is_primary)?.label ??
    (knowledgeCutoff
      ? "Perspective unavailable at this cutoff"
      : post.voc_type_label ?? post.voc_type_code);
}

export function canAuthorVoice(canExtract: boolean, knowledgeCutoff?: string | null): boolean {
  return canExtract && !knowledgeCutoff;
}
