# Analysis-run provenance and temporal evidence references

This doctoring note records the sources used by ADR 0013 and the Milestone 2
analysis-run contract. Product code implements only the bounded provenance and
no-future-information gates described in the ADR; it does not claim to
implement every construct in these standards or the complete TEPP research
program.

## Product and ecosystem sources

ContextualWisdomLab. (2026a). *Temporal Event Psychometrics Platform: Product
requirements document v0.4 approved baseline* [Product requirements document].
https://github.com/ContextualWisdomLab/TEPP

ContextualWisdomLab. (2026b). *ADR 0017: Language-agnostic semantic-span and
embedding-budget authority* [Architecture decision record].
https://github.com/ContextualWisdomLab/TEPP/blob/2294451d7827c3da47099f2593614c4964ec2e41/docs/adr/0017-language-agnostic-semantic-span-budgeting.md

ContextualWisdomLab. (2026c). *Contextual Orchestrator architecture and product
requirements* [Software documentation].
https://github.com/ContextualWisdomLab/contextual-orchestrator

## Standards

Cox, S., & Little, C. (Eds.). (2022). *Time ontology in OWL* (Candidate
Recommendation Draft). World Wide Web Consortium.
https://www.w3.org/TR/owl-time/

Lebo, T., Sahoo, S., & McGuinness, D. (Eds.). (2013). *PROV-O: The PROV
ontology*. World Wide Web Consortium. https://www.w3.org/TR/prov-o/

Moreau, L., & Missier, P. (Eds.). (2013). *PROV-DM: The PROV data model*.
World Wide Web Consortium. https://www.w3.org/TR/prov-dm/

OpenAPI Initiative. (2025). *OpenAPI specification (Version 3.2.0)*.
https://spec.openapis.org/oas/v3.2.0.html

## Decision traceability

| Contract decision | Source basis |
|---|---|
| One product derivation links source, run, service calls, and artifacts | PROV-DM; PROV-O |
| Occurrence and recording timestamps remain distinct | PROV-O generation/activity timing; TEPP multi-clock baseline |
| `maximum_available_time <= knowledge_cutoff` | Accepted TEPP temporal leakage contract |
| TEPP evidence authority is separate from LineageWeave product state | TEPP modular MSA and semantic-span ADRs |
| API output is a versioned source-redacting projection | OpenAPI 3.2.0; ADR 0013 security boundary |
| Exact source and request digests identify immutable evidence | PROV-O entity specialization; TEPP immutable evidence contract |

## Scope note

The product uses OWL-Time's instant/interval vocabulary and alignment with
PROV-O as a documented semantic reference. Database acceptance relies on
explicit PostgreSQL timestamps and constraints, not on an unsupported claim
that the complete OWL-Time ontology is implemented here. TEPP ADR 0017 remains
proposed at the cited exact commit; this LineageWeave slice records a compatible
boundary without presenting the future TEPP implementation as available.
