import { getLocale, type Locale } from "./i18n";

const ENGLISH_ANALYSIS_RUN_COPY = {
  pendingLineage:
    "Open this run, then start reconstruction. Reconstruction has not started yet.",
  pendingMeasurement:
    "Open this run to confirm which posts will be measured. Measurement has not started yet — this is not a calibrated result.",
  pendingTopicLineage:
    "Open this run to confirm which posts will form the topic lineage. Analysis has not started yet — this is not a calibrated topic result.",
  pendingReport:
    "Open this run to confirm which posts the period report will use. The report has not been built yet.",
  failedMeasurement:
    "Open this run to see why it failed. Ask an administrator to restore measurement, then run it again.",
  failedTopicLineage:
    "Open this run to see why it failed. Ask an administrator to restore topic-lineage analysis, then run it again.",
  failedLineage:
    "Open this run to see why it failed, then retry reconstruction from a current snapshot.",
  failedReport:
    "Open this run to see why it failed, then rebuild the period report from a current snapshot.",
  running: "This run is in progress. Refresh it to check for results.",
  cancelledLineage:
    "This run was cancelled. Request a new lineage reconstruction from a current snapshot.",
  cancelledMeasurement:
    "This run was cancelled. Ask an administrator to restore measurement and submit a new run from a current snapshot.",
  cancelledTopicLineage:
    "This run was cancelled. Ask an administrator to restore topic-lineage analysis and submit a new run from a current snapshot.",
  cancelledReport:
    "This run was cancelled. Rebuild the period report from a current snapshot.",
  emptyMeasurement:
    "No posts were available at this snapshot for measurement. Open a later run, or ask an administrator to capture a newer snapshot.",
  emptyTopicLineage:
    "No posts were available at this snapshot for topic-lineage analysis. Open a later run, or ask an administrator to capture a newer snapshot.",
  emptyLineage:
    "No posts were available at this snapshot for reconstruction. Open a later run, or ask an administrator to capture a newer snapshot.",
  emptyReport:
    "No posts were available at this snapshot for the period report. Open a later run, or ask an administrator to capture a newer snapshot.",
  corpusFailedMeasurement:
    "These posts were selected for measurement at this snapshot. Ask an administrator to restore measurement, then run it again.",
  corpusSucceededMeasurement: "These posts were measured in this run.",
  corpusPendingMeasurement: "These posts will be measured when this run finishes.",
  corpusCancelledMeasurement:
    "These posts would have been measured. The run was cancelled before a calibrated result was created.",
  corpusAttachedMeasurement: "These posts are attached to this measurement run.",
  corpusFailedTopicLineage:
    "These posts were selected for topic-lineage analysis at this snapshot. Ask an administrator to restore analysis, then run it again.",
  corpusSucceededTopicLineage: "These posts formed the topic lineage in this run.",
  corpusPendingTopicLineage:
    "These posts will form the topic lineage when this run finishes.",
  corpusCancelledTopicLineage:
    "These posts would have formed the topic lineage. The run was cancelled before a calibrated topic result was created.",
  corpusAttachedTopicLineage: "These posts are attached to this topic-lineage run.",
} as const;

export type AnalysisRunCopyKey = keyof typeof ENGLISH_ANALYSIS_RUN_COPY;

const ANALYSIS_RUN_COPY: Record<
  Locale,
  Record<AnalysisRunCopyKey, string>
