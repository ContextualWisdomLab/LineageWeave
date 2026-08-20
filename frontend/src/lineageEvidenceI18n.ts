import { getLocale, type Locale } from "./i18n";

export const LINEAGE_EVIDENCE_KEYS = [
  "whyLinked",
  "nextAction",
  "tableLabel",
  "from",
  "to",
  "fused",
  "time",
  "secondaryKey",
  "text",
  "llm",
  "notAvailable",
] as const;

export type LineageEvidenceKey = (typeof LINEAGE_EVIDENCE_KEYS)[number];

const ENGLISH: Record<LineageEvidenceKey, string> = {
  whyLinked: "Why these posts are linked",
  nextAction: "Review exact channel scores before relying on this connection.",
  tableLabel: "Lineage evidence scores",
  from: "From",
  to: "To",
  fused: "Fused score",
  time: "Time proximity",
  secondaryKey: "Secondary-key match",
  text: "Text similarity",
  llm: "LLM adjudication",
  notAvailable: "Not available",
};

const TRANSLATIONS: Record<
  Locale,
  Record<LineageEvidenceKey, string>
> = {
  en: ENGLISH,
  ko: {
    whyLinked: "이 게시물이 연결된 이유",
    nextAction: "이 연결을 신뢰하기 전에 채널별 정확한 점수를 검토하세요.",
    tableLabel: "계보 근거 점수",
    from: "출발 게시물",
    to: "도착 게시물",
    fused: "통합 점수",
    time: "시간 근접도",
    secondaryKey: "보조 키 일치",
    text: "텍스트 유사도",
    llm: "LLM 판정",
    notAvailable: "사용할 수 없음",
  },
  zh: {
    whyLinked: "这些帖子为何相连",
    nextAction: "在依赖此连接前，请先检查各通道的精确分数。",
    tableLabel: "谱系证据分数",
    from: "起始帖子",
    to: "目标帖子",
    fused: "融合分数",
    time: "时间接近度",
    secondaryKey: "次级键匹配",
    text: "文本相似度",
    llm: "LLM 判定",
    notAvailable: "不可用",
  },
  ja: {
    whyLinked: "これらの投稿が関連付けられた理由",
    nextAction:
      "この関連を信頼する前に、各チャネルの正確なスコアを確認してください。",
    tableLabel: "系譜の証拠スコア",
    from: "起点の投稿",
    to: "対象の投稿",
    fused: "統合スコア",
    time: "時間的近接度",
    secondaryKey: "補助キー一致",
    text: "テキスト類似度",
    llm: "LLM 判定",
    notAvailable: "利用不可",
  },
  vi: {
    whyLinked: "Vì sao các bài viết này được liên kết",
    nextAction:
      "Hãy xem điểm chính xác của từng kênh trước khi dựa vào liên kết này.",
    tableLabel: "Điểm bằng chứng dòng sự kiện",
    from: "Bài viết nguồn",
    to: "Bài viết đích",
    fused: "Điểm tổng hợp",
    time: "Độ gần thời gian",
    secondaryKey: "Khớp khóa phụ",
    text: "Độ tương đồng văn bản",
    llm: "Phán định LLM",
    notAvailable: "Không khả dụng",
  },
};

/** Return complete Buyer evidence copy for the active or supplied locale. */
export function lineageEvidenceText(
  key: LineageEvidenceKey,
  locale: Locale = getLocale(),
): string {
  return TRANSLATIONS[locale][key];
}
