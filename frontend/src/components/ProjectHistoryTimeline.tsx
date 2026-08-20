import { useEffect, useState, type CSSProperties } from "react";

import {
  fetchPostProjectHistory,
  type TeppProjectHistory,
  type TeppProjectHistoryEnvelope,
} from "../api";
import "./ProjectHistoryTimeline.css";

const EVENT_LABELS: Record<string, string> = {
  contract_awarded: "수주",
  specification_changed: "사양 변경",
  delivered: "납품",
  operational_handoff: "운영 인수",
  voc_received: "VOC 접수",
  rebid_started: "재입찰",
  event_observed: "프로젝트 이벤트",
};

function dateLabel(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  const year = String(date.getUTCFullYear()).slice(-2);
  const month = String(date.getUTCMonth() + 1).padStart(2, "0");
  return `'${year}.${month}`;
}

export function ProjectHistoryTimeline({
  history,
  onOpenPost,
}: {
  history: TeppProjectHistory;
  onOpenPost: (postId: string) => void;
}) {
  const finding = history.findings[0];
  const listStyle = {
    "--tepp-event-count": Math.max(1, history.events.length),
  } as CSSProperties;

  return (
    <section className="tepp-project-history" role="region" aria-label="TEPP project history">
      <div className="tepp-project-history__header">
        <div>
          <p className="section-eyebrow">TEPP 연계 응답</p>
          <h3>프로젝트 이벤트 타임라인</h3>
          <p>{history.project_name}의 명시적 이벤트를 지식 컷오프 안에서 시간순으로 연결합니다.</p>
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
                aria-label={`Open evidence: ${event.event_title}`}
                aria-current={focused ? "step" : undefined}
                onClick={() => onOpenPost(event.source_post_id)}
              >
                <span className="tepp-project-history__dot" aria-hidden="true" />
                <strong>{EVENT_LABELS[event.event_type_code] ?? event.event_type_code}</strong>
                <span>{event.event_title}</span>
              </button>
            </li>
          );
        })}
      </ol>

      <div className="tepp-project-history__detail">
        <h4>이벤트 상세</h4>
        <p>
          현재 이벤트: <strong>{history.events.find((event) => event.event_id === history.focus_event_id)?.event_title}</strong>
          {" · "}담당 이력: {history.participant_count}인
        </p>
        {finding ? (
          <p>
            <strong>TEPP 추론:</strong> {finding.summary}
          </p>
        ) : (
          <p>
            <strong>TEPP 추론:</strong> 명시적 사건을 시간순으로 정렬했습니다. 인과 결론은 생성하지 않습니다.
          </p>
        )}
      </div>

      <p className="tepp-project-history__boundary">
        TEPP는 제공된 증거의 시간적 연관만 설명합니다. 누락된 사건·담당자·인과관계·심리측정 점수는 생성하지 않습니다.
      </p>
    </section>
  );
}

export function PostProjectHistory({
  accessToken,
  postId,
  onOpenPost,
}: {
  accessToken: string;
  postId: string;
  onOpenPost: (postId: string) => void;
}) {
  const [envelope, setEnvelope] = useState<TeppProjectHistoryEnvelope | null>(null);

  useEffect(() => {
    let cancelled = false;
    setEnvelope(null);
    fetchPostProjectHistory(accessToken, postId)
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
  }, [accessToken, postId]);

  if (envelope === null) {
    return <p className="popup-placeholder">TEPP 프로젝트 이력을 불러오는 중입니다.</p>;
  }
  if (!envelope.project_history) {
    return (
      <section className="popup-section tepp-project-history-status" aria-label="TEPP project history status">
        <h3>프로젝트 이벤트 타임라인</h3>
        <p>{envelope.next_action}</p>
      </section>
    );
  }
  return <ProjectHistoryTimeline history={envelope.project_history} onOpenPost={onOpenPost} />;
}
