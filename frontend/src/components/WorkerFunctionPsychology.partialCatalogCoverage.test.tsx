import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { WorkerFunctionConstructCatalogPayload } from "../api";
import { WorkerFunctionPsychology } from "./WorkerFunctionPsychology";

const PARTIAL_CATALOG: WorkerFunctionConstructCatalogPayload = {
  constructs: {},
  relations: [],
};

describe("WorkerFunctionPsychology partial catalog", () => {
  it("keeps omitted catalog dimensions empty instead of inventing constructs", () => {
    render(
      <WorkerFunctionPsychology
        profile={null}
        catalog={PARTIAL_CATALOG}
        loading={false}
      />,
    );

    expect(screen.getByRole("heading", { name: "Catalog dimensions" })).toBeVisible();
    expect(screen.getByText("Cognitive")).toBeVisible();
    expect(screen.getByText("Affective")).toBeVisible();
    expect(screen.getByText("Behavioral")).toBeVisible();
    expect(screen.getAllByText("0")).toHaveLength(3);
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});
