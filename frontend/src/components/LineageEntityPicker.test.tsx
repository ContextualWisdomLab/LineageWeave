import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { LineageEntityPicker } from "./LineageEntityPicker";

const demoEntities = [
  { corporate_entity_id: "corp-demo", entity_name: "Demo Corp" },
  { corporate_entity_id: "corp-north", entity_name: "Northridge Grid" },
];

describe("LineageEntityPicker", () => {
  it("stays hidden for a single affiliation", () => {
    const { container } = render(
      <LineageEntityPicker
        entities={[demoEntities[0]]}
        selectedEntityId="corp-demo"
        onSelectEntityId={() => undefined}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("lets a multi-affiliation operator choose Northridge Grid", async () => {
    const onSelectEntityId = vi.fn();
    render(
      <LineageEntityPicker
        entities={demoEntities}
        selectedEntityId="corp-demo"
        onSelectEntityId={onSelectEntityId}
      />,
    );
    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "Corporate entity to reconstruct" }),
      "corp-north",
    );
    expect(onSelectEntityId).toHaveBeenCalledWith("corp-north");
  });
});
