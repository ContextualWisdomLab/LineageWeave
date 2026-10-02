import { beforeEach, describe, expect, it, vi } from "vitest";

const render = vi.fn();
const createRoot = vi.fn((_container: Element | DocumentFragment) => ({ render }));

vi.mock("react-dom/client", () => ({
  createRoot,
}));

vi.mock("./App.tsx", () => ({
  default: function MockApp() {
    return null;
  },
}));

type RenderedAuthTree = {
  props: {
    children: {
      props: {
        onSigninCallback: (user?: { state?: unknown }) => void;
      };
    };
  };
};

describe("browser bootstrap", () => {
  beforeEach(() => {
    render.mockClear();
    createRoot.mockClear();
    document.body.innerHTML = '<div id="root"></div>';
  });

  it("mounts the authorized app and restores the requested URL after sign-in", async () => {
    const replaceState = vi.spyOn(window.history, "replaceState").mockImplementation(() => undefined);

    await import("./main");

    expect(createRoot).toHaveBeenCalledTimes(1);
    expect(createRoot.mock.calls[0][0]).toBe(document.getElementById("root"));
    expect(render).toHaveBeenCalledTimes(1);

    const tree = render.mock.calls[0][0] as unknown as RenderedAuthTree;
    tree.props.children.props.onSigninCallback({ state: "/projects?post=demo-post" });
    expect(replaceState).toHaveBeenCalledWith({}, document.title, "/projects?post=demo-post");

    replaceState.mockRestore();
  });
});
