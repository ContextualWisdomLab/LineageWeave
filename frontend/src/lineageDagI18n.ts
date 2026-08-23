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
  },
} as const satisfies Record<Locale, Record<string, string>>;

export type LineageDagCopyKey = keyof (typeof LINEAGE_DAG_COPY)["en"];

/** Return reader-facing Event Lineage copy in the active product locale. */
export function lineageDagText(key: LineageDagCopyKey): string {
  return LINEAGE_DAG_COPY[getLocale()][key];
}
