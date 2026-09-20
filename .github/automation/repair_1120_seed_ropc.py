#!/usr/bin/env python3
"""One-shot source repair for the #1120 seed/bootstrap ROPC boundary."""

from __future__ import annotations

import argparse
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEED = ROOT / "scripts" / "seed_demo_data.py"
WARM = ROOT / "scripts" / "warm_seeded_post_content.py"
CONTRACT = ROOT / "tests" / "test_seed_demo_identity_contract.py"
MAKEFILE = ROOT / "Makefile"
MAKEFILE_CONTRACT = ROOT / "tests" / "test_makefile_contract.py"


def write_contract() -> None:
    CONTRACT.write_text(
        textwrap.dedent(
            '''\
            """Keep synthetic seed/bootstrap identity off resource-owner password grants."""

            from __future__ import annotations

            import importlib.util
            import json
            from pathlib import Path

            import pytest


            ROOT = Path(__file__).resolve().parents[1]
            SEED_SCRIPT = ROOT / "scripts" / "seed_demo_data.py"
            WARM_SCRIPT = ROOT / "scripts" / "warm_seeded_post_content.py"
            MAKEFILE = ROOT / "Makefile"


            def _load_script(path: Path, name: str):
                spec = importlib.util.spec_from_file_location(name, path)
                assert spec is not None and spec.loader is not None
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module


            def _realm(users: list[dict[str, object]]) -> dict[str, object]:
                return {"realm": "lineageweave-demo", "users": users}


            def test_seed_subjects_are_read_from_realm_fixture_without_admin_login(tmp_path: Path) -> None:
                seed = _load_script(SEED_SCRIPT, "seed_demo_data_contract")
                fixture = tmp_path / "realm-export.json"
                fixture.write_text(
                    json.dumps(
                        _realm(
                            [
                                {"id": "analyst-sub", "username": "demo.analyst", "enabled": True},
                                {"id": "admin-sub", "username": "demo.admin", "enabled": True},
                            ]
                        )
                    ),
                    encoding="utf-8",
                )

                assert seed._load_demo_user_subjects(fixture) == {
                    "demo.analyst": "analyst-sub",
                    "demo.admin": "admin-sub",
                }


            @pytest.mark.parametrize(
                "users, message",
                [
                    ([{"id": "analyst-sub", "username": "demo.analyst", "enabled": True}], "missing"),
                    (
                        [
                            {"id": "same-sub", "username": "demo.analyst", "enabled": True},
                            {"id": "same-sub", "username": "demo.admin", "enabled": True},
                        ],
                        "subject",
                    ),
                    (
                        [
                            {"id": "analyst-sub", "username": "demo.analyst", "enabled": False},
                            {"id": "admin-sub", "username": "demo.admin", "enabled": True},
                        ],
                        "enabled",
                    ),
                ],
            )
            def test_seed_subject_fixture_fails_closed(
                tmp_path: Path, users: list[dict[str, object]], message: str
            ) -> None:
                seed = _load_script(SEED_SCRIPT, f"seed_demo_data_contract_{message}")
                fixture = tmp_path / "realm-export.json"
                fixture.write_text(json.dumps(_realm(users)), encoding="utf-8")

                with pytest.raises(RuntimeError, match=message):
                    seed._load_demo_user_subjects(fixture)


            def test_seed_and_warm_scripts_contain_no_resource_owner_password_grant() -> None:
                seed_source = SEED_SCRIPT.read_text(encoding="utf-8")
                warm_source = WARM_SCRIPT.read_text(encoding="utf-8")

                assert '\"grant_type\": \"password\"' not in seed_source
                assert "admin-cli" not in seed_source
                assert "KEYCLOAK_ADMIN_PASSWORD" not in seed_source
                assert '\"grant_type\": \"password\"' not in warm_source
                assert '\"grant_type\": \"client_credentials\"' in warm_source
                assert "demo.analyst" not in warm_source
                assert "LINEAGEWEAVE_DEMO_USER_PASSWORD" not in warm_source


            def test_warmup_uses_confidential_automation_client(monkeypatch: pytest.MonkeyPatch) -> None:
                warm = _load_script(WARM_SCRIPT, "warm_seeded_post_content_contract")
                observed: dict[str, object] = {}

                def fake_post_form(url: str, fields: dict[str, str], *, timeout: float):
                    observed.update({"url": url, "fields": fields, "timeout": timeout})
                    return {"access_token": "machine-token"}

                monkeypatch.setattr(warm, "post_form", fake_post_form)

                assert warm._machine_access_token("http://localhost:18080", "secret") == "machine-token"
                assert observed["fields"] == {
                    "grant_type": "client_credentials",
                    "client_id": "lineageweave-test-automation",
                    "client_secret": "secret",
                }


            def test_make_seed_orders_fixture_then_authorization_then_machine_warmup() -> None:
                makefile = MAKEFILE.read_text(encoding="utf-8")
                seed_block = makefile.split("seed:\n", 1)[1].split("\n\n# Authenticated Compose", 1)[0]

                assert "KEYCLOAK_ADMIN_PASSWORD" not in seed_block
                assert "KEYCLOAK_CLIENT_SECRET is required" in seed_block
                commands = [
                    "python scripts/seed_demo_data.py",
                    "python scripts/provision_local_service_accounts.py",
                    "python scripts/warm_seeded_post_content.py",
                ]
                positions = [seed_block.index(command) for command in commands]
                assert positions == sorted(positions)
            '''
        ),
        encoding="utf-8",
    )


