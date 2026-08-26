import type { ProjectEvidence } from "./api";
import type { Locale } from "./i18n";

export type ProjectHistoryTruthStatus = "observed" | "inferred";
export type ResponsibilityTransitionCode = "continuous" | "handoff" | "assignment_gap";
export type ProjectHistoryTimeBasis = "source_post_created_at_fallback" | "document_time";

export interface ProjectHistoryMatch {
  match_kind_code: string;
  matched_value: string;
  truth_status_code: ProjectHistoryTruthStatus;
  confidence: number | null;
  ontology_iri: string | null;
  provenance: string;
}

export interface ProjectHistoryResponsibility {
  actor_key: string;
  actor_name: string;
  actor_type_code: string;
  affiliated_organization_name: string | null;
  responsibility: string;
  truth_status_code: "observed";
  provenance: string;
}

export interface ProjectHistoryPathEdge {
  parent_event_id: string;
  child_event_id: string;
  fused_score: number;
}

export interface ProjectHistoryPriorPath {
  source_event_id: string;
  target_event_id: string;
  event_ids: string[];
  edges: ProjectHistoryPathEdge[];
  minimum_fused_score: number;
  truth_status_code: "inferred";
  source_relation_code: "post_lineage_edge";
  provenance: "post_lineage_edge.fused_score";
}

export interface ProjectHistoryEvent {
  event_id: string;
  source_post_id: string;
  event_title: string;
  event_type_code: string;
  event_type_basis_code: "controlled_source_code";
  occurred_at: string;
  time_basis_code: ProjectHistoryTimeBasis;
  voc_type_code: string | null;
  source_stage_code: string | null;
  source_detail_state_code: string | null;
  project_matches: ProjectHistoryMatch[];
  observed_responsibilities: ProjectHistoryResponsibility[];
  responsibility_transition_code: ResponsibilityTransitionCode | null;
  related_prior_paths: ProjectHistoryPriorPath[];
}

export interface ProjectHistoryProjection {
  contract_version: 1;
  project_key: string;
  normalized_project_key: string;
  project_name: string;
  focus_event_id: string;
  time_basis_code: ProjectHistoryTimeBasis;
  event_count: number;
  distinct_observed_actor_count: number;
  truncated: boolean;
  events: ProjectHistoryEvent[];
}

function normalizeProjectIdentity(value: string): string {
  return value.normalize("NFKC").trim().toLocaleLowerCase("en-US");
}

/** Return one display key per exact normalized project identity. */
export function projectHistoryKeys(
  evidence: ProjectEvidence[] | undefined,
  sourceProjectCode: string | null | undefined,
  sourceProjectName: string | null | undefined,
): string[] {
  const candidates = evidence?.length
    ? evidence.map((project) => project.project_key)
    : [sourceProjectCode?.trim() ? sourceProjectCode : sourceProjectName ?? ""];
  const seen = new Set<string>();
  return candidates.filter((candidate) => {
    const normalized = normalizeProjectIdentity(candidate);
    if (!normalized || seen.has(normalized)) return false;
    seen.add(normalized);
    return true;
  });
}

const MESSAGE_KEYS = [
  "heading",
  "summaryCounts",
  "documentTime",
  "truncated",
  "eventDetail",
  "eventType",
  "eventDate",
  "timeBasisCode",
  "recordedEventTime",
  "sourceCreationTime",
  "sourceStageCode",
  "sourceDetailStateCode",
  "responsibilityEvidence",
  "noResponsibilityEvidence",
  "continuous",
  "handoff",
  "assignmentGap",
  "priorHistory",
  "noPriorHistory",
  "inferredBoundary",
  "projectEvidence",
  "observed",
  "inferred",
  "openSourceRecord",
  "exactValues",
  "exactTableLabel",
  "columnDate",
  "columnEvent",
  "columnType",
  "columnTransition",
  "columnActors",
  "columnPathScore",
  "notApplicable",
  "contractAwarded",
  "specificationChanged",
  "delivered",
  "handoffRecorded",
  "vocReceived",
  "rebidStarted",
  "sourceRecorded",
] as const;

