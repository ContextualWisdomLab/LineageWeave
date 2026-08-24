/// <reference types="vite/client" />

declare module "*.png?inline" {
  const src: string;
  export default src;
}

interface ImportMetaEnv {
  readonly VITE_KEYVERSE_ISSUER?: string;
  readonly VITE_KEYVERSE_CLIENT_ID?: string;
  readonly VITE_OIDC_ISSUER?: string;
  readonly VITE_OIDC_CLIENT_ID?: string;
  readonly VITE_KEYCLOAK_ISSUER?: string;
  readonly VITE_KEYCLOAK_CLIENT_ID?: string;
  readonly VITE_BACKEND_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
