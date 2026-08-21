import { getLocale, type Locale } from "./i18n";

const ONTOLOGY_EXPLORER_COPY = {
  en: {
    "Load next relation page": "Load next relation page",
    "Neighborhood truncated. Load the next relation page or inspect one edge.":
      "Neighborhood truncated. Load the next relation page or inspect one edge.",
    "No direct evidence post is attached. Review the provenance reference above.":
      "No direct evidence post is attached. Review the provenance reference above.",
  },
  ko: {
    "Load next relation page": "다음 관계 페이지 불러오기",
    "Neighborhood truncated. Load the next relation page or inspect one edge.":
      "이웃 그래프가 제한되었습니다. 다음 관계 페이지를 불러오거나 연결 하나를 검토하세요.",
    "No direct evidence post is attached. Review the provenance reference above.":
      "직접 연결된 근거 게시물이 없습니다. 위의 출처 참조를 검토하세요.",
  },
  zh: {
    "Load next relation page": "加载下一页关系",
    "Neighborhood truncated. Load the next relation page or inspect one edge.":
      "邻域图已截断。请加载下一页关系或检查一条边。",
    "No direct evidence post is attached. Review the provenance reference above.":
      "未附加直接证据帖子。请检查上方的来源引用。",
  },
  ja: {
    "Load next relation page": "次の関係ページを読み込む",
    "Neighborhood truncated. Load the next relation page or inspect one edge.":
      "近傍グラフは制限されています。次の関係ページを読み込むか、1本のエッジを確認してください。",
    "No direct evidence post is attached. Review the provenance reference above.":
      "直接の根拠投稿は添付されていません。上の出典参照を確認してください。",
  },
  vi: {
    "Load next relation page": "Tải trang quan hệ tiếp theo",
    "Neighborhood truncated. Load the next relation page or inspect one edge.":
      "Vùng lân cận đã bị giới hạn. Hãy tải trang quan hệ tiếp theo hoặc kiểm tra một cạnh.",
    "No direct evidence post is attached. Review the provenance reference above.":
      "Không có bài đăng bằng chứng trực tiếp được đính kèm. Hãy xem tham chiếu nguồn gốc ở trên.",
  },
} as const satisfies Record<Locale, Record<string, string>>;

export type OntologyExplorerCopyKey = keyof (typeof ONTOLOGY_EXPLORER_COPY)["en"];

/** Return ontology-explorer stabilization copy in the active product locale. */
export function ontologyExplorerText(key: OntologyExplorerCopyKey): string {
  return ONTOLOGY_EXPLORER_COPY[getLocale()][key];
}
