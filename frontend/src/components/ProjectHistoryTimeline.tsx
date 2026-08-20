import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import {
  fetchProjectHistory,
  type ProjectEvidence,
  type ProjectHistory,
  type ProjectHistoryEvent,
  type ProjectResponsibilityAssignment,
} from "../api";
import { useLocale, type Locale } from "../i18n";
import "./ProjectHistoryTimeline.css";

type Copy = {
  heading: string;
  helper: string;
  empty: string;
  loading: string;
  unavailable: string;
  currentProject: string;
  chooseProject: string;
  selectedEvent: string;
  evidence: string;
  openEvidence: string;
  relatedHistory: string;
  noRelations: string;
  responsibility: string;
  noAssignments: string;
  handoverGap: string;
  gapDays: string;
  nonCausal: string;
  truncated: string;
  ongoing: string;
};

const COPY: Record<Locale, Copy> = {
  ko: {
    heading: "프로젝트 전 주기 이력",
    helper: "수주부터 현재 이슈까지 확인된 이벤트와 담당 구간을 시간축으로 연결합니다.",
    empty: "이 프로젝트에 공개할 수 있는 이력 근거가 아직 없습니다.",
    loading: "프로젝트 이력을 불러오는 중...",
    unavailable: "프로젝트 이력을 불러오지 못했습니다. 원문과 기존 Event Lineage는 계속 확인할 수 있습니다.",
    currentProject: "현재 프로젝트",
    chooseProject: "프로젝트 선택",
    selectedEvent: "선택 이벤트",
    evidence: "근거",
    openEvidence: "원문 열기",
    relatedHistory: "연관 이력",
    noRelations: "선택 이벤트에 공개할 수 있는 연관 이력이 없습니다.",
    responsibility: "담당 이력",
    noAssignments: "공개할 수 있는 담당 이력이 없습니다.",
    handoverGap: "인수인계 근거 공백",
    gapDays: "일",
    nonCausal: "연관 관계이며 원인으로 판정하지 않습니다.",
    truncated: "표시 한도를 초과한 이력이 있어 전체 내역으로 취급하기 전에 추가 조회가 필요합니다.",
    ongoing: "현재",
  },
  en: {
    heading: "Project lifecycle history",
    helper: "Connect evidence-backed events and responsibility intervals from order to the current issue.",
    empty: "No project-history evidence is visible for this project.",
    loading: "Loading project history...",
    unavailable: "Project history is unavailable. The source record and existing Event Lineage remain available.",
    currentProject: "Current project",
    chooseProject: "Choose project",
    selectedEvent: "Selected event",
    evidence: "Evidence",
    openEvidence: "Open source",
    relatedHistory: "Related history",
    noRelations: "No related history is visible for the selected event.",
    responsibility: "Responsibility history",
    noAssignments: "No responsibility history is visible.",
    handoverGap: "Visible handover-evidence gap",
    gapDays: "days",
    nonCausal: "This is an association, not a causal finding.",
    truncated: "The display limit was reached; load more before treating this as the complete history.",
    ongoing: "Current",
  },
  zh: {
    heading: "项目全周期履历",
    helper: "按时间轴连接从中标到当前问题的已验证事件与负责人区间。",
    empty: "该项目暂无可见的履历证据。",
    loading: "正在加载项目履历...",
    unavailable: "无法加载项目履历。仍可查看原文和现有事件谱系。",
    currentProject: "当前项目",
    chooseProject: "选择项目",
    selectedEvent: "所选事件",
    evidence: "证据",
    openEvidence: "打开原文",
    relatedHistory: "关联履历",
    noRelations: "所选事件暂无可见的关联履历。",
    responsibility: "负责人履历",
    noAssignments: "暂无可见的负责人履历。",
    handoverGap: "可见交接证据空档",
    gapDays: "天",
    nonCausal: "这是关联关系，不表示因果结论。",
    truncated: "已达到显示上限；在视为完整履历前请继续加载。",
    ongoing: "当前",
  },
  ja: {
    heading: "プロジェクト全期間履歴",
    helper: "受注から現在の課題まで、根拠のあるイベントと担当期間を時系列でつなぎます。",
    empty: "このプロジェクトに表示できる履歴根拠はありません。",
    loading: "プロジェクト履歴を読み込んでいます...",
    unavailable: "プロジェクト履歴を読み込めません。原文と既存のイベント系譜は引き続き確認できます。",
    currentProject: "現在のプロジェクト",
    chooseProject: "プロジェクトを選択",
    selectedEvent: "選択したイベント",
    evidence: "根拠",
    openEvidence: "原文を開く",
    relatedHistory: "関連履歴",
    noRelations: "選択したイベントに表示できる関連履歴はありません。",
    responsibility: "担当履歴",
    noAssignments: "表示できる担当履歴はありません。",
    handoverGap: "可視の引き継ぎ根拠空白",
    gapDays: "日",
    nonCausal: "関連であり、因果関係の判定ではありません。",
    truncated: "表示上限に達しました。完全な履歴として扱う前に追加読み込みが必要です。",
    ongoing: "現在",
  },
  vi: {
    heading: "Lịch sử vòng đời dự án",
    helper: "Kết nối các sự kiện và khoảng trách nhiệm có bằng chứng từ lúc trúng thầu đến vấn đề hiện tại.",
    empty: "Chưa có bằng chứng lịch sử dự án nào có thể hiển thị.",
    loading: "Đang tải lịch sử dự án...",
    unavailable: "Không thể tải lịch sử dự án. Bản ghi nguồn và Dòng sự kiện hiện có vẫn khả dụng.",
    currentProject: "Dự án hiện tại",
    chooseProject: "Chọn dự án",
    selectedEvent: "Sự kiện đã chọn",
    evidence: "Bằng chứng",
    openEvidence: "Mở nguồn",
    relatedHistory: "Lịch sử liên quan",
    noRelations: "Không có lịch sử liên quan hiển thị cho sự kiện đã chọn.",
    responsibility: "Lịch sử phụ trách",
    noAssignments: "Không có lịch sử phụ trách hiển thị.",
    handoverGap: "Khoảng trống bằng chứng bàn giao",
    gapDays: "ngày",
    nonCausal: "Đây là liên hệ, không phải kết luận nhân quả.",
    truncated: "Đã đạt giới hạn hiển thị; cần tải thêm trước khi coi đây là lịch sử đầy đủ.",
    ongoing: "Hiện tại",
  },
};