def apply_repair() -> None:
    source = SEED.read_text(encoding="utf-8")

    doc_start = source.index('"""')
    doc_end = source.index('"""', doc_start + 3) + 3
    replacement_doc = textwrap.dedent(
        '''\
        """Seed synthetic demo data using deterministic local identity fixtures.

        Human demo subjects are read fail-closed from the checked-in Keycloak realm
        export and then bound to LineageWeave-owned roles/affiliations in PostgreSQL.
        The seed path does not authenticate to Keycloak, mint a resource-owner token,
        or depend on a master-realm administrator password. Seeded tickets still
        ``XADD`` onto Valkey so the Activity panel is populated.

        Machine-authenticated post-content warm-up is intentionally separated into
        ``scripts/warm_seeded_post_content.py`` and runs only after the confidential
        service account has been provisioned in LineageWeave's authorization model.

        Canonical usage:
          uv run --locked --extra dev --extra backend python scripts/seed_demo_data.py
        """'''
    )
    source = source[:doc_start] + replacement_doc + source[doc_end:]

    old_imports = (
        "import argparse\n"
        "import hashlib\n"
        "import os\n"
        "import time\n"
        "import sys\n"
        "from pathlib import Path\n"
        "from urllib.parse import urlencode\n"
    )
    new_imports = (
        "import argparse\n"
        "import hashlib\n"
        "import json\n"
        "import sys\n"
        "from pathlib import Path\n"
    )
    if old_imports not in source:
        raise RuntimeError("seed import block drifted")
    source = source.replace(old_imports, new_imports, 1)
    source = source.replace(
        "from lineageweave.http_client import get_json, get_json_list, post_form\n",
        "",
        1,
    )

    old_defaults = (
        'DEFAULT_KEYCLOAK_BASE_URL = "http://localhost:18080"\n'
        'DEFAULT_KEYCLOAK_ADMIN_USER = os.environ.get("KEYCLOAK_ADMIN", "admin")\n'
        'DEFAULT_VALKEY_URL = "redis://localhost:16379/0"\n'
    )
    new_defaults = (
        "DEFAULT_REALM_EXPORT_PATH = (\n"
        "    Path(__file__).resolve().parents[1] / \"docker\" / \"keycloak\" / \"realm-export.json\"\n"
        ")\n"
        'DEFAULT_VALKEY_URL = "redis://localhost:16379/0"\n'
    )
    if old_defaults not in source:
        raise RuntimeError("seed Keycloak defaults drifted")
    source = source.replace(old_defaults, new_defaults, 1)

    function_start = source.index("def _fetch_demo_user_subjects(")
    function_end = source.index("\n\ndef seed(", function_start)
    loader = textwrap.dedent(
        '''\
        def _load_demo_user_subjects(
            realm_export_path: Path = DEFAULT_REALM_EXPORT_PATH,
        ) -> dict[str, str]:
            """Return deterministic enabled human subjects from the local realm fixture."""
            realm = json.loads(realm_export_path.read_text(encoding="utf-8"))
            if not isinstance(realm, dict) or realm.get("realm") != REALM:
                raise RuntimeError(f"realm fixture must describe {REALM!r}")
            users = realm.get("users")
            if not isinstance(users, list):
                raise RuntimeError("realm fixture must contain a users array")

            required = {"demo.analyst", "demo.admin"}
            subjects: dict[str, str] = {}
            subject_owners: dict[str, str] = {}
            for user in users:
                if not isinstance(user, dict):
                    continue
                username = user.get("username")
                if username not in required:
                    continue
                if username in subjects:
                    raise RuntimeError(f"duplicate realm demo user: {username}")
                if user.get("serviceAccountClientId") is not None:
                    raise RuntimeError(f"realm demo user {username!r} must be a human user")
                if user.get("enabled") is not True:
                    raise RuntimeError(f"realm demo user {username!r} must be enabled")
                subject_id = user.get("id")
                if (
                    not isinstance(subject_id, str)
                    or not subject_id
                    or subject_id != subject_id.strip()
                ):
                    raise RuntimeError(
                        f"realm demo user {username!r} must declare a canonical subject id"
                    )
                prior_username = subject_owners.get(subject_id)
                if prior_username is not None:
                    raise RuntimeError(
                        f"realm demo subject {subject_id!r} is shared by "
                        f"{prior_username!r} and {username!r}"
                    )
                subjects[username] = subject_id
                subject_owners[subject_id] = username

            missing = sorted(required.difference(subjects))
            if missing:
                raise RuntimeError(
                    "realm fixture is missing required demo user(s): " + ", ".join(missing)
                )
            return subjects
        '''
    )
    source = source[:function_start] + loader + source[function_end:]

    warm_start = source.index('\n\nDEFAULT_BACKEND_BASE_URL = "http://localhost:18420"')
    main_start = source.index("\ndef main() -> None:", warm_start)
    source = source[:warm_start] + "\n\n" + source[main_start + 1:]

    main_start = source.index("def main() -> None:")
    main_end = source.index('\n\nif __name__ == "__main__":', main_start)
    main = textwrap.dedent(
        '''\
        def main() -> None:
            parser = argparse.ArgumentParser(description=__doc__)
            parser.add_argument("--postgres-dsn", default=DEFAULT_POSTGRES_DSN)
            parser.add_argument(
                "--realm-export-path",
                type=Path,
                default=DEFAULT_REALM_EXPORT_PATH,
                help="Checked-in local Keycloak realm fixture used for deterministic demo subjects.",
            )
            parser.add_argument("--valkey-url", default=DEFAULT_VALKEY_URL)
            args = parser.parse_args()

            subjects = _load_demo_user_subjects(args.realm_export_path)
            seed(args.postgres_dsn, subjects, args.valkey_url)
            print(f"Seeded synthetic demo data for accounts: {subjects}")
        '''
    )
    source = source[:main_start] + main + source[main_end:]
    SEED.write_text(source, encoding="utf-8")

    WARM.write_text(
        textwrap.dedent(
            '''\
            #!/usr/bin/env python3
            """Warm seeded post-content ingestion with the local confidential machine actor.

            Run after ``scripts/provision_local_service_accounts.py``. This path obtains a
            short-lived Client Credentials token for ``lineageweave-test-automation`` and
            opens seeded post content through the public API, preserving the production lazy
            ingestion path without using a human password or browser client.
            """

            from __future__ import annotations

            import argparse
            import os
            import sys
            import time
            from pathlib import Path

            sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

            import psycopg2

            from lineageweave.http_client import get_json, post_form

            REALM = "lineageweave-demo"
            CLIENT_ID = "lineageweave-test-automation"
            DEFAULT_POSTGRES_DSN = (
                "postgresql://lineageweave:lineageweave_dev_only@localhost:15432/lineageweave"
            )
            DEFAULT_KEYCLOAK_BASE_URL = "http://localhost:18080"
            DEFAULT_BACKEND_BASE_URL = "http://localhost:18420"


            def _machine_access_token(keycloak_base_url: str, client_secret: str) -> str:
                """Return one short-lived API token for the provisioned automation actor."""
                response = post_form(
                    f"{keycloak_base_url}/realms/{REALM}/protocol/openid-connect/token",
                    {
                        "grant_type": "client_credentials",
                        "client_id": CLIENT_ID,
                        "client_secret": client_secret,
                    },
                    timeout=30.0,
                )
                token = response.get("access_token")
                if not isinstance(token, str) or not token.strip():
                    raise RuntimeError("Keycloak client-credentials response omitted access_token")
                return token


            def warm_seeded_post_content(
                postgres_dsn: str,
                keycloak_base_url: str,
                backend_base_url: str,
                client_secret: str,
            ) -> int:
                """Open seeded demo posts once through the authenticated API."""
                for _ in range(60):
                    try:
                        get_json(f"{backend_base_url}/healthz", timeout=5.0)
                        break
                    except Exception:
                        time.sleep(2)
                else:
                    raise RuntimeError(
                        f"backend at {backend_base_url} is not serving /healthz; run `make up` first"
                    )

                token = _machine_access_token(keycloak_base_url, client_secret)
                connection = psycopg2.connect(postgres_dsn)
                try:
                    with connection.cursor() as cur:
                        cur.execute(
                            "select post_id from source_post where post_title like 'Demo %post'"
                        )
                        post_ids = [str(row[0]) for row in cur.fetchall()]
                finally:
                    connection.close()

                for post_id in post_ids:
                    get_json(
                        f"{backend_base_url}/api/posts/{post_id}/content",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=60.0,
                    )
                return len(post_ids)


            def main() -> int:
                parser = argparse.ArgumentParser(description=__doc__)
                parser.add_argument("--postgres-dsn", default=DEFAULT_POSTGRES_DSN)
                parser.add_argument("--keycloak-base-url", default=DEFAULT_KEYCLOAK_BASE_URL)
                parser.add_argument("--backend-base-url", default=DEFAULT_BACKEND_BASE_URL)
                args = parser.parse_args()
                client_secret = os.environ.get("KEYCLOAK_CLIENT_SECRET")
                if not client_secret:
                    parser.error("set KEYCLOAK_CLIENT_SECRET for the local test-automation client")

                count = warm_seeded_post_content(
                    args.postgres_dsn,
                    args.keycloak_base_url,
                    args.backend_base_url,
                    client_secret,
                )
                print(f"Warmed post-content ingestion for {count} seeded posts")
                return 0


            if __name__ == "__main__":
                raise SystemExit(main())
            '''
        ),
        encoding="utf-8",
    )

    makefile = MAKEFILE.read_text(encoding="utf-8")
    old_seed = textwrap.dedent(
        '''\
        # Seeds synthetic corp/account/post rows keyed to the actual Keycloak demo
        # users' real subject ids, plus Valkey ticket_created events so Activity
        # is not empty (see scripts/seed_demo_data.py). The second command binds the
        # realm's deterministic confidential service-account subjects to the same
        # DB-owned affiliation/role model; it does not authenticate to Keycloak.
        seed:
        \t@test -n "$${KEYCLOAK_ADMIN_PASSWORD:-}" || { echo "KEYCLOAK_ADMIN_PASSWORD is required" >&2; exit 1; }; \\
        \tuv run --locked --extra dev --extra backend python scripts/seed_demo_data.py; \\
        \tuv run --locked --extra dev --extra backend python scripts/provision_local_service_accounts.py
        '''
    )
    new_seed = textwrap.dedent(
        '''\
        # Seed deterministic human fixtures, bind confidential machine actors, then
        # exercise the lazy post-content path with the provisioned automation subject.
        # No master-admin or resource-owner password grant participates in this target.
        seed:
        \t@test -n "$${KEYCLOAK_CLIENT_SECRET:-}" || { echo "KEYCLOAK_CLIENT_SECRET is required" >&2; exit 1; }
        \tuv run --locked --extra dev --extra backend python scripts/seed_demo_data.py
        \tuv run --locked --extra dev --extra backend python scripts/provision_local_service_accounts.py
        \tuv run --locked --extra dev --extra backend python scripts/warm_seeded_post_content.py
        '''
    )
    if old_seed not in makefile:
        raise RuntimeError("Makefile seed block drifted")
    MAKEFILE.write_text(makefile.replace(old_seed, new_seed, 1), encoding="utf-8")

    makefile_contract = MAKEFILE_CONTRACT.read_text(encoding="utf-8")
    old_count = "assert makefile.count('KEYCLOAK_CLIENT_SECRET is required') == 3"
    new_count = "assert makefile.count('KEYCLOAK_CLIENT_SECRET is required') == 4"
    if old_count not in makefile_contract:
        raise RuntimeError("Makefile secret-count contract drifted")
    MAKEFILE_CONTRACT.write_text(
        makefile_contract.replace(old_count, new_count, 1), encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("contract", "repair"))
    args = parser.parse_args()
    if args.mode == "contract":
        write_contract()
    else:
        apply_repair()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
