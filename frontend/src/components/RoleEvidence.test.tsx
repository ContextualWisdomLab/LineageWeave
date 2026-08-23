import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RoleEvidence } from "./RoleEvidence";

const BASE_PROPS = {
  actorContent: <strong>Ada West</strong>,
  actorName: "Ada West",
  actorTypeCode: "prov_person",
  actorTypeLabel: "Person",
  responsibility: "우리 측 후속",
  affiliationLabel: "Affiliation",
  affiliationAriaLabel: "R&R affiliation: Demo Corp",
  unresolvedLabel: "Not linked to catalog",
  genericUnitNote: "Specific business unit not stated in source",
};

describe("RoleEvidence", () => {
  it("falls back to the generic unresolved label when no reason is recorded", () => {
    render(
      <ul>
        <RoleEvidence {...BASE_PROPS} affiliationName="Demo Corp" affiliationCatalogId={null} />
      </ul>,
    );
    expect(screen.getByText("(Not linked to catalog)")).toBeInTheDocument();
  });

  it.each([
    ["reason_tied_candidates", "Multiple equally likely matches"],
    ["reason_no_live_client", "No live enrichment service configured"],
    ["reason_not_corroborated", "Checked, not independently corroborated"],
    ["reason_no_catalog_entry", "No matching catalog entry yet"],
  ])(
    "shows the specific reason %s for an unresolved affiliation instead of the generic label",
    (_reasonCode, expectedLabel) => {
      render(
        <ul>
          <RoleEvidence
            {...BASE_PROPS}
            affiliationName="Demo Corp"
            affiliationCatalogId={null}
            affiliationUnresolvedReasonLabel={expectedLabel}
          />
        </ul>,
      );
      expect(screen.getByText(`(${expectedLabel})`)).toBeInTheDocument();
      expect(screen.queryByText("(Not linked to catalog)")).not.toBeInTheDocument();
    },
  );

  it("shows nothing extra for the actor itself when no unresolved reason is known", () => {
    render(
      <ul>
        <RoleEvidence {...BASE_PROPS} affiliationName={null} />
      </ul>,
    );
    expect(screen.queryByText(/reason/i)).not.toBeInTheDocument();
  });

  it("shows the actor's own unresolved reason next to its name", () => {
    render(
      <ul>
        <RoleEvidence
          {...BASE_PROPS}
          affiliationName={null}
          actorUnresolvedReasonLabel="No matching catalog entry yet"
        />
      </ul>,
    );
    expect(screen.getByText("(No matching catalog entry yet)")).toBeInTheDocument();
  });

  it("shows the resolved affiliation as a link, not an unresolved reason, once linked", () => {
    render(
      <ul>
        <RoleEvidence
          {...BASE_PROPS}
          affiliationName="Demo Corp"
          affiliationCatalogId="corp-1"
          affiliationUnresolvedReasonLabel={null}
          onSelectAffiliation={() => undefined}
        />
      </ul>,
    );
    expect(screen.getByRole("button", { name: "R&R affiliation: Demo Corp" })).toBeInTheDocument();
    expect(screen.queryByText(/Not linked to catalog/)).not.toBeInTheDocument();
  });
});
