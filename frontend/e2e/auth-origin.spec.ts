import { expect, test } from "@playwright/test";

import {
  isExpectedApplicationUrl,
  isExpectedKeyverseAuthorizationUrl,
} from "./support/auth.js";

const COMPOSE_ISSUER = "http://localhost:18080/realms/lineageweave-demo";
const AUTH_PATH = "/realms/lineageweave-demo/protocol/openid-connect/auth";

test.describe("Keyverse authorization origin boundary", () => {
  test("rejects the expected realm path on a different origin", () => {
    expect(
      isExpectedKeyverseAuthorizationUrl(
        new URL(`https://identity.example${AUTH_PATH}?client_id=lineageweave-frontend`),
        COMPOSE_ISSUER,
      ),
    ).toBe(false);
  });

  test("accepts the configured Compose origin and realm authorization path", () => {
    expect(
      isExpectedKeyverseAuthorizationUrl(
        new URL(`http://localhost:18080${AUTH_PATH}?client_id=lineageweave-frontend`),
        COMPOSE_ISSUER,
      ),
    ).toBe(true);
  });

  test("matches the configured scheme instead of weakening HTTPS deployments", () => {
    const httpsIssuer = "https://identity.example/realms/lineageweave-demo";

    expect(
      isExpectedKeyverseAuthorizationUrl(
        new URL(`http://identity.example${AUTH_PATH}`),
        httpsIssuer,
      ),
    ).toBe(false);
    expect(
      isExpectedKeyverseAuthorizationUrl(
        new URL(`https://identity.example${AUTH_PATH}`),
        httpsIssuer,
      ),
    ).toBe(true);
  });

  test("accepts only the configured application origin after login", () => {
    const applicationUrl = "https://lineage.example/workspace";

    expect(isExpectedApplicationUrl(new URL("https://lineage.example/dashboard"), applicationUrl)).toBe(
      true,
    );
    expect(isExpectedApplicationUrl(new URL("https://identity.example/tenant/login"), applicationUrl)).toBe(
      false,
    );
  });
});
