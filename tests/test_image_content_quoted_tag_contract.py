from __future__ import annotations

import base64

from lineageweave.image_content import EmbeddedImage, extract_base64_images


_TINY_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def test_extract_base64_images_preserves_quoted_greater_than_before_src() -> None:
    html = (
        f'<p>before</p><img alt="a > b" '
        f'src="data:image/png;base64,{_TINY_PNG_B64}"><p>after</p>'
    )

    assert extract_base64_images(html) == [
        EmbeddedImage(
            position=html.index("<img"),
            mime_type="image/png",
            data=base64.b64decode(_TINY_PNG_B64),
        )
    ]


def test_extract_base64_images_preserves_character_offset_across_lines() -> None:
    html = (
        "<p>before</p>\n"
        f'<div>evidence</div>\n<img alt="a > b" '
        f'src="data:image/png;base64,{_TINY_PNG_B64}">'
    )

    images = extract_base64_images(html)

    assert len(images) == 1
    assert images[0].position == html.index("<img")
    assert images[0].data == base64.b64decode(_TINY_PNG_B64)


def test_extract_base64_images_accepts_case_insensitive_self_closing_img() -> None:
    html = f'<IMG ALT="a > b" SRC="data:image/png;base64,{_TINY_PNG_B64}" />'

    images = extract_base64_images(html)

    assert len(images) == 1
    assert images[0].position == 0
    assert images[0].mime_type == "image/png"


def test_extract_base64_images_keeps_remote_image_policy_with_quoted_greater_than() -> None:
    html = '<img alt="a > b" src="https://example.com/photo.png">'

    assert extract_base64_images(html) == []


def test_extract_base64_images_ignores_missing_or_valueless_src() -> None:
    assert extract_base64_images('<p>text</p><img><img src>') == []


def test_extract_base64_images_skips_alphabet_valid_but_undecodable_base64() -> None:
    assert extract_base64_images('<img src="data:image/png;base64,A">') == []
