import { getLocale, type Locale } from "./i18n";

const WORKER_FUNCTION_PSYCHOLOGY_COPY = {
  en: {
    "Work psychology": "Work psychology",
    "Open the DOT/FJA worker-function glossary entry in DOT Appendix B.":
      "Open the DOT/FJA worker-function glossary entry in DOT Appendix B.",
    "Work psychology catalog is unavailable. Ask an administrator to enable the ontology catalog projection.":
      "Work psychology catalog is unavailable. Ask an administrator to enable the ontology catalog projection.",
    "Catalog dimensions": "Catalog dimensions",
    "Reference": "Reference",
    "Select a worker function to review its I/O psychology demand profile.":
      "Select a worker function to review its I/O psychology demand profile.",
  },
  ko: {
    "Work psychology": "직무 심리",
    "Open the DOT/FJA worker-function glossary entry in DOT Appendix B.":
      "DOT 부록 B의 DOT/FJA 직무 기능 용어집 항목을 엽니다.",
    "Work psychology catalog is unavailable. Ask an administrator to enable the ontology catalog projection.":
      "직무 심리 카탈로그를 사용할 수 없습니다. 인증 관리자가 온톨로지 카탈로그 투영을 활성화하도록 요청하세요.",
    "Catalog dimensions": "카탈로그 차원",
    "Reference": "참고 문헌",
    "Select a worker function to review its I/O psychology demand profile.":
      "I/O 심리학 수요 프로필을 검토하려면 직무 기능을 선택하세요.",
  },
  zh: {
    "Work psychology": "工作心理",
    "Open the DOT/FJA worker-function glossary entry in DOT Appendix B.":
      "打开 DOT 附录 B 的 DOT/FJA 工作职能词条。",
    "Work psychology catalog is unavailable. Ask an administrator to enable the ontology catalog projection.":
      "工作心理目录暂不可用。请联系管理员启用本体目录投影。",
    "Catalog dimensions": "目录维度",
    "Reference": "参考",
    "Select a worker function to review its I/O psychology demand profile.":
      "选择一项工作职能以查看其 I/O 心理学需求画像。",
  },
  ja: {
    "Work psychology": "仕事の心理",
    "Open the DOT/FJA worker-function glossary entry in DOT Appendix B.":
      "DOT 付録 B の DOT/FJA 作業機能用語の項目を開きます。",
    "Work psychology catalog is unavailable. Ask an administrator to enable the ontology catalog projection.":
      "仕事の心理カタログは利用できません。管理者にオントロジーカタログ投影を有効にするよう依頼してください。",
    "Catalog dimensions": "カタログの次元",
    "Reference": "引用文献",
    "Select a worker function to review its I/O psychology demand profile.":
      "I/O 心理学の要求プロファイルを確認するには作業機能を選択してください。",
  },
  vi: {
    "Work psychology": "Tâm lý công việc",
    "Open the DOT/FJA worker-function glossary entry in DOT Appendix B.":
      "Mở mục thuật ngữ chức năng công việc DOT/FJA trong Phụ lục B của DOT.",
    "Work psychology catalog is unavailable. Ask an administrator to enable the ontology catalog projection.":
      "Danh mục tâm lý công việc hiện không khả dụng. Hãy yêu cầu quản trị viên bật phép chiếu danh mục ontology.",
    "Catalog dimensions": "Các khía cạnh danh mục",
    "Reference": "Tham khảo",
    "Select a worker function to review its I/O psychology demand profile.":
      "Chọn một chức năng công việc để xem hồ sơ nhu cầu Tâm lý I/O.",
  },
} as const;

export type WorkerFunctionPsychologyCopyKey = keyof (typeof WORKER_FUNCTION_PSYCHOLOGY_COPY)["en"];

/** Return worker-function I/O psychology copy for the active product locale. */
export function workerFunctionPsychologyText(key: WorkerFunctionPsychologyCopyKey): string {
  const copy = WORKER_FUNCTION_PSYCHOLOGY_COPY as Partial<
    Record<Locale, Record<keyof (typeof WORKER_FUNCTION_PSYCHOLOGY_COPY)["en"], string>>
  >;
  return copy[getLocale()]?.[key] ?? WORKER_FUNCTION_PSYCHOLOGY_COPY.en[key];
}
