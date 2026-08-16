# DB design: searchable, position-preserving image content

**Status:** proposed schema, not yet backed by a persistence layer in this
repo (LineageWeave's own demo server is in-memory/stdlib -- this document
is the design a real deployment's persistence layer should implement).
All object names are snake_case, two or more words, per this project's
naming convention.

## Why this needs its own tables, not just a text column

Base64 images live inside a source document's DOM at a specific point --
"the invoice number was in the picture right after the third paragraph."
If extracted OCR text and tags are stored disconnected from that position,
a search hit tells you *that* something matched but not *where* in the
original document to look, and there is no way to reconstruct the
document's original visual layout (text, then a picture, then more text)
for review. The design below keeps three things independently true at
once: (1) the extracted text and tags are searchable on their own terms,
(2) each image stays traceable to exactly which document and which
position produced it, and (3) the same image (by content hash) is never
*stored* twice -- `embedded_image_id`'s primary key guarantees that part
by construction. Avoiding a duplicate *vision-provider call* for two
concurrent ingests of the same new image is a separate concern this
schema does not solve on its own (see the query-shapes note below) --
that needs an atomic claim/lease step in the write path, not just the
content-hash primary key.

## Tables

### `source_document`

One row per document that may contain embedded images (an MHTML/HTML
artifact, an ingested email, etc.). Referenced by whatever this project's
`Record.record_id` maps to in a real deployment -- not redefined here to
avoid coupling this schema to one specific source system.

| Column | Type | Notes |
|---|---|---|
| `source_document_id` | `text` primary key | opaque id, matches the owning record |
| `content_sha256` | `text not null` | hash of the full source document, for idempotent re-ingest |
| `ingested_at` | `timestamptz not null default now()` | |

### `embedded_image`

One row per distinct image (by content hash), decoupled from *where* it
appeared -- the same picture can appear in more than one document.

| Column | Type | Notes |
|---|---|---|
| `embedded_image_id` | `text primary key` | `sha256(image_bytes)`, so identical images across documents are stored once |
| `mime_type` | `text not null` | e.g. `image/png` |
| `byte_size` | `bigint not null` | |
| `extracted_text` | `text` | OCR result (Li et al., 2023 -- TrOCR-family text recognition); `null` until processed, empty string if genuinely no legible text |
| `caption_text` | `text` | one-sentence description (Radford et al., 2021 -- CLIP-family vision-language grounding) |
| `processed_at` | `timestamptz` | `null` until a vision client has run; distinguishes "not yet processed" from "processed, nothing found" |
| `processing_model` | `text` | which vision-capable model produced `extracted_text`/`caption_text`, for auditability if a model change should trigger reprocessing |

### `image_tag`

Many-to-many: independently searchable keyword tags per image, separate
from the free-text caption.

| Column | Type | Notes |
|---|---|---|
| `embedded_image_id` | `text not null references embedded_image` | |
| `tag_text` | `text not null` | a single short tag |
| primary key | `(embedded_image_id, tag_text)` | |

### `document_image_position`

The position-preserving join: which image appeared in which document, at
which position among that document's other content units (text and image
chunks together, true document order -- see
`lineageweave.chunking.chunk_by_dom`'s unified sequence). This is what
lets a UI reconstruct "here is the document, and here is where the
picture sat relative to the surrounding paragraphs."

| Column | Type | Notes |
|---|---|---|
| `source_document_id` | `text not null references source_document` | |
| `embedded_image_id` | `text not null references embedded_image` | |
| `chunk_position` | `integer not null` | 0-based index among ALL of this document's chunks (text and image together) -- matches `Chunk.index` from `chunk_by_dom` |
| primary key | `(source_document_id, chunk_position)` | one image slot per position per document |

## Viewer contract (before persistence exists)

The demo popup does not yet read these tables. It splits the live
`post_body` the same way `extract_base64_images` does: each
`data:image/...;base64,...` payload becomes an `<img>` at its original
character offset, and the surrounding HTML is shown as text. Quoted or
unquoted `src` and optional data-URI parameters such as `charset=utf-8`
are accepted so a real export still shows the picture. A buyer who
opens the post sees the picture that sat between the paragraphs, not the
base64 wall. Remote `src="https://..."` tags are stripped, never fetched;
a remote-only body tells the operator to re-export with the picture
embedded. Undecodable payloads say the same. This screen does not read
text inside the picture. OCR, caption, and tag search still require the
vision client on extract / Ask (Li et al., 2023; Radford et al., 2021)
and, in a real deployment, the tables below. See
`docs/doctoring/IMAGE_CONTENT_REFERENCES.md`.

## Query shapes this supports

- **"Find images whose extracted text or tags match a search query, then
  show me the document and where the image sat"**: search
  `embedded_image.extracted_text` / `image_tag.tag_text`, join through
  `document_image_position` to `source_document`, order surrounding
  content by `chunk_position`.
- **"Reconstruct document N's original layout"**: fetch all of document
  N's text chunks (however the caller's own text-chunk storage models
  them) and `document_image_position` rows for that document, merge-sort
  by `chunk_position` -- text and images interleave back into their
  original order.
- **"Has this exact image already been stored?"**: `SELECT ... FROM
  embedded_image WHERE embedded_image_id = sha256(new_image_bytes)` --
  storage is idempotent by construction (the primary key), a genuinely
  useful guard against re-storing a picture that recurs across documents
  (a common shape for letterhead logos, signature images, etc.). This
  check alone does not prevent two concurrent ingests of the same *new*
  image from both calling the vision provider before either has written
  its row -- a real write path needs an atomic claim (e.g. `INSERT ...
  ON CONFLICT DO NOTHING` before the provider call, or a short-lived
  lease row) to close that race; this schema documents the storage
  guarantee, not that concurrency control.

## References

Li, M., Lv, T., Chen, J., Cui, L., Lu, Y., Florencio, D., Zhang, C., Li, Z.,
& Wei, F. (2023). TrOCR: Transformer-based optical character recognition
with pre-trained models. *Proceedings of the AAAI Conference on Artificial
Intelligence, 37*(11), 13094–13102. https://doi.org/10.1609/aaai.v37i11.26538

Radford, A., Kim, J. W., Hallacy, C., Ramesh, A., Goh, G., Agarwal, S.,
Sastry, G., Askell, A., Mishkin, P., Clark, J., Krueger, G., & Sutskever, I.
(2021). Learning transferable visual models from natural language
supervision. In M. Meila & T. Zhang (Eds.), *Proceedings of the 38th
International Conference on Machine Learning* (pp. 8748–8763). PMLR.
https://proceedings.mlr.press/v139/radford21a.html
