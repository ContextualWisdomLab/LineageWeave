/** Env-driven config -- no hardcoded production identity-provider URLs. Vite only
 * exposes `VITE_`-prefixed variables to client code by design. */

export const config = {
  oidcIssuer:
    import.meta.env.VITE_KEYVERSE_ISSUER ||
    import.meta.env.VITE_OIDC_ISSUER ||
    import.meta.env.VITE_KEYCLOAK_ISSUER ||
    "http://localhost:18080/realms/lineageweave-demo",
  oidcClientId:
    import.meta.env.VITE_KEYVERSE_CLIENT_ID ||
    import.meta.env.VITE_OIDC_CLIENT_ID ||
    import.meta.env.VITE_KEYCLOAK_CLIENT_ID ||
    "lineageweave-frontend",
  backendBaseUrl: import.meta.env.VITE_BACKEND_BASE_URL || "http://localhost:18420",
};
