"""Direct branch tests for fixture cast, commit clock, and vision compression.

The end-to-end suites exercise fixtures and vision images only on the
happy path. These tests drive the remaining branches: the A-100 / B-200 /
unknown fixture casts, the calendar commitment clock helper, and the
bounded-JPEG re-encode loop that steps quality and resizes an oversized
image until it fits the vision payload ceiling.
"""

from __future__ import annotations

import io

from PIL import Image

from lineageweave.fixtures import (
    calendar_commitment_occurred_at,
    fixture_thread_cast,
)
from lineageweave.vision_image import _MAX_VISION_IMAGE_BYTES, _encode_bounded_jpeg


def _alpha_title() -> str:
    from lineageweave.fixtures import sample_records

    return next(
        record.label
        for record in sample_records()
        if record.secondary_key == "proj-alpha"
    )


def _beta_title() -> str:
    from lineageweave.fixtures import sample_records

    return next(
        record.label
        for record in sample_records()
        if record.secondary_key == "proj-beta"
    )


def test_fixture_thread_cast_alpha_and_beta_and_unknown() -> None:
    alpha_cast = fixture_thread_cast(_alpha_title())
    assert alpha_cast is not None
    assert alpha_cast.organization_name == "Northridge Grid"
    assert alpha_cast.person_names == ("Ada West", "Priya Nair")

    beta_cast = fixture_thread_cast(_beta_title())
    assert beta_cast is not None
    assert beta_cast.organization_name == "Westfield Power"
    assert beta_cast.person_names == ("Jordan Hale",)

    assert fixture_thread_cast("A completely unknown title") is None


def test_calendar_commitment_occurred_at_is_a_positive_iso_week_date() -> None:
    value = calendar_commitment_occurred_at()
    assert value.year == 2026
    assert value.month == 1


def test_bounded_jpeg_encodes_a_tiny_image_directly() -> None:
    image = Image.new("RGB", (8, 8), color=(120, 40, 200))
    payload = _encode_bounded_jpeg(image)
    assert len(payload) <= _MAX_VISION_IMAGE_BYTES
    with Image.open(io.BytesIO(payload)) as decoded:
        assert decoded.format == "JPEG"


def test_bounded_jpeg_compresses_an_oversized_image_to_fit() -> None:
    # A huge, high-entropy image never fits at any JPEG quality, forcing
    # the quality-step loop AND the resize fallback before it returns.
    import random

    image = Image.new("RGB", (6000, 6000))
    random.seed(7)
    pixels = image.load()
    for y in range(0, 6000, 2):
        for x in range(0, 6000, 2):
            pixels[x, y] = (random.randrange(256), random.randrange(256), random.randrange(256))
    payload = _encode_bounded_jpeg(image)
    assert len(payload) <= _MAX_VISION_IMAGE_BYTES
    with Image.open(io.BytesIO(payload)) as decoded:
        w, h = decoded.size
        # The resize loop must have shrunk it below the original bounds.
        assert w < 6000 and h < 6000
        assert decoded.format == "JPEG"


def test_bounded_jpeg_resize_fallback_preserves_a_tiny_image() -> None:
    image = Image.new("RGB", (1, 1), color=(10, 20, 30))
    payload = _encode_bounded_jpeg(image)
    assert len(payload) <= _MAX_VISION_IMAGE_BYTES
    with Image.open(io.BytesIO(payload)) as decoded:
        assert decoded.size == (1, 1)

def test_ambiguous_fixture_posts_are_nonempty_and_refer_synthetic_people() -> None:
    """Both ambiguity fixtures stay demo-safe and reference real names."""
    from lineageweave.fixtures import (
        ambiguous_entity_relationship_post,
        ambiguous_keyman_post,
    )

    keyman_title, keyman_body = ambiguous_keyman_post()
    assert keyman_title and keyman_body
    assert "Priya" in keyman_body and "Jordan Hale" in keyman_body

    rel_title, rel_body, org_names = ambiguous_entity_relationship_post()
    assert rel_title and rel_body
    assert "Meridian Utilities" in org_names and "Colby Insulation" in org_names