export const PROJECT_HISTORY_MESSAGE_KEYS = MESSAGE_KEYS;
export type ProjectHistoryMessageKey = (typeof MESSAGE_KEYS)[number];

type MessageParams = Record<string, string | number>;

const EN: Record<ProjectHistoryMessageKey, string> = {
  heading: "Project event timeline",
  summaryCounts: "{events} events · {actors} observed actors",
  documentTime: "Dates use the recorded event time when available and the source creation time otherwise.",
  truncated: "This bounded timeline is truncated. The selected event remains included.",
  eventDetail: "Event detail",
  eventType: "Display event type",
  eventDate: "Event date",
  timeBasisCode: "Time source",
  recordedEventTime: "Recorded event time",
  sourceCreationTime: "Source creation time",
  sourceStageCode: "Source stage code",
  sourceDetailStateCode: "Source detail-state code",
  responsibilityEvidence: "Observed responsibility evidence",
  noResponsibilityEvidence: "No responsibility evidence is recorded for this event.",
  continuous: "Responsibility evidence continued",
  handoff: "Responsibility evidence changed",
  assignmentGap: "Responsibility evidence gap",
  priorHistory: "Related prior history",
  noPriorHistory: "No visible prior lineage path is recorded for this event.",
  inferredBoundary: "This is inferred related history, not causality or an authoritative assignment record.",
  projectEvidence: "Project identity evidence",
  observed: "Observed",
  inferred: "Inferred",
  openSourceRecord: "Open source record: {title}",
  exactValues: "Exact values",
  exactTableLabel: "Project history exact values",
  columnDate: "Date",
  columnEvent: "Event",
  columnType: "Type",
  columnTransition: "Responsibility evidence change",
  columnActors: "Observed actors",
  columnPathScore: "Minimum lineage score",
  notApplicable: "Not applicable",
  contractAwarded: "Contract awarded",
  specificationChanged: "Specification changed",
  delivered: "Delivered",
  handoffRecorded: "Handoff recorded",
  vocReceived: "VOC received",
  rebidStarted: "Rebid started",
  sourceRecorded: "Source record",
};

