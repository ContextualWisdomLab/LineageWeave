import { beforeEach, describe, expect, it, vi } from "vitest";

const render = vi.fn();
const createRoot = vi.fn(() => ({ render }));

vi.mock("react-dom/client", () => ({
  createRoot,
}));

vi.mock("./App.tsx", () => ({
  default: function MockApp() {
    return null;
  },
}));

describe("browser bootstrap", () => {
  beforeEach(() => {
    render.mockClear();
    createRoot.mockClear();
    document.body.innerHTML = '<div id="root"></div>';
  });

  it("mounts the authorized app on the document root", async () => {
    await import("./main");
    expect(createRoot).toHaveBeenCalledTimes(1);
    expect(createRoot.mock.calls[0][0]).toBe(document.getElementById("root"));
    expect(render).toHaveBeenCalledTimes(1);
  });
});
