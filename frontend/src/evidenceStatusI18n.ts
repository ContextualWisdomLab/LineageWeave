import { getLocale, type Locale } from "./i18n";

const EVIDENCE_STATUS_COPY = {
  en: {
    Evidence: "Evidence",
    Inference: "Inference",
    Prediction: "Prediction",
    "Directly observed in the source record.": "Directly observed in the source record.",
    "Derived from observed evidence, not directly recorded.":
      "Derived from observed evidence, not directly recorded.",
    "A forecast. Treat as unconfirmed until later evidence arrives.":
      "A forecast. Treat as unconfirmed until later evidence arrives.",
  },
  ko: {
    Evidence: "증거",
    Inference: "추론",
    Prediction: "예측",
    "Directly observed in the source record.": "원본 기록에서 직접 관찰됨.",
    "Derived from observed evidence, not directly recorded.":
      "관찰된 증거로부터 도출됨, 직접 기록된 것이 아님.",
    "A forecast. Treat as unconfirmed until later evidence arrives.":
      "예측 결과입니다. 이후 증거가 확인되기 전까지는 미확정으로 취급하십시오.",
  },
  zh: {
    Evidence: "证据",
    Inference: "推断",
    Prediction: "预测",
    "Directly observed in the source record.": "在原始记录中直接观察到。",
    "Derived from observed evidence, not directly recorded.":
      "从已观察的证据推导得出，并非直接记录。",
    "A forecast. Treat as unconfirmed until later evidence arrives.":
      "这是一项预测。在获得后续证据确认之前，请视为未确认。",
  },
  ja: {
    Evidence: "証拠",
    Inference: "推論",
    Prediction: "予測",
    "Directly observed in the source record.": "元の記録で直接観測されました。",
    "Derived from observed evidence, not directly recorded.":
      "観測された証拠から導出されたもので、直接記録されたものではありません。",
    "A forecast. Treat as unconfirmed until later evidence arrives.":
      "これは予測です。後の証拠が届くまでは未確認として扱ってください。",
  },
  vi: {
    Evidence: "Bằng chứng",
    Inference: "Suy luận",
    Prediction: "Dự đoán",
    "Directly observed in the source record.": "Được quan sát trực tiếp trong bản ghi nguồn.",
    "Derived from observed evidence, not directly recorded.":
      "Được suy ra từ bằng chứng đã quan sát, không được ghi nhận trực tiếp.",
    "A forecast. Treat as unconfirmed until later evidence arrives.":
      "Đây là một dự đoán. Hãy coi là chưa xác nhận cho đến khi có bằng chứng sau này.",
  },
} as const;

export type EvidenceStatusCopyKey = keyof (typeof EVIDENCE_STATUS_COPY)["en"];

/** Return reader-facing evidence/inference/prediction copy in the active product locale. */
export function evidenceStatusText(key: EvidenceStatusCopyKey): string {
  const copy = EVIDENCE_STATUS_COPY as Partial<
    Record<Locale, Record<keyof (typeof EVIDENCE_STATUS_COPY)["en"], string>>
  >;
  return copy[getLocale()]?.[key] ?? EVIDENCE_STATUS_COPY.en[key];
}
