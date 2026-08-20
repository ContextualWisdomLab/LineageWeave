# ADR 0055: Board project evidence projection

## Status

Accepted

## Context

Project identity may be absent from the imported project fields while a stored
semantic project mention still explains why a post matches a search. Showing
only the title and body in the board hides that distinction and forces buyers
to open every result before understanding the match.

## Decision

- Include at most five stored `post_project_mention` rows in each authorized
  board post projection, ordered by confidence and then stable project keys.
- Preserve project name, evidence text, confidence, ontology IRI, extraction
  method, resolution status, and provenance in the projection.
- Keep explicit `source_project_code` and `source_project_name` separate from
  semantic candidates; neither is upgraded to a confirmed project identity.
- Do not run an LLM while listing posts. Only persisted semantic evidence is
  projected; missing evidence remains missing.

## Consequences

Search results can expose both the source-field hint and the evidence-backed
semantic project without opening the record. The board remains bounded, and
the detail view remains the full evidence surface.
