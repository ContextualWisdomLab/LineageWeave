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


def test_extract_base64_images_keeps_remote_image_policy_with_quoted_greater_than() -> None:
    html = '<img alt="a > b" src="https://example.com/photo.png">'

    assert extract_base64_images(html) == []
