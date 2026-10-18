"""Keep the locked HTTP dependency above its released security repair."""

from pathlib import Path
import tomllib


def test_locked_urllib3_excludes_affected_release() -> None:
    """Upstream 2.8.0 repairs proxy TLS, chunk buffering, and deflate loops."""
    lock = tomllib.loads(
        (Path(__file__).resolve().parents[1] / "uv.lock").read_text()
    )
    package = next(item for item in lock["package"] if item["name"] == "urllib3")
    version = tuple(int(part) for part in package["version"].split("."))
    assert version >= (2, 8, 0), (
        "GHSA-8988-9cw3-xx77, GHSA-vxq7-64xx-v4gw, and GHSA-gh4c-6fx4-qh6g "
        "require the upstream urllib3 2.8.0 security repair"
    )
