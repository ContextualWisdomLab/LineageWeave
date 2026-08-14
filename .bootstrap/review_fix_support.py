from __future__ import annotations

import re
from pathlib import Path
from textwrap import dedent


def read(path: str) -> str:
    return Path(path).read_text()


def write(path: str, content: str) -> None:
    Path(path).write_text(content.rstrip() + "\n")


def replace_all(path: str, replacements: dict[str, str]) -> None:
    text = read(path)
    for old, new in replacements.items():
        text = text.replace(old, new)
    write(path, text)


# ---------------------------------------------------------------------------
# Database constraints and indexes
# ---------------------------------------------------------------------------
path = "migrations/0001_initial_schema.sql"
text = read(path)
text = text.replace(
    "    unique (team_name, affiliated_organization_name)\n);",
    "    unique nulls not distinct (team_name, affiliated_organization_name)\n);",
    1,
)
text = text.replace(
    "create index person_affiliation_person_idx on person_affiliation (person_id);",
    "create index person_affiliation_person_idx on person_affiliation (person_id);\n"
    "create index person_affiliation_corporate_entity_idx\n"
    "    on person_affiliation (affiliated_corporate_entity_id)\n"
    "    where affiliated_corporate_entity_id is not null;",
    1,
)
text = text.replace(
    "create table post_team_mention (",
    "create index cataloged_team_corporate_entity_idx\n"
    "    on cataloged_team (affiliated_corporate_entity_id)\n"
    "    where affiliated_corporate_entity_id is not null;\n\n"
    "create table post_team_mention (",
    1,
)
write(path, text)

path = "migrations/0016_cross_post_actor_identity.sql"
text = read(path)
text = text.replace(
    "    -- deduplicated by this constraint (standard SQL NULL semantics) --\n"
    "    -- the application layer checks for an existing NULL-org row before\n"
    "    -- inserting, so this is a backup, not the only guard.\n"
    "    unique (team_name, affiliated_organization_name)",
    "    -- deduplicated by the database itself, including NULL affiliation.\n"
    "    unique nulls not distinct (team_name, affiliated_organization_name)",
    1,
)
if "cataloged_team_corporate_entity_idx" not in text:
    text = text.replace(
        ");\n\ncreate table if not exists post_team_mention",
        ");\n\ncreate index if not exists cataloged_team_corporate_entity_idx\n"
        "    on cataloged_team (affiliated_corporate_entity_id)\n"
        "    where affiliated_corporate_entity_id is not null;\n\n"
        "create table if not exists post_team_mention",
        1,
    )
lookup_anchor = (
    "insert into common_lookup_value "
    "(lookup_category, lookup_code, lookup_label, display_order) values\n"
)
if "('corporate_entity_level', 'group'" not in text:
    text = text.replace(
        lookup_anchor,
        lookup_anchor
        + "    ('corporate_entity_level', 'group', 'Group', 0),\n"
        + "    ('corporate_entity_level', 'company', 'Company', 1),\n"
        + "    ('corporate_entity_level', 'plant', 'Plant', 2),\n",
        1,
    )
write(path, text)

path = "migrations/0012_role_responsibility_agent_type.sql"
text = read(path)
text = text.replace(
    "        where table_name = 'post_summary_role' and column_name = 'person_name'\n",
    "        where table_schema = 'public'\n"
    "          and table_name = 'post_summary_role'\n"
    "          and column_name = 'person_name'\n",
    1,
)
write(path, text)

