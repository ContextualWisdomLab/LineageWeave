import { getLocale, type Locale } from "./i18n";

const COPY = {
  en: {
    "Work evidence": "Work evidence",
    "Cognitive ability": "Cognitive ability",
    "Work style": "Work style",
    "Work activity": "Work activity",
    "Affective reaction": "Affective reaction",
    "Performance behavior": "Performance behavior",
    "Source evidence": "Source evidence",
    "Open catalog definition": "Open catalog definition",
    "Evidence details": "Evidence details",
    "Catalog release": "Catalog release",
    "Evidence unit": "Evidence unit",
=======
    "Select a work-evidence node to review the records that support it.":
      "Select a work-evidence node to review the records that support it.",
    "No supported work evidence was found in this record.":
      "No supported work evidence was found in this record.",
    "Work evidence is still being prepared. Reopen this record shortly.":
      "Work evidence is still being prepared. Reopen this record shortly.",
    "Work evidence is unavailable. Ask an administrator to retry record analysis.":
      "Work evidence is unavailable. Ask an administrator to retry record analysis.",
    "Work evidence is not enabled. Ask an administrator to enable record analysis, then reopen this record.":
      "Work evidence is not enabled. Ask an administrator to enable record analysis, then reopen this record.",
    "Work evidence is unavailable for this historical cutoff. Review the known body instead.":
      "Work evidence is unavailable for this historical cutoff. Review the known body instead.",
  },
  ko: {
    "Work evidence": "업무 근거",
    "Cognitive ability": "인지 능력",
    "Work style": "업무 성향",
    "Work activity": "업무 활동",
    "Affective reaction": "정서 반응",
    "Performance behavior": "수행 행동",
    "Source evidence": "원문 근거",
    "Open catalog definition": "카탈로그 정의 열기",
    "Evidence details": "근거 상세",
    "Catalog release": "카탈로그 버전",
    "Evidence unit": "근거 단위",
=======
    "Select a work-evidence node to review the records that support it.":
      "업무 근거 노드를 선택하여 이를 뒷받침하는 기록을 검토하세요.",
    "No supported work evidence was found in this record.":
      "이 기록에서 뒷받침되는 업무 근거를 찾지 못했습니다.",
    "Work evidence is still being prepared. Reopen this record shortly.":
      "업무 근거를 준비하고 있습니다. 잠시 후 이 기록을 다시 여세요.",
    "Work evidence is unavailable. Ask an administrator to retry record analysis.":
      "업무 근거를 사용할 수 없습니다. 관리자에게 기록 분석 재시도를 요청하세요.",
    "Work evidence is not enabled. Ask an administrator to enable record analysis, then reopen this record.":
      "업무 근거 분석이 활성화되지 않았습니다. 관리자에게 기록 분석 활성화를 요청한 뒤 이 기록을 다시 여세요.",
    "Work evidence is unavailable for this historical cutoff. Review the known body instead.":
      "이 과거 기준 시점의 업무 근거는 사용할 수 없습니다. 대신 당시 알려진 본문을 검토하세요.",
  },
  zh: {
    "Work evidence": "工作证据",
    "Cognitive ability": "认知能力",
    "Work style": "工作风格",
    "Work activity": "工作活动",
    "Affective reaction": "情感反应",
    "Performance behavior": "绩效行为",
    "Source evidence": "原文证据",
    "Open catalog definition": "打开目录定义",
    "Evidence details": "证据详情",
    "Catalog release": "目录版本",
    "Evidence unit": "证据单元",
=======
    "Select a work-evidence node to review the records that support it.":
      "请选择工作证据节点，查看支持该节点的记录。",
    "No supported work evidence was found in this record.": "此记录中未找到有依据的工作证据。",
    "Work evidence is still being prepared. Reopen this record shortly.":
      "工作证据仍在准备中。请稍后重新打开此记录。",
    "Work evidence is unavailable. Ask an administrator to retry record analysis.":
      "工作证据不可用。请让管理员重试记录分析。",
    "Work evidence is not enabled. Ask an administrator to enable record analysis, then reopen this record.":
      "尚未启用工作证据分析。请让管理员启用记录分析，然后重新打开此记录。",
    "Work evidence is unavailable for this historical cutoff. Review the known body instead.":
      "此历史截止时间没有可用的工作证据。请改为查看当时已知的正文。",
  },
  ja: {
    "Work evidence": "業務エビデンス",
    "Cognitive ability": "認知能力",
    "Work style": "仕事のスタイル",
    "Work activity": "業務活動",
    "Affective reaction": "感情反応",
    "Performance behavior": "遂行行動",
    "Source evidence": "原文の根拠",
    "Open catalog definition": "カタログ定義を開く",
    "Evidence details": "エビデンス詳細",
    "Catalog release": "カタログ版",
    "Evidence unit": "エビデンス単位",
=======
    "Select a work-evidence node to review the records that support it.":
      "業務エビデンスのノードを選択し、それを裏付ける記録を確認してください。",
    "No supported work evidence was found in this record.":
      "この記録には裏付けられた業務エビデンスがありません。",
    "Work evidence is still being prepared. Reopen this record shortly.":
      "業務エビデンスを準備中です。しばらくしてからこの記録を開き直してください。",
    "Work evidence is unavailable. Ask an administrator to retry record analysis.":
      "業務エビデンスを利用できません。管理者に記録分析の再試行を依頼してください。",
    "Work evidence is not enabled. Ask an administrator to enable record analysis, then reopen this record.":
      "業務エビデンス分析が有効ではありません。管理者に記録分析の有効化を依頼してから、この記録を開き直してください。",
    "Work evidence is unavailable for this historical cutoff. Review the known body instead.":
      "この過去の基準時点では業務エビデンスを利用できません。代わりに当時判明していた本文を確認してください。",
  },
  vi: {
    "Work evidence": "Bằng chứng công việc",
    "Cognitive ability": "Năng lực nhận thức",
    "Work style": "Phong cách làm việc",
    "Work activity": "Hoạt động công việc",
    "Affective reaction": "Phản ứng cảm xúc",
    "Performance behavior": "Hành vi thực hiện",
    "Source evidence": "Bằng chứng nguồn",
    "Open catalog definition": "Mở định nghĩa danh mục",
    "Evidence details": "Chi tiết bằng chứng",
    "Catalog release": "Phiên bản danh mục",
    "Evidence unit": "Đơn vị bằng chứng",
=======
    "Select a work-evidence node to review the records that support it.":
      "Chọn một nút bằng chứng công việc để xem các bản ghi hỗ trợ nút đó.",
    "No supported work evidence was found in this record.":
      "Không tìm thấy bằng chứng công việc được hỗ trợ trong bản ghi này.",
    "Work evidence is still being prepared. Reopen this record shortly.":
      "Bằng chứng công việc đang được chuẩn bị. Hãy mở lại bản ghi này sau ít phút.",
    "Work evidence is unavailable. Ask an administrator to retry record analysis.":
      "Bằng chứng công việc không khả dụng. Hãy nhờ quản trị viên thử phân tích lại bản ghi.",
    "Work evidence is not enabled. Ask an administrator to enable record analysis, then reopen this record.":
      "Phân tích bằng chứng công việc chưa được bật. Hãy nhờ quản trị viên bật phân tích bản ghi rồi mở lại bản ghi này.",
    "Work evidence is unavailable for this historical cutoff. Review the known body instead.":
      "Bằng chứng công việc không có tại mốc lịch sử này. Hãy xem phần nội dung đã biết tại thời điểm đó.",
  },
} as const satisfies Record<Locale, Record<string, string>>;

export type OccupationalConstructCopyKey = keyof (typeof COPY)["en"];

/** Return occupational-construct evidence copy in the active product locale. */
export function occupationalConstructText(key: OccupationalConstructCopyKey): string {
  return COPY[getLocale()][key];
}
