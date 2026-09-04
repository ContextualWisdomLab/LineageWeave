"""Architecture fitness for external calendar authority boundaries."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_obsolete_direct_caldav_adapter_and_configuration_are_absent() -> None:
    """LineageWeave must not retain a direct pseudo-CalDAV provider boundary."""
    assert not (ROOT / "lineageweave" / "caldav_client.py").exists()
    assert not (ROOT / "tests" / "test_caldav_client.py").exists()

    config_source = (ROOT / "backend" / "app" / "config.py").read_text(encoding="utf-8")
    main_source = (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    compose_source = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "caldav_base_url" not in config_source
    assert "CALDAV_BASE_URL" not in config_source
    assert "lineageweave.caldav_client" not in main_source
    assert "CALDAV_UNAVAILABLE_NEXT_ACTION" not in main_source
    assert "build_caldav_client" not in main_source
    assert "\nCALDAV_BASE_URL=" not in env_example
    assert "CALDAV_BASE_URL:" not in compose_source

    # The versioned consumer/ACL remains explicit while the provider authority stays external.
    assert "NARUON_CALENDAR_BASE_URL" in config_source
    assert "NARUON_CALENDAR_SERVICE_TOKEN" in config_source
