"""Lock the browser OIDC test runner outside the product identity boundary."""

import json
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_COMPOSE = PROJECT_ROOT / "tests" / "compose.oidc-e2e.yml"
IDP_COMPOSE = PROJECT_ROOT / "tests" / "compose.oidc-conformance-idp.yml"
IDP_REALM = PROJECT_ROOT / "tests" / "oidc-e2e-import" / "lw-e2e-realm.json"
IDP_DOCKERFILE = PROJECT_ROOT / "tests" / "Dockerfile.oidc-conformance"
E2E_SCRIPT = PROJECT_ROOT / "scripts" / "run_oidc_conformance_e2e.sh"
PRODUCT_COMPOSE = PROJECT_ROOT / "compose.yaml"


def test_oidc_e2e_runner_uses_a_separate_conformance_idp() -> None:
    """Keep the test RP runner direct-PG while never packaging a local issuer."""
    test_compose = TEST_COMPOSE.read_text(encoding="utf-8")
    product_compose = PRODUCT_COMPOSE.read_text(encoding="utf-8")

    assert "name: lineageweaveoidce2e" in test_compose
    assert "network_mode: host" in test_compose
    assert "LINEAGEWEAVE_DSN: ${LINEAGEWEAVE_E2E_DSN:?" in test_compose
    assert "LINEAGE_SOURCE_TABLE: ${LINEAGEWEAVE_E2E_SOURCE_TABLE:?" in test_compose
    assert "KEYVERSE_ISSUER: http://localhost:" in test_compose
    assert "\n  keycloak:" not in test_compose
    assert "lineage-http-standin:" not in test_compose
    assert "keycloak:" not in product_compose


def test_conformance_idp_fixture_is_separate_and_claim_complete() -> None:
    """Keep an official test IdP separate while supplying required RP claims."""
    idp_compose = IDP_COMPOSE.read_text(encoding="utf-8")
    realm = json.loads(IDP_REALM.read_text(encoding="utf-8"))
    dockerfile = IDP_DOCKERFILE.read_text(encoding="utf-8")
    script = E2E_SCRIPT.read_text(encoding="utf-8")

    assert "dockerfile: Dockerfile.oidc-conformance" in idp_compose
    assert "FROM quay.io/keycloak/keycloak:26.0.8" in dockerfile
    assert "COPY oidc-e2e-import/lw-e2e-realm.json" in dockerfile
    assert "oidc-e2e-valkey:" in idp_compose
    assert "compose/keyverse_oidc.py" not in idp_compose
    assert "lineage-http-standin:" not in idp_compose
    assert realm["realm"] == "lw-e2e"
    client = next(item for item in realm["clients"] if item["clientId"] == "lineageweave-web")
    assert client["redirectUris"] == ["${LINEAGEWEAVE_E2E_REDIRECT_URI}"]
    assert client["webOrigins"] == ["${LINEAGEWEAVE_E2E_WEB_ORIGIN}"]
    assert "LINEAGEWEAVE_E2E_REDIRECT_URI: http://127.0.0.1:${LINEAGEWEAVE_E2E_PORT:-18105}/api/oidc/callback" in idp_compose
    claims = {item["config"]["claim.name"] for item in client["protocolMappers"]}
    assert claims == {"org", "workspace", "role"}
    assert all(item["config"]["introspection.token.claim"] == "true" for item in client["protocolMappers"])
    user = realm["users"][0]
    assert user["email"].endswith("@example.test")
    assert user["realmRoles"] == ["reader"]
    assert user["attributes"] == {
        "org": ["${LINEAGEWEAVE_E2E_ORG}"],
        "workspace": ["${LINEAGEWEAVE_E2E_WORKSPACE}"],
    }
    assert "LINEAGEWEAVE_E2E_ORG" in idp_compose
    assert "LINEAGEWEAVE_E2E_WORKSPACE" in idp_compose
    assert "compose.oidc-conformance-idp.yml up -d --wait" in script
    assert "compose.oidc-e2e.yml up -d --build --wait" in script
    assert "trap cleanup EXIT" in script
    assert "compose.oidc-e2e.yml down" in script
    assert "compose.oidc-conformance-idp.yml down" in script
    assert os.access(E2E_SCRIPT, os.X_OK)
    assert "LINEAGEWEAVE_E2E_REQUIRE_DATA" in script
