import type { Locale } from "./i18n";

/** Localized copy used by the three-pane Customer Master workspace. */
export interface CustomerMasterWorkspaceCopy {
  hierarchyKicker: string;
  hierarchyTitle: string;
  hierarchyHelp: string;
  focusKicker: string;
  focusTitle: string;
  focusHelp: string;
  evidenceKicker: string;
  evidenceTitle: string;
  evidenceHelp: string;
  selectCustomerPrompt: string;
  selectEvidencePrompt: string;
  parentRelationship: string;
  childRelationships: string;
  noParent: string;
  noChildren: string;
  openEvidence: string;
  closeEvidence: string;
  verifiedMaster: string;
  selectedCustomer: string;
  unresolvedRelation: string;
  relationshipAction: string;
  evidenceNextAction: string;
}

const COPY_BY_LOCALE: Record<Locale, CustomerMasterWorkspaceCopy> = {
  en: {
    hierarchyKicker: "01 · Customer hierarchy",
    hierarchyTitle: "Choose a customer in scope",
    hierarchyHelp: "Use the authorized hierarchy for navigation, then keep one customer centered.",
    focusKicker: "02 · Selected customer",
    focusTitle: "Customer relationship focus",
    focusHelp: "Review the visible parent and direct children around the selected customer.",
    evidenceKicker: "03 · Linked evidence",
    evidenceTitle: "Source-backed customer evidence",
    evidenceHelp: "Open a source post to continue into Event Lineage.",
    selectCustomerPrompt: "Select a customer from the hierarchy to center its relationships.",
    selectEvidencePrompt: "Select a customer to inspect its linked source evidence.",
    parentRelationship: "Parent relationship",
    childRelationships: "Direct child relationships",
    noParent: "No parent organization is visible in the authorized scope.",
    noChildren: "No direct child organization is visible in the authorized scope.",
    openEvidence: "Open linked evidence",
    closeEvidence: "Close linked evidence",
    verifiedMaster: "Verified customer master",
    selectedCustomer: "Selected customer",
    unresolvedRelation:
      "This hierarchy relation is unresolved. Review the source data before treating it as authoritative.",
    relationshipAction: "Center this customer",
    evidenceNextAction: "Open the source post to continue in Event Lineage.",
  },
  ko: {
    hierarchyKicker: "01 · 고객 계층",
    hierarchyTitle: "권한 범위에서 고객사 선택",
    hierarchyHelp: "권한이 확인된 계층에서 탐색한 뒤 한 고객사를 가운데에 고정합니다.",
    focusKicker: "02 · 선택 고객사",
    focusTitle: "고객사 관계 중심",
    focusHelp: "선택 고객사를 기준으로 현재 보이는 상위 관계와 직접 하위 관계를 확인합니다.",
    evidenceKicker: "03 · 연결 근거",
    evidenceTitle: "원문으로 확인된 고객 근거",
    evidenceHelp: "원문 글을 열어 이벤트 계보로 이어서 확인합니다.",
    selectCustomerPrompt: "왼쪽 고객 계층에서 고객사를 선택해 관계의 중심으로 두세요.",
    selectEvidencePrompt: "고객사를 선택하면 연결된 원문 근거를 확인할 수 있습니다.",
    parentRelationship: "상위 관계",
    childRelationships: "직접 하위 관계",
    noParent: "권한 범위에서 확인되는 상위 조직이 없습니다.",
    noChildren: "권한 범위에서 확인되는 직접 하위 조직이 없습니다.",
    openEvidence: "연결 근거 열기",
    closeEvidence: "연결 근거 닫기",
    verifiedMaster: "확인된 고객 마스터",
    selectedCustomer: "선택 고객사",
    unresolvedRelation: "이 계층 관계는 미해결 상태입니다. 권위 있는 사실로 사용하기 전에 원천 데이터를 검토하세요.",
    relationshipAction: "이 고객사를 가운데에 고정",
    evidenceNextAction: "원문 글을 열어 이벤트 계보에서 이어서 확인하세요.",
  },
  zh: {
    hierarchyKicker: "01 · 客户层级",
    hierarchyTitle: "在授权范围内选择客户",
    hierarchyHelp: "从已授权层级中导航，并将一个客户固定在中央。",
    focusKicker: "02 · 已选客户",
    focusTitle: "以客户为中心的关系",
    focusHelp: "围绕已选客户查看可见的上级关系和直接下级关系。",
    evidenceKicker: "03 · 关联证据",
    evidenceTitle: "有原文依据的客户证据",
    evidenceHelp: "打开来源文章，继续查看事件谱系。",
    selectCustomerPrompt: "从左侧客户层级中选择客户，将其作为关系中心。",
    selectEvidencePrompt: "选择客户后可查看其关联的来源证据。",
    parentRelationship: "上级关系",
    childRelationships: "直接下级关系",
    noParent: "授权范围内没有可见的上级组织。",
    noChildren: "授权范围内没有可见的直接下级组织。",
    openEvidence: "打开关联证据",
    closeEvidence: "关闭关联证据",
    verifiedMaster: "已验证客户主数据",
    selectedCustomer: "已选客户",
    unresolvedRelation: "此层级关系尚未解决。在作为权威事实使用前，请检查源数据。",
    relationshipAction: "将此客户置于中央",
    evidenceNextAction: "打开来源文章，继续查看事件谱系。",
  },
  ja: {
    hierarchyKicker: "01 · 顧客階層",
    hierarchyTitle: "権限範囲から顧客を選択",
    hierarchyHelp: "認可済みの階層をたどり、1社を中央に固定します。",
    focusKicker: "02 · 選択中の顧客",
    focusTitle: "顧客を中心とした関係",
    focusHelp: "選択した顧客を基準に、表示可能な上位関係と直属の下位関係を確認します。",
    evidenceKicker: "03 · 関連証拠",
    evidenceTitle: "原文に裏付けられた顧客証拠",
    evidenceHelp: "元投稿を開き、イベント系譜で続けて確認します。",
    selectCustomerPrompt: "左の顧客階層から顧客を選び、関係の中心に置いてください。",
    selectEvidencePrompt: "顧客を選択すると、関連する原文証拠を確認できます。",
    parentRelationship: "上位関係",
    childRelationships: "直属の下位関係",
    noParent: "権限範囲内に表示できる上位組織はありません。",
    noChildren: "権限範囲内に表示できる直属の下位組織はありません。",
    openEvidence: "関連証拠を開く",
    closeEvidence: "関連証拠を閉じる",
    verifiedMaster: "確認済み顧客マスター",
    selectedCustomer: "選択中の顧客",
    unresolvedRelation: "この階層関係は未解決です。権威ある事実として扱う前に元データを確認してください。",
    relationshipAction: "この顧客を中央に固定",
    evidenceNextAction: "元投稿を開き、イベント系譜で続けて確認してください。",
  },
  vi: {
    hierarchyKicker: "01 · Cây phân cấp khách hàng",
    hierarchyTitle: "Chọn khách hàng trong phạm vi được cấp quyền",
    hierarchyHelp: "Đi theo cây phân cấp đã được cấp quyền rồi giữ một khách hàng ở vị trí trung tâm.",
    focusKicker: "02 · Khách hàng đã chọn",
    focusTitle: "Quan hệ lấy khách hàng làm trung tâm",
    focusHelp: "Xem quan hệ cấp trên và các quan hệ cấp dưới trực tiếp quanh khách hàng đã chọn.",
    evidenceKicker: "03 · Bằng chứng liên kết",
    evidenceTitle: "Bằng chứng khách hàng có nguồn gốc",
    evidenceHelp: "Mở bài viết nguồn để tiếp tục trong Dòng sự kiện.",
    selectCustomerPrompt: "Chọn một khách hàng từ cây phân cấp bên trái để đặt làm trung tâm quan hệ.",
    selectEvidencePrompt: "Chọn khách hàng để xem bằng chứng nguồn được liên kết.",
    parentRelationship: "Quan hệ cấp trên",
    childRelationships: "Quan hệ cấp dưới trực tiếp",
    noParent: "Không có tổ chức cấp trên nào hiển thị trong phạm vi được cấp quyền.",
    noChildren: "Không có tổ chức cấp dưới trực tiếp nào hiển thị trong phạm vi được cấp quyền.",
    openEvidence: "Mở bằng chứng liên kết",
    closeEvidence: "Đóng bằng chứng liên kết",
    verifiedMaster: "Danh mục khách hàng đã xác minh",
    selectedCustomer: "Khách hàng đã chọn",
    unresolvedRelation: "Quan hệ phân cấp này chưa được giải quyết. Hãy kiểm tra dữ liệu nguồn trước khi coi là sự thật có thẩm quyền.",
    relationshipAction: "Đặt khách hàng này ở trung tâm",
    evidenceNextAction: "Mở bài viết nguồn để tiếp tục trong Dòng sự kiện.",
  },
};

/** Return the complete Customer Master workspace copy for a supported locale. */
export function getCustomerMasterWorkspaceCopy(locale: Locale): CustomerMasterWorkspaceCopy {
  return COPY_BY_LOCALE[locale];
}
