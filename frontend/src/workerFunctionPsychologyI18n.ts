import { getLocale, type Locale } from "./i18n";

const WORKER_FUNCTION_PSYCHOLOGY_COPY = {
  en: {
    "Work psychology": "Work psychology",
    "Open the DOT/FJA worker-function glossary entry in DOT Appendix B.":
      "Open the DOT/FJA worker-function glossary entry in DOT Appendix B.",
    "Work psychology details are not ready. Select a worker function or try again after the catalog finishes loading.":
      "Work psychology details are not ready. Select a worker function or try again after the catalog finishes loading.",
    "Catalog dimensions": "Catalog dimensions",
    "Reference": "Reference",
    "Select a worker function to review its I/O psychology demand profile.":
      "Select a worker function to review its I/O psychology demand profile.",
  },
  ko: {
    "Work psychology": "직무 심리",
    "Open the DOT/FJA worker-function glossary entry in DOT Appendix B.":
      "DOT 부록 B의 DOT/FJA 직무 기능 용어집 항목을 엽니다.",
    "Work psychology details are not ready. Select a worker function or try again after the catalog finishes loading.":
      "직무 심리 상세 정보가 아직 준비되지 않았습니다. 직무 기능을 선택하거나 카탈로그를 불러온 뒤 다시 시도하세요.",
    "Catalog dimensions": "카탈로그 차원",
    "Reference": "참고 문헌",
    "Select a worker function to review its I/O psychology demand profile.":
      "I/O 심리학 수요 프로필을 검토하려면 직무 기능을 선택하세요.",
  },
  zh: {
    "Work psychology": "工作心理",
    "Open the DOT/FJA worker-function glossary entry in DOT Appendix B.":
      "打开 DOT 附录 B 的 DOT/FJA 工作职能词条。",
    "Work psychology details are not ready. Select a worker function or try again after the catalog finishes loading.":
      "工作心理详情尚未就绪。请选择一项工作职能，或在目录加载完成后重试。",
    "Catalog dimensions": "目录维度",
    "Reference": "参考",
    "Select a worker function to review its I/O psychology demand profile.":
      "选择一项工作职能以查看其 I/O 心理学需求画像。",
  },
  ja: {
    "Work psychology": "仕事の心理",
    "Open the DOT/FJA worker-function glossary entry in DOT Appendix B.":
      "DOT 付録 B の DOT/FJA 作業機能用語の項目を開きます。",
    "Work psychology details are not ready. Select a worker function or try again after the catalog finishes loading.":
      "仕事の心理に関する詳細はまだ準備できていません。作業機能を選択するか、カタログの読み込み後に再試行してください。",
    "Catalog dimensions": "カタログの次元",
    "Reference": "引用文献",
    "Select a worker function to review its I/O psychology demand profile.":
      "I/O 心理学の要求プロファイルを確認するには作業機能を選択してください。",
  },
  vi: {
    "Work psychology": "Tâm lý công việc",
    "Open the DOT/FJA worker-function glossary entry in DOT Appendix B.":
      "Mở mục thuật ngữ chức năng công việc DOT/FJA trong Phụ lục B của DOT.",
    "Work psychology details are not ready. Select a worker function or try again after the catalog finishes loading.":
      "Chi tiết tâm lý công việc chưa sẵn sàng. Hãy chọn một chức năng công việc hoặc thử lại sau khi danh mục tải xong.",
    "Catalog dimensions": "Các khía cạnh danh mục",
    "Reference": "Tham khảo",
    "Select a worker function to review its I/O psychology demand profile.":
      "Chọn một chức năng công việc để xem hồ sơ nhu cầu Tâm lý I/O.",
  },
} as const satisfies Record<Locale, Record<string, string>>;

export type WorkerFunctionPsychologyCopyKey = keyof (typeof WORKER_FUNCTION_PSYCHOLOGY_COPY)["en"];

/** Return worker-function I/O psychology copy for the active product locale. */
export function workerFunctionPsychologyText(key: WorkerFunctionPsychologyCopyKey): string {
  return WORKER_FUNCTION_PSYCHOLOGY_COPY[getLocale()][key];
}
