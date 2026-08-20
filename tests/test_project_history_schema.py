"""Static integration locks for the project lifecycle feature."""

from pathlib import Path
import re

_ROOT = Path(__file__).resolve().parents[1]


def test_project_history_schema_is_third_normal_form_and_replayable() -> None:
    migration = (_ROOT / "migrations/0050_project_history_lifecycle.sql").read_text()
    rollback = (_ROOT / "migrations/rollback/0050_project_history_lifecycle.sql").read_text()
    dockerfile = (_ROOT / "docker/postgres-init/Dockerfile").read_text()
    migrate = (_ROOT / "docker/postgres-init/migrate.sh").read_text()
    makefile = (_ROOT / "Makefile").read_text()

    for table_name in (
        "project_history_project",
        "project_history_event",
        "project_event_relation",
        "project_responsibility_assignment",
    ):
        assert f"create table if not exists {table_name}" in migration
        assert len(table_name.split("_")) >= 2

    event_table = migration.split("create table if not exists project_history_event", 1)[1].split(
        "create index", 1
    )[0]
    assignment_table = migration.split(
        "create table if not exists project_responsibility_assignment", 1
    )[1].split("create index", 1)[0]
    assert "project_name" not in event_table
    assert "project_name" not in assignment_table
    assert "references project_history_project (project_key)" in event_table
    assert "references project_history_project (project_key)" in assignment_table
    assert "validate_project_event_relation_scope" in migration
    assert "evidence_post_id uuid not null references source_post" in migration
    assert "0050_project_history_lifecycle.sql" in dockerfile
    assert "0050_*" in migrate
    assert "scripts/seed_project_history.py" in makefile
    assert "drop table if exists project_history_project" in rollback


def test_project_history_api_and_buyer_surface_are_wired() -> None:
    main = (_ROOT / "backend/app/main.py").read_text()
    api = (_ROOT / "frontend/src/api.ts").read_text()
    app = (_ROOT / "frontend/src/App.tsx").read_text()

    assert "from backend.app.project_history import fetch_project_history" in main
    assert '@app.get("/api/projects/{project_key}/history")' in main
    assert "fetch_project_history(" in main
    assert "export interface ProjectHistory" in api
    assert "export function fetchProjectHistory" in api
    assert 'import { ProjectHistoryPanel } from "./components/ProjectHistoryTimeline";' in app
    assert re.search(r"<ProjectHistoryPanel[\s\S]+projectEvidence=", app)