# ---------------------------------------------------------------------------
# PROV-O persistence: strict dateTime lexical validation and immutable
# reference rows once an assertion depends on them.
# ---------------------------------------------------------------------------
path = "migrations/0017_prov_o_standard_relations.sql"
text = read(path)
text = text.replace(
    "    required_datatype text;\n",
    "    required_datatype text;\n"
    "    literal_datatype text;\n"
    "    literal_lexical text;\n",
    1,
)
old = dedent(
    '''
        if relation_kind = 'datatype' and required_datatype is not null and not exists (
            select 1
              from provenance_literal_value
             where literal_id = new.object_literal_id
               and datatype_iri = required_datatype
        ) then
            raise exception 'literal % violates datatype % for %',
                new.object_literal_id, required_datatype, new.relation_code;
        end if;
    '''
)
new = dedent(
    '''
        if relation_kind = 'datatype' then
            select datatype_iri, lexical_value
              into literal_datatype, literal_lexical
              from provenance_literal_value
             where literal_id = new.object_literal_id;

            if required_datatype is not null
               and literal_datatype is distinct from required_datatype then
                raise exception 'literal % violates datatype % for %',
                    new.object_literal_id, required_datatype, new.relation_code;
            end if;

            if required_datatype = 'http://www.w3.org/2001/XMLSchema#dateTime' then
                if literal_lexical !~ (
                    '^[0-9]{4}-(0[1-9]|1[0-2])-'
                    '(0[1-9]|[12][0-9]|3[01])T'
                    '([01][0-9]|2[0-3]):[0-5][0-9]:'
                    '[0-5][0-9](\\.[0-9]+)?'
                    '(Z|[+-](0[0-9]|1[0-4]):[0-5][0-9])$'
                ) then
                    raise exception 'literal % violates lexical xsd:dateTime for %',
                        new.object_literal_id, new.relation_code;
                end if;
                begin
                    perform literal_lexical::timestamptz;
                exception when others then
                    raise exception 'literal % violates lexical xsd:dateTime for %',
                        new.object_literal_id, new.relation_code;
                end;
            end if;
        end if;
    '''
)
if old not in text:
    raise SystemExit("PROV datatype validation anchor missing")
text = text.replace(old, new, 1)
anchor = dedent(
    '''
    create trigger provenance_assertion_contract_trigger
    before insert or update on provenance_assertion
    for each row execute function validate_provenance_assertion_contract();

    '''
)
protection = dedent(
    '''
    create trigger provenance_assertion_contract_trigger
    before insert or update on provenance_assertion
    for each row execute function validate_provenance_assertion_contract();

    create or replace function protect_provenance_contract_reference()
    returns trigger
    language plpgsql
    as $$
    begin
        if tg_table_name = 'provenance_resource_type' and exists (
            select 1
              from provenance_assertion
             where subject_resource_id = old.resource_id
                or object_resource_id = old.resource_id
        ) then
            raise exception 'referenced provenance resource types are immutable';
        end if;

        if tg_table_name = 'provenance_literal_value' and exists (
            select 1
              from provenance_assertion
             where object_literal_id = old.literal_id
        ) then
            raise exception 'referenced provenance literal values are immutable';
        end if;
        return old;
    end;
    $$;

    drop trigger if exists provenance_resource_type_reference_trigger
        on provenance_resource_type;
    create trigger provenance_resource_type_reference_trigger
    before update or delete on provenance_resource_type
    for each row execute function protect_provenance_contract_reference();

    drop trigger if exists provenance_literal_value_reference_trigger
        on provenance_literal_value;
    create trigger provenance_literal_value_reference_trigger
    before update or delete on provenance_literal_value
    for each row execute function protect_provenance_contract_reference();

    '''
)
if anchor not in text:
    raise SystemExit("PROV trigger anchor missing")
text = text.replace(anchor, protection, 1)
write(path, text)

# ---------------------------------------------------------------------------
# Parsers, cached constants, UI contrast
# ---------------------------------------------------------------------------
path = "lineageweave/image_content.py"
text = read(path)
old = dedent(
    '''
        fields: dict[str, list[str]] = {"TEXT": [], "CAPTION": [], "TAGS": []}
        current: str | None = None
        for line in content.splitlines():
            match = _LABEL_LINE.match(line)
            if match:
                current = match.group(1).upper()
                remainder = match.group(2).strip()
                if remainder:
                    fields[current].append(remainder)
            elif current is not None and line.strip():
                fields[current].append(line.strip())
    '''
)
new = dedent(
    '''
        fields: dict[str, list[str]] = {"TEXT": [], "CAPTION": [], "TAGS": []}
        current: str | None = None
        for line in content.splitlines():
            match = _LABEL_LINE.match(line)
            if match:
                current = match.group(1).upper()
                remainder = match.group(2).strip()
                if remainder:
                    fields[current].append(remainder)
                continue

            if re.match(r"^\\s*[*_`>#\\-\\s]*[A-Za-z][A-Za-z0-9 _-]*\\s*:", line):
                current = None
                continue
            if current is not None and line.strip():
                fields[current].append(line.strip())
    '''
)
if old not in text:
    raise SystemExit("image parser anchor missing")
