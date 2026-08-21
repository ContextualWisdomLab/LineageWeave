import type { Locale } from "../i18n";
import { useLocale } from "../i18n";
import type { TeppProjectHistoryValidation } from "../projectHistory";
import "./TeppProjectHistoryEvidence.css";

interface Copy {
  heading: string;
  eyebrow: string;
  boundary: string;
  participants: (count: number) => string;
  span: string;
  findings: string;
  noFindings: string;
  openEvidence: (label: string) => string;
  status: Record<Exclude<TeppProjectHistoryValidation["status"], "validated">, string>;
  findingLabels: Record<string, string>;
}

const COPY: Record<Locale, Copy> = {
  en: {
    heading: "TEPP temporal validation",
    eyebrow: "TEPP-connected evidence",
    boundary: "Temporal association only; this does not identify a cause.",
    participants: (count) => `${count} participants in the supplied evidence`,
    span: "Validated history span",
    findings: "TEPP findings",
    noFindings: "TEPP ordered the explicit events and returned no additional finding.",
    openEvidence: (label) => `Open evidence: ${label}`,
    status: {
      not_configured: "Configure the TEPP project-history endpoint, then retry this timeline.",
      unavailable: "TEPP is unavailable. Read the canonical timeline now and retry validation later.",
      invalid_evidence: "Open the source evidence and correct the project-history contract before retrying TEPP.",
    },
    findingLabels: {
      contract_award_before_focus: "A contract-award event precedes the selected event.",
      specification_change_before_focus: "A specification-change event precedes the selected event.",
      delivery_before_focus: "A delivery event precedes the selected event.",
      handoff_before_focus: "A handoff record precedes the selected event.",
      rebid_after_focus: "A rebid event follows the selected event.",
      specification_change_and_handoff_before_focus:
        "Specification-change and handoff records both precede the selected event.",
    },
  },
  ko: {
    heading: "TEPP 시간 검증",
    eyebrow: "TEPP 연계 근거",
    boundary: "시간적 연관만 제시하며 원인을 식별한 결과가 아닙니다.",
    participants: (count) => `제공된 근거의 참여자 ${count}명`,
    span: "검증된 이력 구간",
    findings: "TEPP 검토 결과",
    noFindings: "TEPP가 명시적 이벤트를 정렬했으며 추가 검토 결과는 없습니다.",
    openEvidence: (label) => `근거 열기: ${label}`,
    status: {
      not_configured: "TEPP 프로젝트 이력 엔드포인트를 설정한 뒤 이 타임라인을 다시 검증하세요.",
      unavailable: "TEPP를 사용할 수 없습니다. 현재는 기준 타임라인을 읽고 나중에 검증을 다시 실행하세요.",
      invalid_evidence: "원천 근거를 열어 프로젝트 이력 계약을 바로잡은 뒤 TEPP를 다시 실행하세요.",
    },
    findingLabels: {
      contract_award_before_focus: "선택한 이벤트보다 앞선 수주 확정 기록이 있습니다.",
      specification_change_before_focus: "선택한 이벤트보다 앞선 사양 변경 기록이 있습니다.",
      delivery_before_focus: "선택한 이벤트보다 앞선 납품 기록이 있습니다.",
      handoff_before_focus: "선택한 이벤트보다 앞선 인수인계 기록이 있습니다.",
      rebid_after_focus: "선택한 이벤트 뒤에 재입찰 기록이 있습니다.",
      specification_change_and_handoff_before_focus:
        "선택한 이벤트보다 앞서 사양 변경과 인수인계 기록이 모두 있습니다.",
    },
  },
  zh: {
    heading: "TEPP 时间验证",
    eyebrow: "TEPP 关联证据",
    boundary: "仅表示时间关联，不等于识别了原因。",
    participants: (count) => `所提供证据中的参与者：${count} 人`,
    span: "已验证的历史区间",
    findings: "TEPP 结果",
    noFindings: "TEPP 已对明确事件排序，未返回其他结果。",
    openEvidence: (label) => `打开证据：${label}`,
    status: {
      not_configured: "请配置 TEPP 项目历史端点，然后重新验证此时间线。",
      unavailable: "TEPP 当前不可用。请先阅读标准时间线，稍后重试验证。",
      invalid_evidence: "请打开源证据并修正项目历史契约，然后重试 TEPP。",
    },
    findingLabels: {
      contract_award_before_focus: "合同授予记录早于所选事件。",
      specification_change_before_focus: "规格变更记录早于所选事件。",
      delivery_before_focus: "交付记录早于所选事件。",
      handoff_before_focus: "交接记录早于所选事件。",
      rebid_after_focus: "重新投标记录晚于所选事件。",
      specification_change_and_handoff_before_focus: "规格变更和交接记录均早于所选事件。",
    },
  },
  ja: {
    heading: "TEPP 時間検証",
    eyebrow: "TEPP 連携根拠",
    boundary: "時間的関連のみを示し、原因を特定した結果ではありません。",
    participants: (count) => `提供根拠の参加者 ${count} 名`,
    span: "検証済み履歴期間",
    findings: "TEPP の結果",
    noFindings: "TEPP は明示的イベントを並べ替え、追加の結果は返しませんでした。",
    openEvidence: (label) => `根拠を開く: ${label}`,
    status: {
      not_configured: "TEPP プロジェクト履歴エンドポイントを設定し、このタイムラインを再検証してください。",
      unavailable: "TEPP は利用できません。標準タイムラインを読み、後で検証を再試行してください。",
      invalid_evidence: "原典根拠を開いてプロジェクト履歴契約を修正し、TEPP を再実行してください。",
    },
    findingLabels: {
      contract_award_before_focus: "選択イベントより前に受注確定記録があります。",
      specification_change_before_focus: "選択イベントより前に仕様変更記録があります。",
      delivery_before_focus: "選択イベントより前に納品記録があります。",
      handoff_before_focus: "選択イベントより前に引継ぎ記録があります。",
      rebid_after_focus: "選択イベントの後に再入札記録があります。",
      specification_change_and_handoff_before_focus: "仕様変更と引継ぎの記録が選択イベントより前にあります。",
    },
  },
  vi: {
    heading: "Xác thực thời gian TEPP",
    eyebrow: "Bằng chứng liên kết TEPP",
    boundary: "Chỉ thể hiện mối liên hệ theo thời gian; kết quả này không xác định nguyên nhân.",
    participants: (count) => `${count} chủ thể trong bằng chứng đã cung cấp`,
    span: "Khoảng lịch sử đã xác thực",
    findings: "Kết quả TEPP",
    noFindings: "TEPP đã sắp xếp các sự kiện tường minh và không trả về kết quả bổ sung.",
    openEvidence: (label) => `Mở bằng chứng: ${label}`,
    status: {
      not_configured: "Hãy cấu hình điểm cuối lịch sử dự án TEPP rồi xác thực lại dòng thời gian này.",
      unavailable: "TEPP hiện không khả dụng. Hãy đọc dòng thời gian chuẩn và thử xác thực lại sau.",
      invalid_evidence: "Hãy mở bằng chứng nguồn, sửa hợp đồng lịch sử dự án rồi chạy lại TEPP.",
    },
    findingLabels: {
      contract_award_before_focus: "Bản ghi trao hợp đồng có trước sự kiện được chọn.",
      specification_change_before_focus: "Bản ghi thay đổi đặc tả có trước sự kiện được chọn.",
      delivery_before_focus: "Bản ghi bàn giao có trước sự kiện được chọn.",
      handoff_before_focus: "Bản ghi chuyển giao có trước sự kiện được chọn.",
      rebid_after_focus: "Bản ghi đấu thầu lại có sau sự kiện được chọn.",
      specification_change_and_handoff_before_focus:
        "Các bản ghi thay đổi đặc tả và chuyển giao đều có trước sự kiện được chọn.",
    },
  },
};

