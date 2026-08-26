import type { PostDetail } from "./api";

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
