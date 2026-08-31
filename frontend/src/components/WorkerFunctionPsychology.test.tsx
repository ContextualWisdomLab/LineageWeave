import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { setLocale } from "../i18n";
import type {
  WorkerFunctionConstructCatalogPayload,
  WorkerFunctionProfilePayload,
} from "../api";
import { WorkerFunctionPsychology } from "./WorkerFunctionPsychology";

const PROFILE: WorkerFunctionProfilePayload = {
  function_domain: "data",
  function_rank: 2,
  function_label: "Analyzing",
  cognitive_demands: [
    {
      iri: "https://contextualwisdomlab.github.io/LineageWeave/ontology#cogDiagnosticReasoning",
      category: "cognitive",
      label: "Diagnostic Reasoning",
      dimension: "analytic_inference",
      theoretical_basis: "Patel, Evans, & Groen (1989)",
      definition: "Hypothesis-driven inference to isolate root causes.",
    },
  ],
  mental_workload_demands: [],
  affective_demands: [],
  emotional_labor_demands: [],
  behavioral_manifestations: [
    {
      iri: "https://contextualwisdomlab.github.io/LineageWeave/ontology#behCoreTaskPerformance",
      category: "behavioral",
      label: "Core Task Performance",
      dimension: "task_performance",
      theoretical_basis: "Campbell (1990)",
      definition: "Direct execution of assigned technical processes.",
    },
  ],
  psychomotor_behaviors: [],
  interpersonal_behaviors: [],
};

const CATALOG: WorkerFunctionConstructCatalogPayload = {
  constructs: {
    cognitive: [
      {
        iri: "https://contextualwisdomlab.github.io/LineageWeave/ontology#cogMentalWorkload",
        category: "cognitive",
        label: "Mental Workload",
        dimension: "cognitive_load",
        theoretical_basis: "Sweller (1988)",
        definition: "Proportion of cognitive capacity demanded by task difficulty.",
      },
    ],
    affective: [],
    behavioral: [],
  },
  relations: [],
};

describe("WorkerFunctionPsychology", () => {
  afterEach(() => setLocale("en"));

  it("renders the worker function profile slots with metadata and references", () => {
    render(<WorkerFunctionPsychology profile={PROFILE} catalog={CATALOG} />);
    expect(screen.getByRole("heading", { name: "Work psychology" })).toBeVisible();
    expect(screen.getByText("Analyzing")).toBeVisible();
    expect(screen.getByText("data · rank 2")).toBeVisible();
    expect(screen.getByText("Diagnostic Reasoning")).toBeVisible();
    expect(screen.getByText(/Patel, Evans, & Groen \(1989\)/)).toBeVisible();
    expect(screen.getByText("Behavioral manifestations")).toBeVisible();
  });

  it("shows the catalog dimension groups with linking construct chips", () => {
    render(<WorkerFunctionPsychology profile={null} catalog={CATALOG} loading={false} />);
    expect(screen.getByText("Catalog dimensions")).toBeVisible();
    expect(screen.getByRole("link", { name: "Mental Workload" })).toHaveAttribute(
      "href",
      "https://contextualwisdomlab.github.io/LineageWeave/ontology#cogMentalWorkload",
    );
  });

  it("shows an honest loading placeholder", () => {
    render(<WorkerFunctionPsychology profile={null} catalog={null} loading />);
    expect(screen.getByText(/Work psychology details are not ready/i)).toBeVisible();
    expect(screen.queryByText(/ontology|projection|provider|model/i)).not.toBeInTheDocument();
  });

  it.each([
    ["en", "Work psychology details are not ready."],
    ["ko", "직무 심리 상세 정보가 아직 준비되지 않았습니다."],
    ["zh", "工作心理详情尚未就绪。"],
    ["ja", "仕事の心理に関する詳細はまだ準備できていません。"],
    ["vi", "Chi tiết tâm lý công việc chưa sẵn sàng."],
  ] as const)("keeps the loading next action customer-facing in %s", (locale, expected) => {
    setLocale(locale);
    render(<WorkerFunctionPsychology profile={null} catalog={null} loading />);
    expect(screen.getByText(new RegExp(expected))).toBeVisible();
    expect(screen.queryByText(/ontology|projection|provider|model/i)).not.toBeInTheDocument();
  });

  it("does not invent a profile when none is loaded", () => {
    render(<WorkerFunctionPsychology profile={null} catalog={CATALOG} />);
    expect(screen.queryByText("Analyzing")).not.toBeInTheDocument();
    expect(screen.getByText("Catalog dimensions")).toBeVisible();
  });
});
