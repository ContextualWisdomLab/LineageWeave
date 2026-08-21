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
  truth_status_code: ProjectHistoryTruthStatus;
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
  event_type_basis_code: "display_classification";
  occurred_at: string;
  time_basis_code: ProjectHistoryTimeBasis;
  voc_type_code: string | null;
  source_stage_code: string | null;
  source_detail_state_code: string | null;
  project_matches: ProjectHistoryMatch[];
  responsibility_evidence?: ProjectHistoryResponsibility[];
  observed_responsibilities: ProjectHistoryResponsibility[];
  responsibility_transition_code: ResponsibilityTransitionCode | null;
  responsibility_transition_truth_status_code?: ProjectHistoryTruthStatus | null;
  related_prior_paths: ProjectHistoryPriorPath[];
}

export interface ProjectHistoryProjection {
  contract_version: 1;
  project_key: string;
  normalized_project_key: string;
  project_name: string;
  focus_event_id: string;
  time_basis_code: ProjectHistoryTimeBasis;
  knowledge_cutoff?: string;
  evidence_boundary_code?: "authorized_visible_source_posts" | string;
  event_count: number;
  distinct_actor_count?: number;
  distinct_observed_actor_count: number;
  truncated: boolean;
  events: ProjectHistoryEvent[];
}

export interface ProjectHistoryIndexEntry {
  normalized_project_key: string;
  project_key: string;
  project_name: string;
  truth_status_code: ProjectHistoryTruthStatus;
  event_count: number;
  latest_event_at: string;
}

export interface ProjectHistoryIndex {
  contract_version: 1;
  time_basis_code: ProjectHistoryTimeBasis;
  knowledge_cutoff: string;
  project_count: number;
  truncated: boolean;
  projects: ProjectHistoryIndexEntry[];
}

export interface ProjectEvidenceGroup {
  normalizedProjectKey: string;
  projectKey: string;
  projectName: string;
  evidence: ProjectEvidence[];
}

function normalizeProjectIdentity(value: string): string {
  return value.normalize("NFKC").trim().toLocaleLowerCase("en-US");
}

function evidenceOrder(evidence: ProjectEvidence): number {
  if (evidence.extraction_method === "source_field_hint") return 0;
  if (evidence.resolution_status === "hint_only") return 1;
  return 2;
}

function compareEvidence(left: ProjectEvidence, right: ProjectEvidence): number {
  return (
    evidenceOrder(left) - evidenceOrder(right) ||
    left.project_name.localeCompare(right.project_name) ||
    left.project_key.localeCompare(right.project_key) ||
    left.provenance.localeCompare(right.provenance)
  );
}

export function groupProjectEvidence(evidence: ProjectEvidence[]): ProjectEvidenceGroup[] {
  const groups = new Map<string, ProjectEvidence[]>();
  for (const item of evidence) {
    const normalizedProjectKey = normalizeProjectIdentity(item.project_key || item.project_name);
    if (!normalizedProjectKey) continue;
    const rows = groups.get(normalizedProjectKey) ?? [];
    rows.push(item);
    groups.set(normalizedProjectKey, rows);
  }
  return Array.from(groups.entries())
    .map(([normalizedProjectKey, rows]) => {
      const ordered = [...rows].sort(compareEvidence);
      const representative = ordered[0];
      return {
        normalizedProjectKey,
        projectKey: representative.project_key || representative.project_name,
        projectName: representative.project_name || representative.project_key,
        evidence: ordered,
      };
    })
    .sort(
      (left, right) =>
        left.projectName.localeCompare(right.projectName) ||
        left.normalizedProjectKey.localeCompare(right.normalizedProjectKey),
    );
}

