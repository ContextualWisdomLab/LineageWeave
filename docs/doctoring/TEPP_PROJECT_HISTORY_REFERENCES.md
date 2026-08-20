# TEPP project-history references and adoption record

This doctoring note records the standards and research used by the TEPP-backed Buyer project-history surface. The implementation is intentionally conservative: observed event order and provenance may support a **temporal association**, but do not by themselves establish causation, latent-trait estimates, confidence, or a missing lifecycle event.

## Adopted requirements

| Authority | Requirement adopted in LineageWeave |
|---|---|
| ISO 8601-1:2019 and RFC 3339 | Exchange absolute event, availability, and knowledge-cutoff clocks as strict timezone-qualified timestamps; emit canonical UTC `Z` values at the TEPP boundary. |
| W3C Time Ontology in OWL and Allen interval algebra | Keep temporal ordering and interval relations semantically distinct from causal claims. The Buyer projection therefore accepts only `temporal_association_only`. |
| W3C PROV-O / PROV-DM | Retain the source-post identity and availability basis for every event and require every TEPP finding to cite evidence inside the caller-authorized bundle. |
| RFC 8259 | Use a closed, versioned JSON object contract and reject unknown fields, malformed types, duplicate event identities, and references outside the submitted bundle. |
| RFC 9110 | Keep HTTP method, status, content-type, and idempotency semantics explicit. Local modular operation may use loopback HTTP; non-loopback service origins require HTTPS. |
| Allen (1983) | Use deterministic temporal ordering as a qualitative reasoning aid, not as a substitute for causal identification. |

## Product consequences

1. LineageWeave remains the authorization and exact-project evidence selector.
2. TEPP remains the temporal-contract authority and must preserve the supplied evidence verbatim.
3. `available_at <= knowledge_cutoff` is mandatory for every event.
4. A timeline event must open its exact authorized `source_post` evidence.
5. Missing events, actors, project identities, theta, confidence, and causal conclusions are never invented.
6. The same projection contract is reused by post reading, Global Ask, and post-scoped Ask.
7. Browser bearer tokens, review-agent credentials, provider keys, `TEPP_API_KEY`, and database credentials are not forwarded through the project-history request.

## APA 7th references

Allen, J. F. (1983). Maintaining knowledge about temporal intervals. *Communications of the ACM, 26*(11), 832–843. https://doi.org/10.1145/182.358434

Bray, T. (Ed.). (2017). *The JavaScript Object Notation (JSON) data interchange format* (RFC 8259). Internet Engineering Task Force. https://doi.org/10.17487/RFC8259

Cox, S., & Little, C. (Eds.). (2017). *Time ontology in OWL*. World Wide Web Consortium. https://www.w3.org/TR/owl-time/

Fielding, R., Nottingham, M., & Reschke, J. (2022). *HTTP semantics* (RFC 9110). Internet Engineering Task Force. https://doi.org/10.17487/RFC9110

International Organization for Standardization. (2019). *Date and time—Representations for information interchange—Part 1: Basic rules* (ISO Standard No. 8601-1:2019). https://www.iso.org/standard/70907.html

Klyne, G., & Newman, C. (2002). *Date and time on the Internet: Timestamps* (RFC 3339). Internet Engineering Task Force. https://doi.org/10.17487/RFC3339

Moreau, L., & Missier, P. (Eds.). (2013a). *PROV-DM: The PROV data model*. World Wide Web Consortium. https://www.w3.org/TR/prov-dm/

Moreau, L., & Missier, P. (Eds.). (2013b). *PROV-O: The PROV ontology*. World Wide Web Consortium. https://www.w3.org/TR/prov-o/