function eventDate(value: string, locale: Locale): string {
  return new Intl.DateTimeFormat(locale, {
    year: "2-digit",
    month: "2-digit",
    day: "2-digit",
    timeZone: "UTC",
  }).format(new Date(value));
}

function timelineBounds(history: ProjectHistory): { start: number; end: number } {
  const fixedValues = [
    ...history.events.flatMap((event) => [
      Date.parse(event.occurred_at),
      Date.parse(event.ended_at ?? event.occurred_at),
    ]),
    ...history.responsibility_assignments.flatMap((assignment) => [
      Date.parse(assignment.valid_from),
      ...(assignment.valid_to ? [Date.parse(assignment.valid_to)] : []),
    ]),
  ].filter(Number.isFinite);
  if (fixedValues.length === 0) return { start: 0, end: 1 };
  const start = Math.min(...fixedValues);
  const end = Math.max(...fixedValues);
  return { start, end: end === start ? start + 1 : end };
}

function intervalStyle(
  assignment: ProjectResponsibilityAssignment,
  start: number,
  end: number,
): CSSProperties {
  const from = Math.max(start, Date.parse(assignment.valid_from));
  const to = Math.min(end, assignment.valid_to ? Date.parse(assignment.valid_to) : end);
  const span = end - start;
  const left = ((from - start) / span) * 100;
  const width = Math.max(2, ((Math.max(from, to) - from) / span) * 100);
  return {
    "--history-left": `${left}%`,
    "--history-width": `${width}%`,
  } as CSSProperties;
}

function defaultEvent(
  history: ProjectHistory,
  currentPostId?: string,
): ProjectHistoryEvent | null {
  return (
    history.events.find((event) => event.evidence_post_id === currentPostId) ??
    history.events.find((event) => event.event_type_code === "project_event_voc") ??
    history.events.at(-1) ??
    null
  );
}

