import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { type User, WebStorageStateStore } from "oidc-client-ts";
import { AuthProvider } from "react-oidc-context";
import "./index.css";
import App from "./App.tsx";
import { config } from "./config";
import { restoreOidcReturnUrl } from "./oidcReturnUrl";

const oidcConfig = {
  authority: config.oidcIssuer,
  client_id: config.oidcClientId,
  redirect_uri: window.location.origin,
  post_logout_redirect_uri: window.location.origin,
  userStore: new WebStorageStateStore({ store: window.localStorage }),
  onSigninCallback: (user: User | undefined) => {
    const returnUrl = restoreOidcReturnUrl(user?.state);
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
