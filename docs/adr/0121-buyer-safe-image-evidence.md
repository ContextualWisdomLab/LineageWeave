# ADR 0121: Keep Internal Image Instructions Out of Buyer Evidence

## Status

Accepted

## Context

VISION analysis may receive or inherit an internal instruction such as
`This post is an image. Ask questions to read its text.` or its Korean
equivalent. That text is an agent instruction, not a caption describing the
source image. Persisted legacy content can still contain it even after the
prompt is corrected.

## Decision

At the image and visual-region evidence boundary, normalize captions and suppress captions that
match the known internal instruction forms. Apply the same rule when creating
LLM/embedding placeholders and when rendering the buyer-facing post body.
Retain the original image, OCR text, tags, region coordinates, and provenance;
only the non-evidence caption is removed. If no useful caption remains, show
the image and available evidence without inventing a description.

The instruction matcher uses concrete imperative phrases for Korean text
extraction guidance rather than ordinary words such as `텍스트` or `질문`, so
legitimate captions that describe an image containing text remain evidence.

The configured Vision destination is also a trust boundary. The client rejects
credential-bearing URLs, invalid ports, loopback/private/link-local/reserved
IP literals, and known local or cloud-metadata hostnames even when local HTTP
is explicitly enabled. Compose uses the service name `orchestrator` for its
local HTTP route; a caller cannot opt into an internal IP destination by
setting `allow_insecure_http`.

Vision parse failures and unexpected provider failures are also trust-boundary
events. Their raw response or exception text is never returned in an API
payload or persisted as post-content detail; the product exposes a stable
unavailable message and schedules a retry where applicable.

## Consequences

- Buyer screens cannot expose the analysis agent's instruction as post content.
- Existing persisted image rows are safe immediately; re-ingestion is not
  required merely to hide the legacy caption.
- OCR, region evidence, and semantic search remain available.
- New provider-specific instruction variants require an explicit, reviewed
  pattern and a regression test rather than a broad caption guess.
- A malformed or attacker-controlled Vision endpoint fails closed at client
  construction, before an API key or image payload is sent.
- A malformed provider response cannot disclose gateway diagnostics through a
  buyer-facing error or durable ingestion record.

## References — APA 7th

MITRE. (2026). *CWE-209: Generation of error message containing sensitive
information*. https://cwe.mitre.org/data/definitions/209.html

National Institute of Standards and Technology. (2020). *Security and privacy
controls for information systems and organizations* (NIST Special Publication
800-53 Rev. 5). https://doi.org/10.6028/NIST.SP.800-53r5