function projectOptions(projectEvidence: ProjectEvidence[]): ProjectEvidence[] {
  const seen = new Set<string>();
  return projectEvidence.filter((project) => {
    const key = project.project_key.trim();
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export function ProjectHistoryPanel({
  accessToken,
  projectEvidence,
  currentPostId,
  onOpenPost,
}: {
  accessToken: string;
  projectEvidence: ProjectEvidence[];
  currentPostId?: string;
  onOpenPost?: (postId: string) => void;
}) {
  const locale = useLocale();
  const copy = COPY[locale];
  const options = useMemo(() => projectOptions(projectEvidence), [projectEvidence]);
  const [selectedKey, setSelectedKey] = useState<string>(options[0]?.project_key ?? "");
  const [history, setHistory] = useState<ProjectHistory | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const requestId = useRef(0);

  useEffect(() => {
    if (options.length === 0) {
      setSelectedKey("");
      return;
    }
    setSelectedKey((current) =>
      options.some((option) => option.project_key === current)
        ? current
        : options[0].project_key,
    );
  }, [options]);

  useEffect(() => {
    if (!selectedKey) {
      setHistory(null);
      setUnavailable(false);
      return;
    }
    const currentRequest = ++requestId.current;
    setHistory(null);
    setUnavailable(false);
    fetchProjectHistory(accessToken, selectedKey)
      .then((payload) => {
        if (requestId.current === currentRequest) setHistory(payload);
      })
      .catch(() => {
        if (requestId.current === currentRequest) setUnavailable(true);
      });
  }, [accessToken, selectedKey]);

  if (options.length === 0) return null;

  return (
    <section className="project-history-panel" aria-label={copy.heading}>
      <label className="project-history-selector">
        <span>{copy.currentProject}</span>
        <select
          aria-label={copy.chooseProject}
          value={selectedKey}
          onChange={(event) => setSelectedKey(event.target.value)}
        >
          {options.map((project) => (
            <option key={project.project_key} value={project.project_key}>
              {project.project_name} · {project.project_key}
            </option>
          ))}
        </select>
      </label>
      {unavailable ? (
        <p className="popup-placeholder" role="status">
          {copy.unavailable}
        </p>
      ) : history === null ? (
        <p role="status">{copy.loading}</p>
      ) : (
        <ProjectHistoryTimeline
          history={history}
          currentPostId={currentPostId}
          onOpenPost={onOpenPost}
        />
      )}
    </section>
  );
}

export function ProjectHistoryTimeline({
  history,
  currentPostId,
  onOpenPost,
}: {
  history: ProjectHistory;
  currentPostId?: string;
  onOpenPost?: (postId: string) => void;
}) {
  const locale = useLocale();
  const copy = COPY[locale];
  const initial = defaultEvent(history, currentPostId);
  const [selectedId, setSelectedId] = useState<string | null>(
    initial?.project_history_event_id ?? null,
  );

  useEffect(() => {
    setSelectedId(defaultEvent(history, currentPostId)?.project_history_event_id ?? null);
  }, [history, currentPostId]);

  const selected =
    history.events.find((event) => event.project_history_event_id === selectedId) ?? null;
  const eventById = useMemo(
    () =>
      new Map(
        history.events.map((event) => [event.project_history_event_id, event]),
      ),
    [history.events],
  );
  const selectedRelations = history.relations.filter(
    (relation) =>
      relation.source_project_history_event_id === selectedId ||
      relation.target_project_history_event_id === selectedId,
  );
  const bounds = timelineBounds(history);

  if (history.events.length === 0) {
    return (
      <section className="project-history" aria-label={copy.heading}>
        <h3>{copy.heading}</h3>
        <p className="popup-placeholder">{copy.empty}</p>
      </section>
    );
  }

  return (
    <section className="project-history" aria-label={copy.heading}>
      <header className="project-history-header">
        <div>
          <p className="section-eyebrow">{history.project_name}</p>
          <h3>{copy.heading}</h3>
          <p>{copy.helper}</p>
        </div>
        <span className="project-history-key">{history.project_key}</span>
      </header>

      <ol
        className="project-history-events"
        aria-label={copy.heading}
        style={
          {
            "--project-history-event-count": history.events.length,
          } as CSSProperties
        }
      >
        {history.events.map((event) => {
          const isSelected =
            event.project_history_event_id === selected?.project_history_event_id;
          return (
            <li key={event.project_history_event_id}>
              <button
                type="button"
                className="project-history-event"
                aria-pressed={isSelected}
                aria-label={`${event.event_type_label}: ${event.event_title}, ${eventDate(
                  event.occurred_at,
                  locale,
                )}, ${copy.evidence} ${event.evidence_count}`}
                onClick={() => setSelectedId(event.project_history_event_id)}
              >
                <time dateTime={event.occurred_at}>
                  {eventDate(event.occurred_at, locale)}
                </time>
                <span className="project-history-dot" aria-hidden="true" />
                <strong>{event.event_type_label}</strong>
                <span>{event.event_title}</span>
              </button>
            </li>
          );
        })}
      </ol>

      <section
        className="project-history-responsibility"
        aria-label={copy.responsibility}
      >
        <h4>{copy.responsibility}</h4>
        {history.responsibility_assignments.length === 0 ? (
          <p className="popup-placeholder">{copy.noAssignments}</p>
        ) : (
          <div className="project-history-assignment-track">
            {history.responsibility_assignments.map((assignment) => {
              const assignmentEnd = assignment.valid_to
                ? eventDate(assignment.valid_to, locale)
                : copy.ongoing;
              return (
                <button
                  type="button"
                  key={assignment.project_responsibility_assignment_id}
                  className="project-history-assignment"
                  style={intervalStyle(assignment, bounds.start, bounds.end)}
                  aria-label={`${assignment.person_name}, ${
                    assignment.responsibility_role_label
                  }, ${eventDate(assignment.valid_from, locale)}–${assignmentEnd}`}
                  onClick={() => onOpenPost?.(assignment.evidence_post_id)}
                >
                  <strong>{assignment.person_name}</strong>
                  <span>{assignment.responsibility_role_label}</span>
                </button>
              );
            })}
            {history.handover_gaps.map((gap) => {
              const left =
                ((Date.parse(gap.gap_start) - bounds.start) /
                  (bounds.end - bounds.start)) *
                100;
              const width = Math.max(
                2,
                ((Date.parse(gap.gap_end) - Date.parse(gap.gap_start)) /
                  (bounds.end - bounds.start)) *
                  100,
              );
              return (
                <span
                  key={`${gap.previous_assignment_id}:${gap.next_assignment_id}`}
                  className="project-history-gap"
                  style={
                    {
                      "--history-left": `${left}%`,
                      "--history-width": `${width}%`,
                    } as CSSProperties
                  }
                  role="note"
                  aria-label={`${copy.handoverGap}: ${gap.gap_days.toFixed(
                    1,
                  )} ${copy.gapDays}`}
                >
                  {copy.handoverGap} · {gap.gap_days.toFixed(0)} {copy.gapDays}
                </span>
              );
            })}
          </div>
        )}
      </section>

      {selected ? (
        <section className="project-history-detail" aria-label={copy.selectedEvent}>
          <p className="section-eyebrow">{copy.selectedEvent}</p>
          <h4>{selected.event_type_label}</h4>
          <p>{selected.event_title}</p>
          <p className="post-meta">
            <time dateTime={selected.occurred_at}>
              {eventDate(selected.occurred_at, locale)}
            </time>
            {" · "}
            {copy.evidence} {selected.evidence_count}
          </p>
          {onOpenPost ? (
            <button
              type="button"
              className="keyman-select"
              aria-label={`${copy.openEvidence}: ${selected.evidence_post_title}`}
              onClick={() => onOpenPost(selected.evidence_post_id)}
            >
              {copy.openEvidence}: {selected.evidence_post_title}
            </button>
          ) : null}

          <h5>{copy.relatedHistory}</h5>
          {selectedRelations.length === 0 ? (
            <p className="popup-placeholder">{copy.noRelations}</p>
          ) : (
            <ul className="project-history-relations">
              {selectedRelations.map((relation) => {
                const otherId =
                  relation.source_project_history_event_id ===
                  selected.project_history_event_id
                    ? relation.target_project_history_event_id
                    : relation.source_project_history_event_id;
                const other = eventById.get(otherId);
                return (
                  <li
                    key={`${relation.source_project_history_event_id}:${relation.target_project_history_event_id}:${relation.relation_type_code}`}
                  >
                    <strong>{relation.relation_type_label}</strong>
                    {" · "}
                    {other?.event_type_label ?? otherId}
                    <span className="post-meta"> — {copy.nonCausal}</span>
                    {onOpenPost ? (
                      <button
                        type="button"
                        className="keyman-select"
                        aria-label={`${copy.evidence}: ${relation.evidence_post_title}`}
                        onClick={() => onOpenPost(relation.evidence_post_id)}
                      >
                        {copy.evidence}: {relation.evidence_post_title}
                      </button>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      ) : null}

      {history.truncated ? (
        <p className="project-history-truncated" role="status">
          {copy.truncated}
        </p>
      ) : null}
    </section>
  );
}
