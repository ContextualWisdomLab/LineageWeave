import { getLocale, type Locale } from "./i18n";

const LINEAGE_DAG_COPY = {
  en: {
    "Lineage legend": "Lineage legend",
    "Root record": "Root record",
    "Branch point": "Branch point",
    "Current record": "Current record",
    "Parent to child": "Parent → child",
    "Reconstructed edges suggest continuation; they do not prove causality or authoritative fact.":
      "Reconstructed edges suggest continuation; they do not prove causality or authoritative fact.",
  },
  ko: {
    "Lineage legend": "계보 범례",
    "Root record": "루트 기록",
    "Branch point": "분기점",
    "Current record": "현재 기록",
    "Parent to child": "부모 → 자식",
    "Reconstructed edges suggest continuation; they do not prove causality or authoritative fact.":
      "재구성된 연결은 후속 관계를 제안할 뿐, 인과관계나 권위 있는 사실을 증명하지 않습니다.",
  },
  zh: {
    "Lineage legend": "谱系图例",
    "Root record": "根记录",
    "Branch point": "分支点",
    "Current record": "当前记录",
    "Parent to child": "父项 → 子项",
    "Reconstructed edges suggest continuation; they do not prove causality or authoritative fact.":
      "重建的连线仅表示可能的延续关系，不证明因果关系或权威事实。",
  },
  ja: {
    "Lineage legend": "系譜の凡例",
    "Root record": "ルート記録",
    "Branch point": "分岐点",
    "Current record": "現在の記録",
    "Parent to child": "親 → 子",
    "Reconstructed edges suggest continuation; they do not prove causality or authoritative fact.":
      "再構成されたエッジは継続関係の候補を示すだけで、因果関係や権威ある事実を証明しません。",
  },
  vi: {
    "Lineage legend": "Chú giải dòng sự kiện",
    "Root record": "Bản ghi gốc",
    "Branch point": "Điểm phân nhánh",
    "Current record": "Bản ghi hiện tại",
    "Parent to child": "Cha → con",
    "Reconstructed edges suggest continuation; they do not prove causality or authoritative fact.":
      "Các cạnh tái dựng chỉ gợi ý quan hệ tiếp nối; chúng không chứng minh quan hệ nhân quả hoặc sự thật có thẩm quyền.",
  },
} as const satisfies Record<Locale, Record<string, string>>;

export type LineageDagCopyKey = keyof (typeof LINEAGE_DAG_COPY)["en"];

/** Return buyer-facing Event Lineage copy in the active product locale. */
export function lineageDagText(key: LineageDagCopyKey): string {
  return LINEAGE_DAG_COPY[getLocale()][key];
}
