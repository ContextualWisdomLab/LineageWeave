import { getLocale, type Locale } from "./i18n";

const LINEAGE_DAG_COPY = {
  en: {
    "Lineage legend": "Lineage legend",
    "Root record": "Root record",
    "Branch point": "Branch point",
    "Current record": "Current record",
    "Parent to child": "Parent → child",
    Topic: "Topic",
    "Predecessor to successor": "Predecessor → successor",
    Earlier: "Earlier",
    Later: "Later",
    "Reconstructed edges suggest continuation; they do not prove causality or authoritative fact.":
      "Reconstructed edges suggest continuation; they do not prove causality or authoritative fact.",
    "No reconstructed lineage yet. Add eligible source records, then rebuild Event Lineage.":
      "No reconstructed lineage yet. Add eligible source records, then rebuild Event Lineage.",
    "This chain has no branch point: each record matched exactly one likely predecessor. See the evidence trail below for why each link was made.":
      "This chain has no branch point: each record matched exactly one likely predecessor. See the evidence trail below for why each link was made.",
    "Channel breakdown": "Channel breakdown",
    "Temporal proximity": "Temporal proximity",
    "Secondary key match": "Secondary key match",
    "Text similarity": "Text similarity",
    "LLM judgment": "LLM judgment",
  },
  ko: {
    "Lineage legend": "계보 범례",
    "Root record": "루트 기록",
    "Branch point": "분기점",
    "Current record": "현재 기록",
    "Parent to child": "부모 → 자식",
    Topic: "주제",
    "Predecessor to successor": "선·후행",
    Earlier: "선행",
    Later: "후행",
    "Reconstructed edges suggest continuation; they do not prove causality or authoritative fact.":
      "재구성된 연결은 후속 관계를 제안할 뿐, 인과관계나 권위 있는 사실을 증명하지 않습니다.",
    "No reconstructed lineage yet. Add eligible source records, then rebuild Event Lineage.":
      "아직 재구성된 계보가 없습니다. 대상 원본 기록을 추가한 뒤 이벤트 계보를 다시 만드세요.",
    "This chain has no branch point: each record matched exactly one likely predecessor. See the evidence trail below for why each link was made.":
      "이 사슬에는 분기점이 없습니다: 각 기록이 가장 유력한 선행 기록을 정확히 하나씩 찾았기 때문입니다. 아래 근거 내역에서 각 연결의 이유를 확인하세요.",
    "Channel breakdown": "채널별 근거",
    "Temporal proximity": "시간 근접도",
    "Secondary key match": "보조 키 일치",
    "Text similarity": "텍스트 유사도",
    "LLM judgment": "LLM 판단",
  },
  zh: {
    "Lineage legend": "谱系图例",
    "Root record": "根记录",
    "Branch point": "分支点",
    "Current record": "当前记录",
    "Parent to child": "父项 → 子项",
    Topic: "主题",
    "Predecessor to successor": "先后行",
    Earlier: "先行",
    Later: "后行",
    "Reconstructed edges suggest continuation; they do not prove causality or authoritative fact.":
      "重建的连线仅表示可能的延续关系，不证明因果关系或权威事实。",
    "No reconstructed lineage yet. Add eligible source records, then rebuild Event Lineage.":
      "尚无重建的谱系。请先添加符合条件的源记录，然后重建事件谱系。",
    "This chain has no branch point: each record matched exactly one likely predecessor. See the evidence trail below for why each link was made.":
      "此链没有分支点：每条记录都恰好匹配到一个最可能的前序记录。请查看下方的证据记录，了解每条连接的原因。",
    "Channel breakdown": "通道细分",
    "Temporal proximity": "时间接近度",
    "Secondary key match": "辅助键匹配",
    "Text similarity": "文本相似度",
    "LLM judgment": "LLM 判断",
  },
  ja: {
    "Lineage legend": "系譜の凡例",
    "Root record": "ルート記録",
    "Branch point": "分岐点",
    "Current record": "現在の記録",
    "Parent to child": "親 → 子",
    Topic: "トピック",
    "Predecessor to successor": "先後",
    Earlier: "先行",
    Later: "後行",
    "Reconstructed edges suggest continuation; they do not prove causality or authoritative fact.":
      "再構成されたエッジは継続関係の候補を示すだけで、因果関係や権威ある事実を証明しません。",
    "No reconstructed lineage yet. Add eligible source records, then rebuild Event Lineage.":
      "再構成された系譜はまだありません。対象となる元記録を追加してから、イベント系譜を再構築してください。",
    "This chain has no branch point: each record matched exactly one likely predecessor. See the evidence trail below for why each link was made.":
      "この鎖に分岐点はありません。各記録がそれぞれ最も可能性の高い先行記録を1件だけ見つけたためです。各リンクの理由は下の証跡でご確認ください。",
    "Channel breakdown": "チャネル内訳",
    "Temporal proximity": "時間的近接度",
    "Secondary key match": "副次キー一致",
    "Text similarity": "テキスト類似度",
    "LLM judgment": "LLM判定",
  },
  vi: {
    "Lineage legend": "Chú giải dòng sự kiện",
    "Root record": "Bản ghi gốc",
    "Branch point": "Điểm phân nhánh",
    "Current record": "Bản ghi hiện tại",
    "Parent to child": "Cha → con",
    Topic: "Chủ đề",
    "Predecessor to successor": "Trước → sau",
    Earlier: "Trước",
    Later: "Sau",
    "Reconstructed edges suggest continuation; they do not prove causality or authoritative fact.":
      "Các cạnh tái dựng chỉ gợi ý quan hệ tiếp nối; chúng không chứng minh quan hệ nhân quả hoặc sự thật có thẩm quyền.",
    "No reconstructed lineage yet. Add eligible source records, then rebuild Event Lineage.":
      "Chưa có dòng sự kiện được tái dựng. Hãy thêm các bản ghi nguồn đủ điều kiện rồi tái dựng Dòng sự kiện.",
    "This chain has no branch point: each record matched exactly one likely predecessor. See the evidence trail below for why each link was made.":
      "Chuỗi này không có điểm phân nhánh: mỗi bản ghi chỉ khớp với đúng một bản ghi tiền nhiệm khả dĩ nhất. Xem bằng chứng bên dưới để biết lý do của từng liên kết.",
    "Channel breakdown": "Phân tích theo kênh",
    "Temporal proximity": "Độ gần thời gian",
    "Secondary key match": "Khớp khóa phụ",
    "Text similarity": "Độ tương đồng văn bản",
    "LLM judgment": "Đánh giá LLM",
  },
} as const satisfies Record<Locale, Record<string, string>>;

export type LineageDagCopyKey = keyof (typeof LINEAGE_DAG_COPY)["en"];

/** Return reader-facing Event Lineage copy in the active product locale. */
export function lineageDagText(key: LineageDagCopyKey): string {
  return LINEAGE_DAG_COPY[getLocale()][key];
}
