# ADR 0031 — Embedded images use an HTML parser and a raster allowlist

**Decision status:** Accepted
**Date:** 2026-08-17

## Context

The product popup stopped dumping a well-formed
`data:image/png;base64,...` invoice as a base64 wall. The splitter and
`extract_base64_images` still used a `[^>]*` regex. Real invoice HTML
puts `>` inside `alt` or `title` *before* `src`. That shape is legal
HTML (WHATWG, n.d.) and is what `chunk_by_dom` already parses. The regex
missed the picture and put the payload back into the text node.

The same open MIME class `image/[a-zA-Z0-9.+-]+` accepted
`image/svg+xml`. SVG-as-`<img>` does not run script in current browsers,
but the regex also fed the vision channel. `atob` and
`b64decode(validate=True)` already disagreed on padding.

ADR 0019 is the R&R catalog-identity decision. This decision is the
viewer/extractor parse contract. Layout clues stay as character offsets
and `chunk_position` rows — never raw HTML in the knowledge graph or in
a persisted post body.

Persistence of OCR under the figure (Li et al., 2023; Radford et al.,
2021) is still the next buyer slice. It must not land on a splitter that
fails the HTML the buyer actually opens.

## Decision

The popup (`splitPostBody`), `extract_base64_images`, and `chunk_by_dom`
share one decode helper (`lineageweave.embedded_image_payload`):

1. Parse with an HTML parser (`DOMParser` in the browser, `html.parser`
   in Python). Comments, `<style>`, and `<script>` do not yield images.
2. Accept only raster MIME types: `png`, `jpeg`/`jpg`, `gif`, `webp`,
   `avif`. Reject SVG and non-image labels.
3. Require strict base64 padding and a matching magic-byte signature
   (Boutell & Randers-Pehrson, 2003, for PNG).
4. Never fall back to the raw `post_body` when every tag strips away.
   Tell the operator to re-export.
5. Lock the contract with
   `tests/fixtures/synthetic_invoice_embedded_image.html` — the same
   file the TypeScript and Python tests read.

`GET /api/posts/{id}` still returns raw `post_body`. Vision captions
stay on Extract Keyman / Ask until a later persistence PR.

## Consequences

- Open a post whose invoice HTML has `alt="Invoice > 1000"`. You see
  the picture and the surrounding sentences. The raw base64 string is gone.
- An SVG or a remote `https://` image is not loaded. Re-export as an
  embedded PNG or JPEG and open the post again.
- A commented-out `<img>` or a CSS `background:url(data:image/...)`
  does not appear as a picture and does not leak into the text.

## References

Boutell, T., & Randers-Pehrson, G. (Eds.). (2003). *Portable Network
Graphics (PNG) specification (second edition)*. World Wide Web
Consortium. https://www.w3.org/TR/2003/REC-PNG-20031110/

Li, M., Lv, T., Chen, J., Cui, L., Lu, Y., Florencio, D., Zhang, C.,
Li, Z., & Wei, F. (2023). TrOCR: Transformer-based optical character
recognition with pre-trained models. *Proceedings of the AAAI
Conference on Artificial Intelligence, 37*(11), 13094–13102.
https://doi.org/10.1609/aaai.v37i11.26538

Radford, A., Kim, J. W., Hallacy, C., Ramesh, A., Goh, G., Agarwal, S.,
Sastry, G., Askell, A., Mishkin, P., Clark, J., Krueger, G., &
Sutskever, I. (2021). Learning transferable visual models from natural
language supervision. In M. Meila & T. Zhang (Eds.), *Proceedings of
the 38th International Conference on Machine Learning* (pp. 8748–8763).
PMLR. https://proceedings.mlr.press/v139/radford21a.html

WHATWG. (n.d.). *HTML living standard*.
https://html.spec.whatwg.org/multipage/
