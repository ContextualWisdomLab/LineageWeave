import { getLocale, type Locale } from "./i18n";

const ONTOLOGY_EXPLORER_COPY = {
  en: {
    "Load next relation page": "Load next relation page",
    "Neighborhood truncated. Load the next relation page or inspect one edge.":
      "Some related information is not shown. Open a source post to continue.",
    "Neighborhood reached the authorized query bound. Narrow the property filter or reduce traversal depth.":
      "Neighborhood reached the authorized query bound. Narrow the property filter or reduce traversal depth.",
    "No direct evidence post is attached. Review the provenance reference above.":
      "No direct evidence post is attached. Review the provenance reference above.",
  },
  ko: {
    "Load next relation page": "다음 관계 페이지 불러오기",
    "Neighborhood truncated. Load the next relation page or inspect one edge.":
      "일부 관련 정보가 표시되지 않습니다. 계속하려면 원본 글을 여세요.",
    "Neighborhood reached the authorized query bound. Narrow the property filter or reduce traversal depth.":
      "권한 범위의 조회 한도에 도달했습니다. 관계 속성 필터를 좁히거나 탐색 깊이를 줄이세요.",
    "No direct evidence post is attached. Review the provenance reference above.":
      "직접 연결된 근거 게시물이 없습니다. 위의 출처 참조를 검토하세요.",
  },
  zh: {
    "Load next relation page": "加载下一页关系",
    "Neighborhood truncated. Load the next relation page or inspect one edge.":
      "部分相关信息未显示。请打开来源文章继续。",
    "Neighborhood reached the authorized query bound. Narrow the property filter or reduce traversal depth.":
      "已达到授权查询上限。请缩小属性筛选范围或降低遍历深度。",
    "No direct evidence post is attached. Review the provenance reference above.":
      "未附加直接证据帖子。请检查上方的来源引用。",
  },
  ja: {
    "Load next relation page": "次の関係ページを読み込む",
    "Neighborhood truncated. Load the next relation page or inspect one edge.":
      "一部の関連情報は表示されません。続けるには元の投稿を開いてください。",
    "Neighborhood reached the authorized query bound. Narrow the property filter or reduce traversal depth.":
      "認可されたクエリ上限に達しました。プロパティの絞り込みを強めるか、探索深度を下げてください。",
    "No direct evidence post is attached. Review the provenance reference above.":
      "直接の根拠投稿は添付されていません。上の出典参照を確認してください。",
  },
  vi: {
    "Load next relation page": "Tải trang quan hệ tiếp theo",
    "Neighborhood truncated. Load the next relation page or inspect one edge.":
      "Một số thông tin liên quan không được hiển thị. Hãy mở bài viết nguồn để tiếp tục.",
    "Neighborhood reached the authorized query bound. Narrow the property filter or reduce traversal depth.":
      "Đã đạt giới hạn truy vấn được cấp quyền. Hãy thu hẹp bộ lọc thuộc tính hoặc giảm độ sâu duyệt.",
    "No direct evidence post is attached. Review the provenance reference above.":
      "Không có bài đăng bằng chứng trực tiếp được đính kèm. Hãy xem tham chiếu nguồn gốc ở trên.",
  },
} as const satisfies Record<Locale, Record<string, string>>;

export type OntologyExplorerCopyKey = keyof (typeof ONTOLOGY_EXPLORER_COPY)["en"];

/** Return ontology-explorer stabilization copy in the active product locale. */
export function ontologyExplorerText(key: OntologyExplorerCopyKey): string {
  return ONTOLOGY_EXPLORER_COPY[getLocale()][key];
}