const MESSAGE_KEYS = [
  "destinationHeading",
  "destinationIntro",
  "selectProject",
  "loadingProjects",
  "noProjects",
  "loadingHistory",
  "historyUnavailable",
  "projectListTruncated",
  "openProject",
  "evidenceBoundary",
  "heading",
  "summaryCounts",
  "sourcePostTime",
  "documentTime",
  "truncated",
  "eventDetail",
  "eventType",
  "eventDate",
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
  destinationHeading: "Project lifecycle history",
  destinationIntro: "Read the authorized order, change, delivery, VOC, and rebid evidence on one timeline.",
  selectProject: "Select project",
  loadingProjects: "Loading authorized projects...",
  noProjects: "No project evidence is available in your authorized scope.",
  loadingHistory: "Loading project history...",
  historyUnavailable: "Project history could not be loaded. Open a source record and check its project evidence.",
  projectListTruncated: "Only the most recent projects within the display bound are shown.",
  openProject: "Open project: {name}",
  evidenceBoundary: "Only source posts that pass the current permission, visibility, publication, and cutoff gates are included.",
  heading: "Project event timeline",
  summaryCounts: "{events} events · {actors} actors in evidence",
  sourcePostTime: "Dates use source-post creation time because a separate event clock is not recorded.",
  documentTime: "Dates use the recorded document time.",
  truncated: "This bounded timeline is truncated. The selected event remains included.",
  eventDetail: "Event detail",
  eventType: "Display event type",
  eventDate: "Source-post date",
  responsibilityEvidence: "Responsibility evidence",
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
  columnActors: "Actors in evidence",
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
    destinationHeading: "프로젝트 전 주기 이력",
    destinationIntro: "권한 범위의 수주·변경·납품·VOC·재입찰 근거를 하나의 시간축에서 확인합니다.",
    selectProject: "프로젝트 선택",
    loadingProjects: "열람 가능한 프로젝트를 불러오는 중...",
    noProjects: "현재 권한 범위에는 프로젝트 근거가 없습니다.",
    loadingHistory: "프로젝트 이력을 불러오는 중...",
    historyUnavailable: "프로젝트 이력을 불러오지 못했습니다. 원천 기록을 열어 프로젝트 근거를 확인하세요.",
    projectListTruncated: "표시 한도 안의 최근 프로젝트만 보여 줍니다.",
    openProject: "프로젝트 열기: {name}",
    evidenceBoundary: "현재 권한·공개 범위·게시 상태·기준 시각을 통과한 원천 게시물만 포함합니다.",
    heading: "프로젝트 이벤트 타임라인",
    summaryCounts: "이벤트 {events}건 · 근거에 등장한 담당자 {actors}명",
    sourcePostTime: "별도 사건 시각이 없어 날짜는 원천 게시물 생성 시각을 사용합니다.",
    documentTime: "날짜는 기록된 문서 시각을 사용합니다.",
    truncated: "이 제한된 타임라인은 일부만 표시합니다. 선택한 이벤트는 계속 포함됩니다.",
    eventDetail: "이벤트 상세",
    eventType: "표시용 이벤트 유형",
    eventDate: "원천 게시물 날짜",
    responsibilityEvidence: "담당 근거",
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
    columnActors: "근거에 등장한 담당자",
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
    destinationHeading: "项目全周期历史",
    destinationIntro: "在一条时间线上查看权限范围内的订单、变更、交付、客户之声和重新投标依据。",
    selectProject: "选择项目",
    loadingProjects: "正在加载可访问项目...",
    noProjects: "当前授权范围内没有项目依据。",
    loadingHistory: "正在加载项目历史...",
    historyUnavailable: "无法加载项目历史。请打开源记录并检查项目依据。",
    projectListTruncated: "仅显示边界内最近的项目。",
    openProject: "打开项目：{name}",
    evidenceBoundary: "仅包含通过当前权限、可见性、发布状态和截止时间检查的源帖子。",
    heading: "项目事件时间线",
    summaryCounts: "{events} 个事件 · 依据中出现 {actors} 名责任人",
    sourcePostTime: "未记录独立事件时钟，因此日期采用源帖子创建时间。",
    documentTime: "日期采用记录的文档时间。",
    truncated: "此有界时间线已截断，但所选事件仍保留。",
    eventDetail: "事件详情",
    eventType: "显示事件类型",
    eventDate: "源帖子日期",
    responsibilityEvidence: "责任依据",
    noResponsibilityEvidence: "此事件没有记录责任依据。",
    continuous: "责任依据持续",
    handoff: "责任依据变化",
    assignmentGap: "责任依据缺口",
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
    columnTransition: "责任依据变化",
    columnActors: "依据中的责任人",
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
    destinationHeading: "プロジェクト全期間履歴",
    destinationIntro: "権限範囲内の受注・変更・納品・VOC・再入札の根拠を一つの時間軸で確認します。",
    selectProject: "プロジェクトを選択",
    loadingProjects: "閲覧可能なプロジェクトを読み込み中...",
    noProjects: "現在の権限範囲にはプロジェクト根拠がありません。",
    loadingHistory: "プロジェクト履歴を読み込み中...",
    historyUnavailable: "プロジェクト履歴を読み込めませんでした。原資料を開いてプロジェクト根拠を確認してください。",
    projectListTruncated: "表示上限内の最近のプロジェクトのみを表示します。",
    openProject: "プロジェクトを開く: {name}",
    evidenceBoundary: "現在の権限・可視性・公開状態・基準時刻を通過した原資料だけを含みます。",
    heading: "プロジェクトイベントのタイムライン",
    summaryCounts: "イベント {events}件 · 根拠内の担当者 {actors}名",
    sourcePostTime: "独立したイベント時刻がないため、原資料の作成時刻を使用します。",
    documentTime: "日付は記録された文書時刻を使用します。",
    truncated: "この上限付きタイムラインは省略されていますが、選択イベントは保持されます。",
    eventDetail: "イベント詳細",
    eventType: "表示用イベント種別",
    eventDate: "原資料の日付",
    responsibilityEvidence: "担当根拠",
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
    columnActors: "根拠内の担当者",
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
    destinationHeading: "Lịch sử toàn vòng đời dự án",
    destinationIntro: "Xem bằng chứng đơn hàng, thay đổi, giao hàng, VOC và đấu thầu lại được phép trên một dòng thời gian.",
    selectProject: "Chọn dự án",
    loadingProjects: "Đang tải các dự án được phép...",
    noProjects: "Không có bằng chứng dự án trong phạm vi được phép hiện tại.",
    loadingHistory: "Đang tải lịch sử dự án...",
    historyUnavailable: "Không thể tải lịch sử dự án. Hãy mở bản ghi nguồn và kiểm tra bằng chứng dự án.",
    projectListTruncated: "Chỉ hiển thị các dự án gần đây trong giới hạn trình bày.",
    openProject: "Mở dự án: {name}",
    evidenceBoundary: "Chỉ bao gồm bài nguồn vượt qua quyền, khả năng hiển thị, trạng thái xuất bản và mốc thời gian hiện tại.",
    heading: "Dòng thời gian sự kiện dự án",
    summaryCounts: "{events} sự kiện · {actors} người xuất hiện trong bằng chứng",
    sourcePostTime: "Không có đồng hồ sự kiện riêng, nên dùng thời gian tạo bài nguồn.",
    documentTime: "Ngày sử dụng thời gian tài liệu được ghi nhận.",
    truncated: "Dòng thời gian có giới hạn này đã bị rút gọn nhưng vẫn giữ sự kiện đang chọn.",
    eventDetail: "Chi tiết sự kiện",
    eventType: "Loại sự kiện hiển thị",
    eventDate: "Ngày bài nguồn",
    responsibilityEvidence: "Bằng chứng trách nhiệm",
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
    columnActors: "Người trong bằng chứng",
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
