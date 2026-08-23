# Local demo CalDAV source for docker-compose

- Add a `caldav-demo` compose service (`docker/caldav-demo`) serving a static
  `GET /events` fixture, so a fresh `docker compose up` shows a connected
  Calendar workspace instead of "CalDAV is not connected" (ADR 0145).
- `backend`'s `CALDAV_BASE_URL` now defaults to the new service instead of
  empty; set it explicitly to point at a real CalDAV source (Naruon, once
  it ships its provider endpoint, or any other bridge) instead.
