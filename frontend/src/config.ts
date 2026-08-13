/** Env-driven config -- no hardcoded backend/Keycloak URLs. Vite only
 * exposes `VITE_`-prefixed variables to client code by design. */

export const config = {
  keycloakIssuer: import.meta.env.VITE_KEYCLOAK_ISSUER ?? "http://localhost:18080/realms/lineageweave-demo",
  keycloakClientId: import.meta.env.VITE_KEYCLOAK_CLIENT_ID ?? "lineageweave-frontend",
  backendBaseUrl: import.meta.env.VITE_BACKEND_BASE_URL ?? "http://localhost:18420",
};