write(path, text.replace(old, new, 1))

path = "lineageweave/corporate_hierarchy_inference.py"
text = read(path)
text = text.replace(
    "from dataclasses import dataclass\n",
    "from dataclasses import dataclass\nfrom functools import lru_cache\n",
    1,
)
text = text.replace(
    "_VALID_LEVEL_CODES = frozenset({LEVEL_GROUP, LEVEL_COMPANY, LEVEL_PLANT})\n",
    "_VALID_LEVEL_CODES = frozenset({LEVEL_GROUP, LEVEL_COMPANY, LEVEL_PLANT})\n\n"
    "@lru_cache(maxsize=1)\n"
    "def required_corporate_level_codes() -> frozenset[str]:\n"
    "    \"\"\"Return the level codes every migrated database registers.\"\"\"\n"
    "    return _VALID_LEVEL_CODES\n",
    1,
)
write(path, text)

path = "frontend/src/App.css"
write(path, read(path).replace("  color: #e65100;\n", "  color: #9a3412;\n", 1))

# ---------------------------------------------------------------------------
# De-identify examples and remove operational counts from public history.
# ---------------------------------------------------------------------------
replacements = {
    "한수원": "AGP",
    "한국수력원자력": "Aurora Grid Power",
    "삼성전자 광주공장": "Acme Electronics South Plant",
    "삼성전자 한국": "Acme Electronics Korea",
    "삼성전자": "Acme Electronics",
    "삼성": "Acme Group",
    "real Milestone 2": "synthetic regression corpus",
    "Milestone 2 batch": "synthetic regression batch",
    "(~1% of calls)": "in format-variation fixtures",
    "real embedded images": "synthetic embedded-image fixtures",
    "private real-data batch script": "offline synthetic-batch script",
    "real-data batch script": "offline synthetic-batch script",
    "real dataset": "unseen dataset",
}
for target in (
    "ARCHITECTURE.md",
    "CHANGELOG.md",
    "backend/app/keyman_ingestion.py",
    "backend/tests/test_api.py",
    "tests/test_corporate_hierarchy_inference.py",
    "docs/adr/0008-organization-abbreviation-resolution.md",
    "docs/adr/0010-corporate-hierarchy-auto-creation.md",
    "migrations/0001_initial_schema.sql",
    "lineageweave/corporate_hierarchy_inference.py",
):
    if Path(target).exists():
        replace_all(target, replacements)

path = "CHANGELOG.md"
text = read(path)
text = re.sub(
    r"  gets auto-created into the corporate hierarchy, not left permanently\n"
    r"  unresolved -- confirmed against .*? An LLM proposes a\n",
    "  gets auto-created into the corporate hierarchy, not left permanently\n"
    "  unresolved. Synthetic regression fixtures prove the first-mention gap.\n"
    "  An LLM proposes a\n",
    text,
    count=1,
    flags=re.DOTALL,
)
fixed_note = (
    "- Review hardening verifies complete hierarchy placement, rejects parent\n"
    "  failures and cycles, propagates canonical affiliations, replaces stale\n"
    "  actor projections, enforces atomic team identity, validates timezone-aware\n"
    "  `xsd:dateTime` literals, and protects referenced provenance rows.\n"
)
release_end = text.index("## [0.75.0]")
if fixed_note not in text[:release_end]:
    text = text[:release_end] + "### Fixed\n\n" + fixed_note + "\n" + text[release_end:]
write(path, text)

