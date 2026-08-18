"""CalDAV consume stays fail-closed. No invented events."""

from lineageweave.caldav_client import (
    CALDAV_UNAVAILABLE_NEXT_ACTION,
    NullCalDavClient,
    build_caldav_client,
)


def test_empty_caldav_url_does_not_plant_a_server() -> None:
    client = build_caldav_client("")
    assert isinstance(client, NullCalDavClient)
    assert client.available is False
    assert client.list_events() == ()


def test_null_client_does_not_invent_events() -> None:
    assert NullCalDavClient().list_events() == ()
    assert CALDAV_UNAVAILABLE_NEXT_ACTION == "이 범위의 일정을 아직 받을 수 없습니다"
