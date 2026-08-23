import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  authProps: null as null | { onSigninCallback: (user?: { state?: unknown }) => void },
  createRoot: vi.fn(),
  renderRoot: vi.fn(),
  restoreReturnUrl: vi.fn(() => "/board?post=synthetic-post"),
}));

vi.mock("react-dom/client", () => ({
  createRoot: mocks.createRoot,
}));

vi.mock("react-oidc-context", () => ({
  AuthProvider: (props: {
    children: React.ReactNode;
    onSigninCallback: (user?: { state?: unknown }) => void;
  }) => {
    mocks.authProps = props;
    return props.children;
  },
}));

vi.mock("oidc-client-ts", () => ({
  WebStorageStateStore: class WebStorageStateStore {
    constructor(_options: unknown) {}
  },
}));

vi.mock("./App.tsx", () => ({
  default: () => <p>Workspace application</p>,
}));

vi.mock("./oidcReturnUrl", () => ({
  restoreOidcReturnUrl: mocks.restoreReturnUrl,
}));

it("mounts the OIDC application and restores its deep link after sign-in", async () => {
  document.body.innerHTML = '<div id="root"></div>';
  mocks.createRoot.mockReturnValue({ render: mocks.renderRoot });
  const replaceState = vi.spyOn(window.history, "replaceState");

  await import("./main.tsx");

  expect(mocks.createRoot).toHaveBeenCalledWith(document.getElementById("root"));
  render(mocks.renderRoot.mock.calls[0][0]);
  expect(screen.getByText("Workspace application")).toBeInTheDocument();

  const user = { state: { returnUrl: "/board?post=synthetic-post" } };
  mocks.authProps?.onSigninCallback(user);
  expect(mocks.restoreReturnUrl).toHaveBeenCalledWith(user.state);
  expect(replaceState).toHaveBeenCalledWith(
    {},
    document.title,
    "/board?post=synthetic-post",
  );
});