# Explicitly preserve the Recommendation's warning about broad OWL-RL aids.
path = "docs/PROV_O_IMPLEMENTATION.md"
text = read(path)
note = dedent(
    '''

    ## OWL 2 RL compatibility domains are not universal permissions

    Appendix A also publishes broad `prov:Influence` domains for
    `prov:hadActivity` and `prov:hadRole` as OWL 2 RL compatibility aids.
    The Recommendation explicitly warns that these broad domains must not be
    read as permission to use either property on every Influence. Runtime and
    database validation therefore enforce the normative union members rather
    than weakening the contract.
    '''
)
if "OWL 2 RL compatibility domains are not universal" not in text:
    text = text.rstrip() + note
write(path, text)

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
path = "tests/test_prov_o_schema.py"
text = read(path)
if "from urllib.parse import" not in text:
    text = text.replace(
        "from pathlib import Path\n",
        "from pathlib import Path\nfrom urllib.parse import urlsplit, urlunsplit\n",
        1,
    )
text = text.replace(
    "        database_dsn = _ADMIN_DSN.rsplit(\"/\", 1)[0] + f\"/{database_name}\"\n",
    "        parsed_admin_dsn = urlsplit(_ADMIN_DSN)\n"
    "        database_dsn = urlunsplit(\n"
    "            parsed_admin_dsn._replace(path=f\"/{database_name}\")\n"
    "        )\n",
    1,
)
extra = dedent(
    '''


    def _literal(cursor, lexical_value: str, datatype_iri: str | None) -> str:
        """Insert one RDF literal and return its UUID."""
        cursor.execute(
            "insert into provenance_literal_value (lexical_value, datatype_iri) "
            "values (%s, %s) returning literal_id",
            (lexical_value, datatype_iri),
        )
        return str(cursor.fetchone()[0])


    @pytest.mark.parametrize(
        "lexical_value",
        ("2026-08-14T04:00:00", "not-a-date", "2026-02-31T04:00:00Z"),
    )
    def test_database_rejects_invalid_xsd_datetime(prov_schema_db, lexical_value: str) -> None:
        """Malformed and timezone-less xsd:dateTime values fail closed."""
        with prov_schema_db.cursor() as cursor:
            activity_id = _resource(cursor, "urn:test:strict-time", "prov_activity")
            literal_id = _literal(
                cursor,
                lexical_value,
                "http://www.w3.org/2001/XMLSchema#dateTime",
            )
            with pytest.raises(psycopg2.errors.RaiseException, match="lexical xsd:dateTime"):
                cursor.execute(
                    "insert into provenance_assertion "
                    "(subject_resource_id, relation_code, object_literal_id) "
                    "values (%s, 'prov_started_at_time', %s)",
                    (activity_id, literal_id),
                )
        prov_schema_db.rollback()


    def test_database_accepts_timezone_aware_xsd_datetime(prov_schema_db) -> None:
        """A valid timezone-aware dateTime reaches the assertion store."""
        with prov_schema_db.cursor() as cursor:
            activity_id = _resource(cursor, "urn:test:valid-time", "prov_activity")
            literal_id = _literal(
                cursor,
                "2026-08-14T04:00:00+09:00",
                "http://www.w3.org/2001/XMLSchema#dateTime",
            )
            cursor.execute(
                "insert into provenance_assertion "
                "(subject_resource_id, relation_code, object_literal_id) "
                "values (%s, 'prov_started_at_time', %s)",
                (activity_id, literal_id),
            )
        prov_schema_db.rollback()


    def test_referenced_contract_rows_are_immutable(prov_schema_db) -> None:
        """Reference-table mutation cannot invalidate stored assertions."""
        with prov_schema_db.cursor() as cursor:
            entity_id = _resource(cursor, "urn:test:immutable-entity", "prov_entity")
            activity_id = _resource(cursor, "urn:test:immutable-activity", "prov_activity")
            cursor.execute(
                "insert into provenance_assertion "
                "(subject_resource_id, relation_code, object_resource_id) "
                "values (%s, 'prov_was_generated_by', %s)",
                (entity_id, activity_id),
            )
            with pytest.raises(psycopg2.errors.RaiseException, match="types are immutable"):
                cursor.execute(
                    "delete from provenance_resource_type "
                    "where resource_id = %s and class_code = 'prov_activity'",
                    (activity_id,),
                )
        prov_schema_db.rollback()

        with prov_schema_db.cursor() as cursor:
            activity_id = _resource(cursor, "urn:test:immutable-time", "prov_activity")
            literal_id = _literal(
                cursor,
                "2026-08-14T04:00:00Z",
                "http://www.w3.org/2001/XMLSchema#dateTime",
            )
            cursor.execute(
                "insert into provenance_assertion "
                "(subject_resource_id, relation_code, object_literal_id) "
                "values (%s, 'prov_started_at_time', %s)",
                (activity_id, literal_id),
            )
            with pytest.raises(psycopg2.errors.RaiseException, match="literal values are immutable"):
                cursor.execute(
                    "update provenance_literal_value set datatype_iri = null "
                    "where literal_id = %s",
                    (literal_id,),
                )
        prov_schema_db.rollback()
    '''
)
if "test_database_rejects_invalid_xsd_datetime" not in text:
    text = text.rstrip() + extra
