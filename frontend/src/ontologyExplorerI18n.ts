import { getLocale, type Locale } from "./i18n";

const ONTOLOGY_EXPLORER_COPY = {
  en: {
    "Load next relation page": "Load next relation page",
    "Neighborhood truncated. Load the next relation page or inspect one edge.":
      "Some related information is not shown. Open a source post to continue.",
    "Neighborhood reached the authorized query bound. Narrow the property filter or reduce traversal depth.":
      "Too many related records match. Narrow the relationship filter or open a source post.",
    "No direct evidence post is attached. Review the provenance reference above.":
      "No source post is attached to this relationship. Review the connected records instead.",
  },
  ko: {
    "Load next relation page": "다음 관계 페이지 불러오기",
    "Neighborhood truncated. Load the next relation page or inspect one edge.":
      "일부 관련 정보가 표시되지 않습니다. 계속하려면 원본 글을 여세요.",
    "Neighborhood reached the authorized query bound. Narrow the property filter or reduce traversal depth.":
      "관련 기록이 너무 많습니다. 관계 필터를 좁히거나 원본 글을 여세요.",
    "No direct evidence post is attached. Review the provenance reference above.":
      "이 관계에 연결된 원본 글이 없습니다. 대신 연결된 기록을 검토하세요.",
  },
  zh: {
    "Load next relation page": "加载下一页关系",
    "Neighborhood truncated. Load the next relation page or inspect one edge.":
      "部分相关信息未显示。请打开来源文章继续。",
    "Neighborhood reached the authorized query bound. Narrow the property filter or reduce traversal depth.":
      "匹配的相关记录过多。请缩小关系筛选范围或打开来源文章。",
    "No direct evidence post is attached. Review the provenance reference above.":
      "此关系未关联来源文章。请改为检查相连记录。",
  },
  ja: {
    "Load next relation page": "次の関係ページを読み込む",
    "Neighborhood truncated. Load the next relation page or inspect one edge.":
      "一部の関連情報は表示されません。続けるには元の投稿を開いてください。",
    "Neighborhood reached the authorized query bound. Narrow the property filter or reduce traversal depth.":
      "関連する記録が多すぎます。関係フィルターを絞るか、元の投稿を開いてください。",
    "No direct evidence post is attached. Review the provenance reference above.":
      "この関係に元の投稿は紐付いていません。代わりに接続された記録を確認してください。",
  },
  vi: {
    "Load next relation page": "Tải trang quan hệ tiếp theo",
    "Neighborhood truncated. Load the next relation page or inspect one edge.":
      "Một số thông tin liên quan không được hiển thị. Hãy mở bài viết nguồn để tiếp tục.",
    "Neighborhood reached the authorized query bound. Narrow the property filter or reduce traversal depth.":
      "Có quá nhiều bản ghi liên quan phù hợp. Hãy thu hẹp bộ lọc quan hệ hoặc mở bài viết nguồn.",
    "No direct evidence post is attached. Review the provenance reference above.":
      "Quan hệ này không có bài viết nguồn đính kèm. Hãy xem các bản ghi được kết nối thay thế.",
  },
} as const satisfies Record<Locale, Record<string, string>>;

export type OntologyExplorerCopyKey = keyof (typeof ONTOLOGY_EXPLORER_COPY)["en"];

/** Return ontology-explorer stabilization copy in the active product locale. */
export function ontologyExplorerText(key: OntologyExplorerCopyKey): string {
  return ONTOLOGY_EXPLORER_COPY[getLocale()][key];
}
