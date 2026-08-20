"""Harden TEPP transport and temporal-only claim acceptance on PR #282."""

from __future__ import annotations

from pathlib import Path

TARGET = Path("lineageweave/tepp_project_history.py")


def main() -> None:
    """Patch the endpoint resolver and reject positively causal finding prose."""
    source = TARGET.read_text(encoding="utf-8")
    if "from ipaddress import ip_address\n" not in source:
        anchor = "from dataclasses import dataclass\n"
        if anchor not in source:
            raise SystemExit("project-history dataclass import anchor drifted")
        source = source.replace(
            anchor,
            "from ipaddress import ip_address\n\n" + anchor,
            1,
        )

    start = source.find("def project_history_endpoint(transport_url: str) -> str:\n")
    end = source.find("\n\nTransport =", start)
    if start < 0 or end < 0:
        raise SystemExit("project-history endpoint resolver anchor drifted")
    replacement = '''def _hostname_is_loopback(hostname: str) -> bool:\n    """Return whether a parsed hostname is local-only."""\n    if hostname.casefold() == "localhost":\n        return True\n    try:\n        return ip_address(hostname).is_loopback\n    except ValueError:\n        return False\n\n\ndef project_history_endpoint(transport_url: str) -> str:\n    """Resolve TEPP's history path, requiring TLS except for loopback HTTP.\n\n    TEPP's current embedded live service binds only to loopback HTTP. Production\n    and every non-loopback endpoint remain HTTPS-only. Credentials, fragments,\n    query strings, malformed ports, control characters, and unrelated paths are\n    rejected before any network request is attempted.\n    """\n    candidate = transport_url.strip()\n    if not candidate:\n        raise TeppProjectHistoryUnavailable("TEPP project-history transport is not configured")\n    if any(ord(character) < 0x20 for character in candidate):\n        raise TeppProjectHistoryUnavailable("TEPP project-history URL contains a control character")\n    parsed = urlsplit(candidate)\n    try:\n        _ = parsed.port\n    except ValueError as exc:\n        raise TeppProjectHistoryUnavailable("TEPP project-history URL has an invalid port") from exc\n    hostname = parsed.hostname\n    if (\n        not hostname\n        or parsed.username is not None\n        or parsed.password is not None\n        or parsed.query\n        or parsed.fragment\n    ):\n        raise TeppProjectHistoryUnavailable("TEPP project-history URL is not a clean service origin")\n    remote_tls = parsed.scheme == "https"\n    local_http = parsed.scheme == "http" and _hostname_is_loopback(hostname)\n    if not (remote_tls or local_http):\n        raise TeppProjectHistoryUnavailable(\n            "TEPP project-history URL must use HTTPS or loopback-only HTTP"\n        )\n    path = parsed.path.rstrip("/")\n    if path.endswith("/v1/analysis-runs"):\n        path = path[: -len("/v1/analysis-runs")]\n    elif path and path != "/":\n        raise TeppProjectHistoryUnavailable("TEPP transport URL has an unsupported path")\n    return urlunsplit((parsed.scheme, parsed.netloc, f"{path}{PROJECT_HISTORY_PATH}", "", ""))\n'''
    source = source[:start] + replacement + source[end:]

    old_boundary = '''        if "temporal association" not in lowered_summary or "causal" not in lowered_summary:\n            raise TeppProjectHistoryUnavailable("finding summary omitted temporal/non-causal boundary")\n'''
    new_boundary = '''        if (\n            "temporal association" not in lowered_summary\n            or "not a causal conclusion" not in lowered_summary\n        ):\n            raise TeppProjectHistoryUnavailable("finding summary omitted temporal/non-causal boundary")\n'''
    if new_boundary not in source:
        if source.count(old_boundary) != 1:
            raise SystemExit("project-history claim-boundary anchor drifted")
        source = source.replace(old_boundary, new_boundary, 1)

    TARGET.write_text(source, encoding="utf-8")


if __name__ == "__main__":
    main()
