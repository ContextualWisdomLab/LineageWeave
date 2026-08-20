import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { type User, WebStorageStateStore } from "oidc-client-ts";
import { AuthProvider } from "react-oidc-context";
import "./index.css";
import App from "./App.tsx";
import { config } from "./config";

const oidcConfig = {
  authority: config.oidcIssuer,
  client_id: config.oidcClientId,
  redirect_uri: window.location.origin,
  post_logout_redirect_uri: window.location.origin,
  userStore: new WebStorageStateStore({ store: window.localStorage }),
  onSigninCallback: (user: User | undefined) => {
    const state = user?.state;
    const requestedReturnUrl =
      typeof state === "object" &&
      state !== null &&
      "returnUrl" in state &&
      typeof state.returnUrl === "string"
        ? state.returnUrl
        : "";
    let storedReturnUrl = "";
    try {
      storedReturnUrl = window.sessionStorage.getItem("lineageweave.oidc.returnUrl") ?? "";
      window.sessionStorage.removeItem("lineageweave.oidc.returnUrl");
    } catch {
      // OIDC state remains sufficient when session storage is unavailable.
    }
    const returnUrl =
      [requestedReturnUrl, storedReturnUrl].find(
        (candidate) => candidate.startsWith("/") && !candidate.startsWith("//"),
      )
        ? [requestedReturnUrl, storedReturnUrl].find(
            (candidate) => candidate.startsWith("/") && !candidate.startsWith("//"),
          )!
        : window.location.pathname;

    // Strip OIDC response params while preserving the requested deep link.
    window.history.replaceState({}, document.title, returnUrl);
  },
};

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AuthProvider {...oidcConfig}>
      <App />
    </AuthProvider>
  </StrictMode>,
);