write(path, text)

path = "tests/test_schema.py"
text = read(path)
if "from urllib.parse import" not in text:
    text = text.replace(
        "from pathlib import Path\n",
        "from pathlib import Path\nfrom urllib.parse import urlsplit, urlunsplit\n",
        1,
    )
text = text.replace(
    "        db_dsn = _ADMIN_DSN.rsplit(\"/\", 1)[0] + f\"/{db_name}\"\n",
    "        parsed_admin_dsn = urlsplit(_ADMIN_DSN)\n"
    "        db_dsn = urlunsplit(parsed_admin_dsn._replace(path=f\"/{db_name}\"))\n",
    1,
)
extra = dedent(
    '''


    def test_cataloged_team_null_affiliation_is_unique(schema_db) -> None:
        """Repeated NULL-affiliation upserts return one catalog identity."""
        with schema_db.cursor() as cursor:
            ids = []
            for _ in range(2):
                cursor.execute(
                    "insert into cataloged_team (team_name, affiliated_organization_name) "
                    "values ('Synthetic Design Team', null) "
                    "on conflict (team_name, affiliated_organization_name) do update "
                    "set team_name = excluded.team_name returning team_id"
                )
                ids.append(cursor.fetchone()[0])
            cursor.execute(
                "select count(*) from cataloged_team "
                "where team_name = 'Synthetic Design Team' "
                "and affiliated_organization_name is null"
            )
            count = cursor.fetchone()[0]
        assert ids[0] == ids[1]
        assert count == 1
    '''
)
if "test_cataloged_team_null_affiliation_is_unique" not in text:
    text = text.rstrip() + extra
write(path, text)

path = "tests/test_ontology.py"
text = read(path)
extra = dedent(
    '''


    def test_actor_mentions_follow_stored_edge_direction() -> None:
        """Ontology domain/range matches Team/Organization -> Post storage."""
        graph = _load_graph()
        assert (LW.mentionsTeam, RDFS.domain, LW.Team) in graph
        assert (LW.mentionsTeam, RDFS.range, LW.Post) in graph
        assert (LW.mentionsOrganization, RDFS.domain, LW.CorporateEntity) in graph
        assert (LW.mentionsOrganization, RDFS.range, LW.Post) in graph
    '''
)
if "test_actor_mentions_follow_stored_edge_direction" not in text:
    text = text.rstrip() + extra
write(path, text)

path = "tests/test_image_content.py"
if Path(path).exists():
    text = read(path)
    extra = dedent(
        '''


        def test_parse_description_does_not_absorb_unknown_labels_into_tags() -> None:
            parsed = image_content._parse_description(
                "TEXT: NONE\\nCAPTION: A turbine diagram\\n"
                "TAGS: turbine, diagram\\nNOTE: synthetic"
            )
            assert parsed.tags == ("turbine", "diagram")
        '''
    )
    if "does_not_absorb_unknown_labels_into_tags" not in text:
        text = text.rstrip() + extra
    write(path, text)