> = {
  en: ENGLISH_ANALYSIS_RUN_COPY,
  ko: {
    pendingLineage: "이 실행을 연 다음 계보 재구성을 시작하세요. 재구성은 아직 시작되지 않았습니다.",
    pendingMeasurement: "이 실행을 열어 측정할 글을 확인하세요. 측정은 아직 시작되지 않았으며, 보정된 결과가 아닙니다.",
    pendingTopicLineage: "이 실행을 열어 토픽 계보를 구성할 글을 확인하세요. 분석은 아직 시작되지 않았으며, 보정된 토픽 결과가 아닙니다.",
    pendingReport: "이 실행을 열어 기간 보고서에 사용할 글을 확인하세요. 보고서는 아직 생성되지 않았습니다.",
    failedMeasurement: "이 실행을 열어 실패 이유를 확인하세요. 관리자에게 측정 복구를 요청한 다음 다시 실행하세요.",
    failedTopicLineage: "이 실행을 열어 실패 이유를 확인하세요. 관리자에게 토픽 계보 분석 복구를 요청한 다음 다시 실행하세요.",
    failedLineage: "이 실행을 열어 실패 이유를 확인한 다음 현재 스냅샷에서 재구성을 다시 시도하세요.",
    failedReport: "이 실행을 열어 실패 이유를 확인한 다음 현재 스냅샷에서 기간 보고서를 다시 생성하세요.",
    running: "이 실행은 진행 중입니다. 결과를 확인하려면 새로 고치세요.",
    cancelledLineage: "이 실행은 취소되었습니다. 현재 스냅샷에서 새 계보 재구성을 요청하세요.",
    cancelledMeasurement: "이 실행은 취소되었습니다. 관리자에게 측정 복구를 요청하고 현재 스냅샷에서 새 실행을 제출하세요.",
    cancelledTopicLineage: "이 실행은 취소되었습니다. 관리자에게 토픽 계보 분석 복구를 요청하고 현재 스냅샷에서 새 실행을 제출하세요.",
    cancelledReport: "이 실행은 취소되었습니다. 현재 스냅샷에서 기간 보고서를 다시 생성하세요.",
    emptyMeasurement: "이 스냅샷에는 측정할 글이 없습니다. 이후 실행을 열거나 관리자에게 최신 스냅샷 생성을 요청하세요.",
    emptyTopicLineage: "이 스냅샷에는 토픽 계보를 분석할 글이 없습니다. 이후 실행을 열거나 관리자에게 최신 스냅샷 생성을 요청하세요.",
    emptyLineage: "이 스냅샷에는 재구성할 글이 없습니다. 이후 실행을 열거나 관리자에게 최신 스냅샷 생성을 요청하세요.",
    emptyReport: "이 스냅샷에는 기간 보고서에 사용할 글이 없습니다. 이후 실행을 열거나 관리자에게 최신 스냅샷 생성을 요청하세요.",
    corpusFailedMeasurement: "이 글들은 이 스냅샷에서 측정 대상으로 선택되었습니다. 관리자에게 측정 복구를 요청한 다음 다시 실행하세요.",
    corpusSucceededMeasurement: "이 실행에서 이 글들을 측정했습니다.",
    corpusPendingMeasurement: "이 실행이 끝나면 이 글들을 측정합니다.",
    corpusCancelledMeasurement: "이 글들은 측정될 예정이었습니다. 보정된 결과가 생성되기 전에 실행이 취소되었습니다.",
    corpusAttachedMeasurement: "이 글들은 이 측정 실행에 연결되어 있습니다.",
    corpusFailedTopicLineage: "이 글들은 이 스냅샷에서 토픽 계보 분석 대상으로 선택되었습니다. 관리자에게 분석 복구를 요청한 다음 다시 실행하세요.",
    corpusSucceededTopicLineage: "이 실행에서 이 글들이 토픽 계보를 구성했습니다.",
    corpusPendingTopicLineage: "이 실행이 끝나면 이 글들이 토픽 계보를 구성합니다.",
    corpusCancelledTopicLineage: "이 글들은 토픽 계보를 구성할 예정이었습니다. 보정된 토픽 결과가 생성되기 전에 실행이 취소되었습니다.",
    corpusAttachedTopicLineage: "이 글들은 이 토픽 계보 실행에 연결되어 있습니다.",
  },
  zh: {
    pendingLineage: "打开此运行，然后开始重建。重建尚未开始。",
    pendingMeasurement: "打开此运行以确认要测量的文章。测量尚未开始，这不是校准结果。",
    pendingTopicLineage: "打开此运行以确认将构成主题谱系的文章。分析尚未开始，这不是校准后的主题结果。",
    pendingReport: "打开此运行以确认周期报告将使用的文章。报告尚未生成。",
    failedMeasurement: "打开此运行查看失败原因。请管理员恢复测量，然后重新运行。",
    failedTopicLineage: "打开此运行查看失败原因。请管理员恢复主题谱系分析，然后重新运行。",
    failedLineage: "打开此运行查看失败原因，然后从当前快照重试重建。",
    failedReport: "打开此运行查看失败原因，然后从当前快照重新生成周期报告。",
    running: "此运行正在进行。请刷新以查看结果。",
    cancelledLineage: "此运行已取消。请从当前快照请求新的谱系重建。",
    cancelledMeasurement: "此运行已取消。请管理员恢复测量，并从当前快照提交新的运行。",
    cancelledTopicLineage: "此运行已取消。请管理员恢复主题谱系分析，并从当前快照提交新的运行。",
    cancelledReport: "此运行已取消。请从当前快照重新生成周期报告。",
    emptyMeasurement: "此快照中没有可测量的文章。请打开较晚的运行，或请管理员创建更新的快照。",
    emptyTopicLineage: "此快照中没有可用于主题谱系分析的文章。请打开较晚的运行，或请管理员创建更新的快照。",
    emptyLineage: "此快照中没有可重建的文章。请打开较晚的运行，或请管理员创建更新的快照。",
    emptyReport: "此快照中没有可用于周期报告的文章。请打开较晚的运行，或请管理员创建更新的快照。",
    corpusFailedMeasurement: "这些文章已在此快照中选为测量对象。请管理员恢复测量，然后重新运行。",
    corpusSucceededMeasurement: "这些文章已在此运行中完成测量。",
    corpusPendingMeasurement: "此运行完成后将测量这些文章。",
    corpusCancelledMeasurement: "这些文章原本将被测量。运行在生成校准结果前已取消。",
    corpusAttachedMeasurement: "这些文章已附加到此测量运行。",
    corpusFailedTopicLineage: "这些文章已在此快照中选为主题谱系分析对象。请管理员恢复分析，然后重新运行。",
    corpusSucceededTopicLineage: "这些文章在此运行中构成了主题谱系。",
    corpusPendingTopicLineage: "此运行完成后，这些文章将构成主题谱系。",
    corpusCancelledTopicLineage: "这些文章原本将构成主题谱系。运行在生成校准后的主题结果前已取消。",
    corpusAttachedTopicLineage: "这些文章已附加到此主题谱系运行。",
  },
  ja: {
    pendingLineage: "この実行を開いてから系譜の再構成を開始してください。再構成はまだ始まっていません。",
    pendingMeasurement: "この実行を開いて測定する投稿を確認してください。測定はまだ始まっておらず、校正済みの結果ではありません。",
    pendingTopicLineage: "この実行を開いてトピック系譜を構成する投稿を確認してください。分析はまだ始まっておらず、校正済みのトピック結果ではありません。",
    pendingReport: "この実行を開いて期間レポートに使用する投稿を確認してください。レポートはまだ作成されていません。",
    failedMeasurement: "この実行を開いて失敗理由を確認してください。管理者に測定の復旧を依頼してから再実行してください。",
    failedTopicLineage: "この実行を開いて失敗理由を確認してください。管理者にトピック系譜分析の復旧を依頼してから再実行してください。",
    failedLineage: "この実行を開いて失敗理由を確認し、現在のスナップショットから再構成を再試行してください。",
    failedReport: "この実行を開いて失敗理由を確認し、現在のスナップショットから期間レポートを再作成してください。",
    running: "この実行は進行中です。結果を確認するには更新してください。",
    cancelledLineage: "この実行はキャンセルされました。現在のスナップショットから新しい系譜再構成を依頼してください。",
    cancelledMeasurement: "この実行はキャンセルされました。管理者に測定の復旧を依頼し、現在のスナップショットから新しい実行を送信してください。",
    cancelledTopicLineage: "この実行はキャンセルされました。管理者にトピック系譜分析の復旧を依頼し、現在のスナップショットから新しい実行を送信してください。",
    cancelledReport: "この実行はキャンセルされました。現在のスナップショットから期間レポートを再作成してください。",
    emptyMeasurement: "このスナップショットには測定できる投稿がありません。後の実行を開くか、管理者に新しいスナップショットの作成を依頼してください。",
    emptyTopicLineage: "このスナップショットにはトピック系譜を分析できる投稿がありません。後の実行を開くか、管理者に新しいスナップショットの作成を依頼してください。",
    emptyLineage: "このスナップショットには再構成できる投稿がありません。後の実行を開くか、管理者に新しいスナップショットの作成を依頼してください。",
    emptyReport: "このスナップショットには期間レポートで使用できる投稿がありません。後の実行を開くか、管理者に新しいスナップショットの作成を依頼してください。",
    corpusFailedMeasurement: "これらの投稿は、このスナップショットで測定対象に選ばれました。管理者に測定の復旧を依頼してから再実行してください。",
    corpusSucceededMeasurement: "これらの投稿はこの実行で測定されました。",
    corpusPendingMeasurement: "この実行が完了すると、これらの投稿が測定されます。",
    corpusCancelledMeasurement: "これらの投稿は測定される予定でした。校正済みの結果が作成される前に実行がキャンセルされました。",
    corpusAttachedMeasurement: "これらの投稿はこの測定実行に関連付けられています。",
    corpusFailedTopicLineage: "これらの投稿は、このスナップショットでトピック系譜分析の対象に選ばれました。管理者に分析の復旧を依頼してから再実行してください。",
    corpusSucceededTopicLineage: "これらの投稿はこの実行でトピック系譜を構成しました。",
    corpusPendingTopicLineage: "この実行が完了すると、これらの投稿がトピック系譜を構成します。",
    corpusCancelledTopicLineage: "これらの投稿はトピック系譜を構成する予定でした。校正済みのトピック結果が作成される前に実行がキャンセルされました。",
    corpusAttachedTopicLineage: "これらの投稿はこのトピック系譜実行に関連付けられています。",
  },
  vi: {
    pendingLineage: "Mở lượt chạy này rồi bắt đầu tái dựng phả hệ. Việc tái dựng chưa bắt đầu.",
    pendingMeasurement: "Mở lượt chạy này để xác nhận các bài viết sẽ được đo. Việc đo chưa bắt đầu và đây chưa phải là kết quả đã hiệu chuẩn.",
    pendingTopicLineage: "Mở lượt chạy này để xác nhận các bài viết sẽ tạo thành phả hệ chủ đề. Phân tích chưa bắt đầu và đây chưa phải là kết quả chủ đề đã hiệu chuẩn.",
    pendingReport: "Mở lượt chạy này để xác nhận các bài viết mà báo cáo kỳ sẽ sử dụng. Báo cáo chưa được tạo.",
    failedMeasurement: "Mở lượt chạy này để xem lý do thất bại. Hãy yêu cầu quản trị viên khôi phục việc đo rồi chạy lại.",
    failedTopicLineage: "Mở lượt chạy này để xem lý do thất bại. Hãy yêu cầu quản trị viên khôi phục phân tích phả hệ chủ đề rồi chạy lại.",
    failedLineage: "Mở lượt chạy này để xem lý do thất bại, rồi thử tái dựng lại từ ảnh chụp hiện tại.",
    failedReport: "Mở lượt chạy này để xem lý do thất bại, rồi tạo lại báo cáo kỳ từ ảnh chụp hiện tại.",
    running: "Lượt chạy này đang thực hiện. Hãy làm mới để kiểm tra kết quả.",
    cancelledLineage: "Lượt chạy này đã bị hủy. Hãy yêu cầu tái dựng phả hệ mới từ ảnh chụp hiện tại.",
    cancelledMeasurement: "Lượt chạy này đã bị hủy. Hãy yêu cầu quản trị viên khôi phục việc đo và gửi lượt chạy mới từ ảnh chụp hiện tại.",
    cancelledTopicLineage: "Lượt chạy này đã bị hủy. Hãy yêu cầu quản trị viên khôi phục phân tích phả hệ chủ đề và gửi lượt chạy mới từ ảnh chụp hiện tại.",
    cancelledReport: "Lượt chạy này đã bị hủy. Hãy tạo lại báo cáo kỳ từ ảnh chụp hiện tại.",
    emptyMeasurement: "Không có bài viết để đo trong ảnh chụp này. Hãy mở một lượt chạy sau hoặc yêu cầu quản trị viên tạo ảnh chụp mới hơn.",
    emptyTopicLineage: "Không có bài viết để phân tích phả hệ chủ đề trong ảnh chụp này. Hãy mở một lượt chạy sau hoặc yêu cầu quản trị viên tạo ảnh chụp mới hơn.",
    emptyLineage: "Không có bài viết để tái dựng trong ảnh chụp này. Hãy mở một lượt chạy sau hoặc yêu cầu quản trị viên tạo ảnh chụp mới hơn.",
    emptyReport: "Không có bài viết cho báo cáo kỳ trong ảnh chụp này. Hãy mở một lượt chạy sau hoặc yêu cầu quản trị viên tạo ảnh chụp mới hơn.",
    corpusFailedMeasurement: "Các bài viết này đã được chọn để đo trong ảnh chụp này. Hãy yêu cầu quản trị viên khôi phục việc đo rồi chạy lại.",
    corpusSucceededMeasurement: "Các bài viết này đã được đo trong lượt chạy này.",
    corpusPendingMeasurement: "Các bài viết này sẽ được đo khi lượt chạy hoàn tất.",
    corpusCancelledMeasurement: "Các bài viết này lẽ ra sẽ được đo. Lượt chạy đã bị hủy trước khi tạo kết quả đã hiệu chuẩn.",
    corpusAttachedMeasurement: "Các bài viết này được đính kèm với lượt chạy đo này.",
    corpusFailedTopicLineage: "Các bài viết này đã được chọn để phân tích phả hệ chủ đề trong ảnh chụp này. Hãy yêu cầu quản trị viên khôi phục phân tích rồi chạy lại.",
    corpusSucceededTopicLineage: "Các bài viết này đã tạo thành phả hệ chủ đề trong lượt chạy này.",
    corpusPendingTopicLineage: "Các bài viết này sẽ tạo thành phả hệ chủ đề khi lượt chạy hoàn tất.",
    corpusCancelledTopicLineage: "Các bài viết này lẽ ra sẽ tạo thành phả hệ chủ đề. Lượt chạy đã bị hủy trước khi tạo kết quả chủ đề đã hiệu chuẩn.",
    corpusAttachedTopicLineage: "Các bài viết này được đính kèm với lượt chạy phả hệ chủ đề này.",
  },
};

export const ANALYSIS_RUN_COPY_KEYS = Object.keys(
  ENGLISH_ANALYSIS_RUN_COPY,
) as AnalysisRunCopyKey[];

/** Return analysis-run guidance in the active product locale. */
export function analysisRunText(key: AnalysisRunCopyKey): string {
  return ANALYSIS_RUN_COPY[getLocale()][key];
}