function shortDate(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.valueOf()) ? value : parsed.toISOString().slice(0, 10);
}

export function TeppProjectHistoryEvidence({
  validation,
  onOpenPost,
  sourceLabels,
}: {
  validation: TeppProjectHistoryValidation;
  onOpenPost: (postId: string) => void;
  sourceLabels: Record<string, string>;
}) {
  const locale = useLocale();
  const copy = COPY[locale];
  const history = validation.project_history;

  if (validation.status !== "validated" || history === null) {
    return (
      <section className="tepp-project-evidence tepp-project-evidence-status" aria-label={copy.heading}>
        <h4>{copy.heading}</h4>
        <p role="status">{copy.status[validation.status]}</p>
      </section>
    );
  }

  return (
    <section className="tepp-project-evidence" aria-labelledby="tepp-project-evidence-heading">
      <header>
        <div>
          <p className="section-eyebrow">{copy.eyebrow}</p>
          <h4 id="tepp-project-evidence-heading">{copy.heading}</h4>
        </div>
        <span className="post-badge">TEPP · v{history.contract_version}</span>
      </header>
      <p className="tepp-project-evidence-boundary">{copy.boundary}</p>
      <dl>
        <div>
          <dt>{copy.participants(history.participant_count)}</dt>
          <dd>{history.participant_count}</dd>
        </div>
        <div>
          <dt>{copy.span}</dt>
          <dd>
            {shortDate(history.history_span_start)} – {shortDate(history.history_span_end)}
          </dd>
        </div>
      </dl>
      <section aria-labelledby="tepp-project-findings-heading">
        <h5 id="tepp-project-findings-heading">{copy.findings}</h5>
        {history.findings.length === 0 ? <p>{copy.noFindings}</p> : null}
        {history.findings.length > 0 ? (
          <ul>
            {history.findings.map((finding) => (
              <li key={`${finding.finding_code}:${finding.related_event_ids.join(":")}`}>
                <p>{copy.findingLabels[finding.finding_code] ?? finding.summary}</p>
                <div className="tepp-project-evidence-links">
                  {finding.evidence_post_ids.map((postId) => {
                    const label = sourceLabels[postId] ?? postId;
                    return (
                      <button
                        key={postId}
                        type="button"
                        aria-label={copy.openEvidence(label)}
                        onClick={() => onOpenPost(postId)}
                      >
                        {copy.openEvidence(label)}
                      </button>
                    );
                  })}
                </div>
              </li>
            ))}
          </ul>
        ) : null}
      </section>
    </section>
  );
}
