"""Localize the TEPP project-history Buyer component and status copy."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

COMPONENT = r'''import { useEffect, useState, type CSSProperties } from "react";

import {
  fetchPostProjectHistory,
  type TeppProjectHistory,
  type TeppProjectHistoryEnvelope,
} from "../api";
import { t, tf, useLocale } from "../i18n";
import "./ProjectHistoryTimeline.css";

const EVENT_LABEL_KEYS: Record<string, string> = {
  contract_awarded: "Contract award",
  specification_changed: "Specification change",
  delivered: "Delivery",
  operational_handoff: "Operational handoff",
  voc_received: "VOC received",
  rebid_started: "Rebid",
  event_observed: "Observed project event",
};

function dateLabel(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  const year = String(date.getUTCFullYear()).slice(-2);
  const month = String(date.getUTCMonth() + 1).padStart(2, "0");
  return `'${year}.${month}`;
}

function unavailableMessage(status: string, fallback: string): string {
  if (status === "insufficient_project_evidence") {
    return t("Project history needs an explicit project code and authorized event evidence.");
  }
  if (status === "tepp_unavailable") {
    return t("TEPP project history is unavailable. Configure the service and retry.");
  }
  return fallback;
}

export function ProjectHistoryTimeline({
  history,
  onOpenPost,
}: {
  history: TeppProjectHistory;
  onOpenPost: (postId: string) => void;
}) {
  useLocale();
  const finding = history.findings[0];
  const focusEvent = history.events.find((event) => event.event_id === history.focus_event_id);
  const listStyle = {
    "--tepp-event-count": Math.max(1, history.events.length),
  } as CSSProperties;

  return (
    <section className="tepp-project-history" role="region" aria-label={t("TEPP project history")}>
      <div className="tepp-project-history__header">
        <div>
          <p className="section-eyebrow">{t("TEPP-connected answer")}</p>
          <h3>{t("Project event timeline")}</h3>
          <p>
            {tf("{project} events are connected in time within the knowledge cutoff.", {
              project: history.project_name,
            })}
          </p>
        </div>
        <span className="post-badge">TEPP · v{history.contract_version}</span>
      </div>

      <ol className="tepp-project-history__timeline" style={listStyle}>
        {history.events.map((event) => {
          const focused = event.event_id === history.focus_event_id;
          return (
            <li
              key={event.event_id}
              className={focused ? "tepp-project-history__event is-focus" : "tepp-project-history__event"}
            >
              <time dateTime={event.event_time}>{dateLabel(event.event_time)}</time>
              <button
                type="button"
                aria-label={tf("Open evidence: {title}", { title: event.event_title })}
                aria-current={focused ? "step" : undefined}
                onClick={() => onOpenPost(event.source_post_id)}
              >
                <span className="tepp-project-history__dot" aria-hidden="true" />
                <strong>{t(EVENT_LABEL_KEYS[event.event_type_code] ?? event.event_type_code)}</strong>
                <span>{event.event_title}</span>
              </button>
            </li>
          );
        })}
      </ol>

      <div className="tepp-project-history__detail">
        <h4>{t("Event details")}</h4>
        <p>
          {tf("Current event: {event} · Participant history: {count}", {
            event: focusEvent?.event_title ?? history.focus_event_id,
            count: history.participant_count,
          })}
        </p>
        {finding ? (
          <p>
            <strong>{t("TEPP inference:")}</strong> {finding.summary}
          </p>
        ) : (
          <p>
            <strong>{t("TEPP inference:")}</strong>{" "}
            {t("TEPP ordered explicit events. It does not create a causal conclusion.")}
          </p>
        )}
      </div>

      <p className="tepp-project-history__boundary">
        {t(
          "TEPP explains temporal associations only. It does not create missing events, participants, causal relations, or psychometric scores.",
        )}
      </p>
    </section>
  );
}

export function PostProjectHistory({
  accessToken,
  postId,
  onOpenPost,
  knowledgeCutoff,
}: {
  accessToken: string;
  postId: string;
  onOpenPost: (postId: string) => void;
  knowledgeCutoff?: string | null;
}) {
  useLocale();
  const [envelope, setEnvelope] = useState<TeppProjectHistoryEnvelope | null>(null);

  useEffect(() => {
    let cancelled = false;
    setEnvelope(null);
    fetchPostProjectHistory(accessToken, postId, knowledgeCutoff ?? undefined)
      .then((result) => {
        if (!cancelled) setEnvelope(result);
      })
      .catch(() => {
        if (!cancelled) {
          setEnvelope({
            status: "tepp_unavailable",
            project_history: null,
            next_action: "TEPP project history is unavailable.",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [accessToken, knowledgeCutoff, postId]);

  if (envelope === null) {
    return <p className="popup-placeholder">{t("Loading TEPP project history...")}</p>;
  }
  if (!envelope.project_history) {
    return (
      <section
        className="popup-section tepp-project-history-status"
        aria-label={t("TEPP project history status")}
      >
        <h3>{t("Project event timeline")}</h3>
        <p>{unavailableMessage(envelope.status, envelope.next_action)}</p>
      </section>
    );
  }
  return <ProjectHistoryTimeline history={envelope.project_history} onOpenPost={onOpenPost} />;
}
'''

TRANSLATIONS = {
    "en": {
        "TEPP project history": "TEPP project history",
        "TEPP-connected answer": "TEPP-connected answer",
        "Project event timeline": "Project event timeline",
        "{project} events are connected in time within the knowledge cutoff.": "{project} events are connected in time within the knowledge cutoff.",
        "Contract award": "Contract award",
        "Specification change": "Specification change",
        "Delivery": "Delivery",
        "Operational handoff": "Operational handoff",
        "VOC received": "VOC received",
        "Rebid": "Rebid",
        "Observed project event": "Observed project event",
        "Event details": "Event details",
        "Current event: {event} · Participant history: {count}": "Current event: {event} · Participant history: {count}",
        "TEPP inference:": "TEPP inference:",
        "TEPP ordered explicit events. It does not create a causal conclusion.": "TEPP ordered explicit events. It does not create a causal conclusion.",
        "TEPP explains temporal associations only. It does not create missing events, participants, causal relations, or psychometric scores.": "TEPP explains temporal associations only. It does not create missing events, participants, causal relations, or psychometric scores.",
        "Loading TEPP project history...": "Loading TEPP project history...",
        "TEPP project history status": "TEPP project history status",
        "Project history needs an explicit project code and authorized event evidence.": "Project history needs an explicit project code and authorized event evidence.",
        "TEPP project history is unavailable. Configure the service and retry.": "TEPP project history is unavailable. Configure the service and retry.",
    },
    "ko": {
        "TEPP project history": "TEPP 프로젝트 이력",
        "TEPP-connected answer": "TEPP 연계 응답",
        "Project event timeline": "프로젝트 이벤트 타임라인",
        "{project} events are connected in time within the knowledge cutoff.": "{project}의 명시적 이벤트를 지식 컷오프 안에서 시간순으로 연결합니다.",
        "Contract award": "수주",
        "Specification change": "사양 변경",
        "Delivery": "납품",
        "Operational handoff": "운영 인수",
        "VOC received": "VOC 접수",
        "Rebid": "재입찰",
        "Observed project event": "프로젝트 이벤트",
        "Event details": "이벤트 상세",
        "Current event: {event} · Participant history: {count}": "현재 이벤트: {event} · 담당 이력: {count}인",
        "TEPP inference:": "TEPP 추론:",
        "TEPP ordered explicit events. It does not create a causal conclusion.": "명시적 사건을 시간순으로 정렬했습니다. 인과 결론은 생성하지 않습니다.",
        "TEPP explains temporal associations only. It does not create missing events, participants, causal relations, or psychometric scores.": "TEPP는 제공된 증거의 시간적 연관만 설명합니다. 누락된 사건·담당자·인과관계·심리측정 점수는 생성하지 않습니다.",
        "Loading TEPP project history...": "TEPP 프로젝트 이력을 불러오는 중입니다.",
        "TEPP project history status": "TEPP 프로젝트 이력 상태",
        "Project history needs an explicit project code and authorized event evidence.": "프로젝트 이력에는 명시적 프로젝트 코드와 열람 권한이 있는 이벤트 증거가 필요합니다.",
        "TEPP project history is unavailable. Configure the service and retry.": "TEPP 프로젝트 이력을 사용할 수 없습니다. 서비스를 설정한 뒤 다시 시도하세요.",
    },
    "zh": {
        "TEPP project history": "TEPP 项目历史",
        "TEPP-connected answer": "TEPP 关联回答",
        "Project event timeline": "项目事件时间线",
        "{project} events are connected in time within the knowledge cutoff.": "在知识截止时间内按时间顺序连接 {project} 的明确事件。",
        "Contract award": "中标",
        "Specification change": "规格变更",
        "Delivery": "交付",
        "Operational handoff": "运营移交",
        "VOC received": "收到客户意见",
        "Rebid": "重新投标",
        "Observed project event": "项目事件",
        "Event details": "事件详情",
        "Current event: {event} · Participant history: {count}": "当前事件：{event} · 参与人员：{count}人",
        "TEPP inference:": "TEPP 推断：",
        "TEPP ordered explicit events. It does not create a causal conclusion.": "TEPP 对明确事件进行了排序，不生成因果结论。",
        "TEPP explains temporal associations only. It does not create missing events, participants, causal relations, or psychometric scores.": "TEPP 仅说明时间关联，不生成缺失事件、参与者、因果关系或心理测量分数。",
        "Loading TEPP project history...": "正在加载 TEPP 项目历史…",
        "TEPP project history status": "TEPP 项目历史状态",
        "Project history needs an explicit project code and authorized event evidence.": "项目历史需要明确的项目代码和已授权的事件证据。",
        "TEPP project history is unavailable. Configure the service and retry.": "TEPP 项目历史不可用。请配置服务后重试。",
    },
    "ja": {
        "TEPP project history": "TEPPプロジェクト履歴",
        "TEPP-connected answer": "TEPP連携回答",
        "Project event timeline": "プロジェクトイベントのタイムライン",
        "{project} events are connected in time within the knowledge cutoff.": "知識カットオフ内で {project} の明示的なイベントを時系列に接続します。",
        "Contract award": "受注",
        "Specification change": "仕様変更",
        "Delivery": "納品",
        "Operational handoff": "運用引継ぎ",
        "VOC received": "VOC受付",
        "Rebid": "再入札",
        "Observed project event": "プロジェクトイベント",
        "Event details": "イベント詳細",
        "Current event: {event} · Participant history: {count}": "現在のイベント：{event} · 担当履歴：{count}名",
        "TEPP inference:": "TEPP推論：",
        "TEPP ordered explicit events. It does not create a causal conclusion.": "明示的なイベントを時系列に並べました。因果結論は生成しません。",
        "TEPP explains temporal associations only. It does not create missing events, participants, causal relations, or psychometric scores.": "TEPPは時間的関連のみを説明し、欠落イベント、担当者、因果関係、心理測定スコアを生成しません。",
        "Loading TEPP project history...": "TEPPプロジェクト履歴を読み込んでいます…",
        "TEPP project history status": "TEPPプロジェクト履歴の状態",
        "Project history needs an explicit project code and authorized event evidence.": "プロジェクト履歴には明示的なプロジェクトコードと閲覧権限のあるイベント証拠が必要です。",
        "TEPP project history is unavailable. Configure the service and retry.": "TEPPプロジェクト履歴を利用できません。サービスを設定して再試行してください。",
    },
    "vi": {
        "TEPP project history": "Lịch sử dự án TEPP",
        "TEPP-connected answer": "Câu trả lời liên kết TEPP",
        "Project event timeline": "Dòng thời gian sự kiện dự án",
        "{project} events are connected in time within the knowledge cutoff.": "Các sự kiện rõ ràng của {project} được nối theo thời gian trong giới hạn tri thức.",
        "Contract award": "Trúng thầu",
        "Specification change": "Thay đổi đặc tả",
        "Delivery": "Bàn giao",
        "Operational handoff": "Chuyển giao vận hành",
        "VOC received": "Tiếp nhận VOC",
        "Rebid": "Đấu thầu lại",
        "Observed project event": "Sự kiện dự án",
        "Event details": "Chi tiết sự kiện",
        "Current event: {event} · Participant history: {count}": "Sự kiện hiện tại: {event} · Lịch sử phụ trách: {count} người",
        "TEPP inference:": "Suy luận TEPP:",
        "TEPP ordered explicit events. It does not create a causal conclusion.": "TEPP sắp xếp các sự kiện rõ ràng và không tạo kết luận nhân quả.",
        "TEPP explains temporal associations only. It does not create missing events, participants, causal relations, or psychometric scores.": "TEPP chỉ giải thích liên hệ thời gian; không tạo sự kiện, người tham gia, quan hệ nhân quả hoặc điểm đo lường tâm lý còn thiếu.",
        "Loading TEPP project history...": "Đang tải lịch sử dự án TEPP…",
        "TEPP project history status": "Trạng thái lịch sử dự án TEPP",
        "Project history needs an explicit project code and authorized event evidence.": "Lịch sử dự án cần mã dự án rõ ràng và bằng chứng sự kiện đã được cấp quyền.",
        "TEPP project history is unavailable. Configure the service and retry.": "Lịch sử dự án TEPP hiện không khả dụng. Hãy cấu hình dịch vụ và thử lại.",
    },
}


def patch_i18n() -> None:
    path = ROOT / "frontend/src/i18n.ts"
    text = path.read_text(encoding="utf-8")
    if '"TEPP-connected answer"' in text:
        return
    for locale, translations in TRANSLATIONS.items():
        anchor = f"  {locale}: {{\n"
        if text.count(anchor) != 1:
            raise RuntimeError(f"i18n locale anchor drifted: {locale}")
        lines = "".join(
            f"    {key!r}: {value!r},\n".replace("'", '"')
            for key, value in translations.items()
        )
        text = text.replace(anchor, anchor + lines, 1)
    path.write_text(text, encoding="utf-8")


def patch_test() -> None:
    path = ROOT / "frontend/src/components/ProjectHistoryTimeline.i18n.test.tsx"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        '    expect(screen.getByText("VOC received")).toBeInTheDocument();\n',
        '    expect(screen.getAllByText("VOC received").length).toBeGreaterThan(0);\n',
    )
    path.write_text(text, encoding="utf-8")


def patch_changelog() -> None:
    path = ROOT / "CHANGELOG.d/2.18.0-tepp-project-history-ask.md"
    text = path.read_text(encoding="utf-8")
    line = "- Localizes timeline labels, state messages, and trust-boundary copy in Korean, English, Chinese, Japanese, and Vietnamese.\n"
    if line not in text:
        text += line
        path.write_text(text, encoding="utf-8")


def main() -> None:
    (ROOT / "frontend/src/components/ProjectHistoryTimeline.tsx").write_text(
        COMPONENT, encoding="utf-8"
    )
    patch_i18n()
    patch_test()
    patch_changelog()


if __name__ == "__main__":
    main()
