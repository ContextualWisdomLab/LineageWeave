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
re-processed or re-stored twice.

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
- **"Has this exact image already been processed?"**: `SELECT ... FROM
  embedded_image WHERE embedded_image_id = sha256(new_image_bytes)` --
  idempotent by construction, no duplicate vision-provider calls for a
  picture that recurs across documents (a common shape for letterhead
  logos, signature images, etc.).
