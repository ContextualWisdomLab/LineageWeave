# ADR 0059: Surface unknown publication state without fail-closed navigation

## Status

Accepted; complements ADR 0058

## Context

Legacy target rows may predate the publication-state gate and therefore have
neither a draft marker nor a deletion marker. Hiding every such row would turn
the board into a fail-closed screen and remove the evidence surface the buyer
needs. Treating those rows as published would be an unsupported claim.

## Decision

- The board keeps authorized legacy rows navigable, but labels them
  `publication_state_unknown`.
- A raw draft marker is exposed as `source_draft_marker` and a raw deletion
  marker as `source_deletion_marker`; neither is translated into a stronger
  lifecycle claim without a source dictionary.
- The UI renders the state beside the body preview in every board card and
  keeps the raw source markers in the detail evidence panel.
- Search and related-post navigation may locate an unknown-state row, but no
  workflow may describe it as published or use it as publication evidence.

## Consequences

Buyers can continue to inspect and trace legacy evidence while seeing exactly
what the source lifecycle contract does and does not prove. Once a governed
source dictionary is supplied, the raw states can be mapped to eligible
publication states without changing the board's evidence boundary.