const MESSAGES: Record<Locale, Record<ProjectHistoryMessageKey, string>> = {
  en: EN,
  ko: {
    heading: "프로젝트 이벤트 타임라인",
    summaryCounts: "이벤트 {events}건 · 관찰된 담당자 {actors}명",
    documentTime: "기록된 사건 시각을 우선 사용하고, 없으면 원천 생성 시각을 사용합니다.",
    truncated: "이 제한된 타임라인은 일부만 표시합니다. 선택한 이벤트는 계속 포함됩니다.",
    eventDetail: "이벤트 상세",
    eventType: "표시용 이벤트 유형",
    eventDate: "이벤트 날짜",
    timeBasisCode: "시간 출처",
    recordedEventTime: "기록된 사건 시각",
    sourceCreationTime: "원천 생성 시각",
    sourceStageCode: "원천 단계 코드",
    sourceDetailStateCode: "원천 세부 상태 코드",
    responsibilityEvidence: "관찰된 담당 근거",
    noResponsibilityEvidence: "이 이벤트에는 기록된 담당 근거가 없습니다.",
    continuous: "담당 근거 유지",
    handoff: "담당 근거 변경",
    assignmentGap: "담당 근거 공백",
    priorHistory: "관련 과거 이력",
    noPriorHistory: "이 이벤트로 이어지는 공개 가능한 이전 계보가 없습니다.",
    inferredBoundary: "이는 추론된 관련 이력이며 인과관계나 권위 있는 인사 배정 기록이 아닙니다.",
    projectEvidence: "프로젝트 식별 근거",
    observed: "관찰됨",
    inferred: "추론됨",
    openSourceRecord: "원천 기록 열기: {title}",
    exactValues: "정확한 값",
    exactTableLabel: "프로젝트 이력 정확한 값",
    columnDate: "날짜",
    columnEvent: "이벤트",
    columnType: "유형",
    columnTransition: "담당 근거 변화",
    columnActors: "관찰된 담당자",
    columnPathScore: "최소 계보 점수",
    notApplicable: "해당 없음",
    contractAwarded: "수주 확정",
    specificationChanged: "사양 변경",
    delivered: "납품",
    handoffRecorded: "인수인계 기록",
    vocReceived: "VOC 접수",
    rebidStarted: "재입찰 시작",
    sourceRecorded: "원천 기록",
  },
  zh: {
    heading: "项目事件时间线",
    summaryCounts: "{events} 个事件 · {actors} 名已观察责任人",
    documentTime: "优先使用已记录的事件时间；若无，则使用来源创建时间。",
    truncated: "此有界时间线已截断，但所选事件仍保留。",
    eventDetail: "事件详情",
    eventType: "显示事件类型",
    eventDate: "事件日期",
    timeBasisCode: "时间来源",
    recordedEventTime: "已记录的事件时间",
    sourceCreationTime: "来源创建时间",
    sourceStageCode: "来源阶段代码",
    sourceDetailStateCode: "来源详细状态代码",
    responsibilityEvidence: "已观察的责任证据",
    noResponsibilityEvidence: "此事件没有记录责任证据。",
    continuous: "责任证据持续",
    handoff: "责任证据变化",
    assignmentGap: "责任证据缺口",
    priorHistory: "相关既往历史",
    noPriorHistory: "此事件没有可见的既往谱系路径。",
    inferredBoundary: "这是推断的相关历史，并非因果关系或权威任命记录。",
    projectEvidence: "项目身份依据",
    observed: "已观察",
    inferred: "已推断",
    openSourceRecord: "打开源记录：{title}",
    exactValues: "精确值",
    exactTableLabel: "项目历史精确值",
    columnDate: "日期",
    columnEvent: "事件",
    columnType: "类型",
    columnTransition: "责任证据变化",
    columnActors: "已观察责任人",
    columnPathScore: "最低谱系分数",
    notApplicable: "不适用",
    contractAwarded: "合同授予",
    specificationChanged: "规格变更",
    delivered: "已交付",
    handoffRecorded: "已记录交接",
    vocReceived: "收到客户之声",
    rebidStarted: "重新投标开始",
    sourceRecorded: "源记录",
  },
  ja: {
    heading: "プロジェクトイベントのタイムライン",
    summaryCounts: "イベント {events}件 · 観察された担当者 {actors}名",
    documentTime: "記録されたイベント時刻を優先し、ない場合は原資料の作成時刻を使います。",
    truncated: "この上限付きタイムラインは省略されていますが、選択イベントは保持されます。",
    eventDetail: "イベント詳細",
    eventType: "表示用イベント種別",
    eventDate: "イベント日",
    timeBasisCode: "時刻の出典",
    recordedEventTime: "記録されたイベント時刻",
    sourceCreationTime: "原資料の作成時刻",
    sourceStageCode: "ソース段階コード",
    sourceDetailStateCode: "ソース詳細状態コード",
    responsibilityEvidence: "観察された担当根拠",
    noResponsibilityEvidence: "このイベントには担当根拠が記録されていません。",
    continuous: "担当根拠が継続",
    handoff: "担当根拠が変更",
    assignmentGap: "担当根拠の空白",
    priorHistory: "関連する過去履歴",
    noPriorHistory: "このイベントに至る可視の過去系譜はありません。",
    inferredBoundary: "これは推論された関連履歴であり、因果関係や権威ある配属記録ではありません。",
    projectEvidence: "プロジェクト識別根拠",
    observed: "観察済み",
    inferred: "推論済み",
    openSourceRecord: "原資料を開く: {title}",
    exactValues: "正確な値",
    exactTableLabel: "プロジェクト履歴の正確な値",
    columnDate: "日付",
    columnEvent: "イベント",
    columnType: "種別",
    columnTransition: "担当根拠の変化",
    columnActors: "観察担当者",
    columnPathScore: "最小系譜スコア",
    notApplicable: "該当なし",
    contractAwarded: "受注確定",
    specificationChanged: "仕様変更",
    delivered: "納品",
    handoffRecorded: "引継ぎ記録",
    vocReceived: "VOC受付",
    rebidStarted: "再入札開始",
    sourceRecorded: "原資料",
  },
  vi: {
    heading: "Dòng thời gian sự kiện dự án",
    summaryCounts: "{events} sự kiện · {actors} người phụ trách được quan sát",
    documentTime: "Ưu tiên thời gian sự kiện đã ghi; nếu thiếu thì dùng thời gian tạo nguồn.",
    truncated: "Dòng thời gian có giới hạn này đã bị rút gọn nhưng vẫn giữ sự kiện đang chọn.",
    eventDetail: "Chi tiết sự kiện",
    eventType: "Loại sự kiện hiển thị",
    eventDate: "Ngày sự kiện",
    timeBasisCode: "Nguồn thời gian",
    recordedEventTime: "Thời gian sự kiện đã ghi",
    sourceCreationTime: "Thời gian tạo nguồn",
    sourceStageCode: "Mã giai đoạn nguồn",
    sourceDetailStateCode: "Mã trạng thái chi tiết nguồn",
    responsibilityEvidence: "Bằng chứng trách nhiệm quan sát được",
    noResponsibilityEvidence: "Không có bằng chứng trách nhiệm được ghi cho sự kiện này.",
    continuous: "Bằng chứng trách nhiệm tiếp tục",
    handoff: "Bằng chứng trách nhiệm thay đổi",
    assignmentGap: "Khoảng trống bằng chứng trách nhiệm",
    priorHistory: "Lịch sử trước đó có liên quan",
    noPriorHistory: "Không có đường dẫn lịch sử trước đó khả kiến cho sự kiện này.",
    inferredBoundary: "Đây là lịch sử liên quan được suy luận, không phải quan hệ nhân quả hay hồ sơ phân công có thẩm quyền.",
    projectEvidence: "Bằng chứng nhận dạng dự án",
    observed: "Đã quan sát",
    inferred: "Đã suy luận",
    openSourceRecord: "Mở bản ghi nguồn: {title}",
    exactValues: "Giá trị chính xác",
    exactTableLabel: "Giá trị chính xác của lịch sử dự án",
    columnDate: "Ngày",
    columnEvent: "Sự kiện",
    columnType: "Loại",
    columnTransition: "Thay đổi bằng chứng trách nhiệm",
    columnActors: "Người phụ trách được quan sát",
    columnPathScore: "Điểm dòng dõi tối thiểu",
    notApplicable: "Không áp dụng",
    contractAwarded: "Đã trao hợp đồng",
    specificationChanged: "Đã thay đổi đặc tả",
    delivered: "Đã bàn giao sản phẩm",
    handoffRecorded: "Đã ghi nhận bàn giao",
    vocReceived: "Đã nhận ý kiến khách hàng",
    rebidStarted: "Đã bắt đầu đấu thầu lại",
    sourceRecorded: "Bản ghi nguồn",
  },
};

export function projectHistoryText(
  locale: Locale,
  key: ProjectHistoryMessageKey,
  params: MessageParams = {},
): string {
  let value = MESSAGES[locale][key];
  for (const [name, replacement] of Object.entries(params)) {
    value = value.replaceAll(`{${name}}`, String(replacement));
  }
  return value;
}

export function projectHistoryEventTypeLabel(locale: Locale, code: string): string {
  const keyByCode: Record<string, ProjectHistoryMessageKey> = {
    contract_awarded: "contractAwarded",
    specification_changed: "specificationChanged",
    delivered: "delivered",
    handoff_recorded: "handoffRecorded",
    voc_received: "vocReceived",
    rebid_started: "rebidStarted",
    source_recorded: "sourceRecorded",
  };
  const key = keyByCode[code];
  return key ? projectHistoryText(locale, key) : code;
}

export function projectHistoryTransitionLabel(
  locale: Locale,
  code: ResponsibilityTransitionCode | null,
): string {
  if (code === "continuous") return projectHistoryText(locale, "continuous");
  if (code === "handoff") return projectHistoryText(locale, "handoff");
  if (code === "assignment_gap") return projectHistoryText(locale, "assignmentGap");
  return projectHistoryText(locale, "notApplicable");
}
