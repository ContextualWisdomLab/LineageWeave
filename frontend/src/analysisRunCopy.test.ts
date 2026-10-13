import { describe, expect, it } from "vitest";
import type { AnalysisRun } from "./api";
import { analysisRunCaption, analysisRunCorpusHint, periodGroupMeasureCaption } from "./analysisRunCopy";
import { getLocale, setLocale, type Locale } from "./i18n";

function run(kind: AnalysisRun["run_kind_code"], status: AnalysisRun["status_code"]): AnalysisRun {
  return {
    run_kind_code: kind,
    status_code: status,
    status_label: status === "analysis_status_failed" ? "Failed" : "Pending",
    scope_kind_label: "Demo workspace",
  } as AnalysisRun;
}

describe("analysis run customer copy", () => {
  it("keeps fitting details out of group captions and gives an unready result a next action", () => {
    const report = {
      grouping_key: "demo-group",
      grouping_label: "Demo group",
      mean_theta: 0.42,
      fit_converged: true,
      selected_model: "private-model-sentinel",
    };
    expect(periodGroupMeasureCaption(report)).toBe("Demo group: mean θ 0.42");
    expect(periodGroupMeasureCaption({ ...report, fit_converged: false })).toBe(
      "Demo group: mean θ 0.42 — Ask an administrator to review this report before using it.",
    );
  });

  it("localizes the report review action in each supported locale", () => {
    const original = getLocale();
    const actions: Record<Locale, string> = {
      en: "Ask an administrator to review this report before using it.",
      ko: "이 보고서를 활용하기 전에 관리자에게 검토를 요청하세요.",
      zh: "使用此报告前，请先请管理员审核。",
      ja: "このレポートを利用する前に、管理者に確認を依頼してください。",
      vi: "Trước khi dùng báo cáo này, hãy nhờ quản trị viên xem lại.",
    };
    try {
      for (const [locale, action] of Object.entries(actions) as [Locale, string][]) {
        setLocale(locale);
        expect(periodGroupMeasureCaption({
          grouping_key: "demo-group", mean_theta: 0.42, fit_converged: false,
        })).toContain(action);
      }
    } finally {
      setLocale(original);
    }
  });

  it("names governed run kinds by the task", () => {
    expect(analysisRunCaption(run("analysis_run_tepp", "analysis_status_failed"))).toBe(
      "Record measurement · Failed · Demo workspace",
    );
    expect(analysisRunCaption(run("analysis_run_topic_lineage", "analysis_status_pending"))).toBe(
      "Topic history · Pending · Demo workspace",
    );
  });

  it("keeps every measurement and topic state actionable without internal boundaries", () => {
    for (const kind of ["analysis_run_tepp", "analysis_run_topic_lineage"] as const) {
      for (const status of [
        "analysis_status_pending",
        "analysis_status_running",
        "analysis_status_succeeded",
        "analysis_status_failed",
        "analysis_status_cancelled",
        null,
      ] as const) {
        const copy = analysisRunCorpusHint(run(kind, status));
        expect(copy).toBeTruthy();
        expect(copy).not.toMatch(/TEPP|transport|provider|model|worker/i);
        if (status === "analysis_status_pending") expect(copy).toContain("Start this run");
        if (status === "analysis_status_running") expect(copy).toContain("Refresh this run");
        if (status === "analysis_status_failed") expect(copy).toContain("Ask an administrator");
      }
    }
    expect(analysisRunCorpusHint(run("analysis_run_lineage", "analysis_status_pending"))).toBeNull();
  });

  it("localizes run captions and recovery actions in every supported locale", () => {
    const original = getLocale();
    const labels: Record<Locale, string> = {
      en: "Record measurement",
      ko: "기록 측정",
      zh: "记录测量",
      ja: "記録の測定",
      vi: "Đo lường bản ghi",
    };
    try {
      for (const [locale, label] of Object.entries(labels) as [Locale, string][]) {
        setLocale(locale);
        expect(analysisRunCaption(run("analysis_run_tepp", "analysis_status_failed"))).toContain(label);
        const action = analysisRunCorpusHint(run("analysis_run_tepp", "analysis_status_failed"));
        expect(action).toBeTruthy();
        expect(action).not.toContain("{analysis}");
        expect(action).not.toMatch(/TEPP|transport|provider|model|worker/i);
        if (locale !== "en") expect(action).not.toContain("Ask an administrator");
      }
    } finally {
      setLocale(original);
    }
  });
});
