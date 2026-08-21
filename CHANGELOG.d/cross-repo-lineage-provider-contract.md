# Unreleased: bounded cross-repository lineage provider contract

LineageWeave now exposes a versioned, store-agnostic contract for authorized
Naruon-shaped evidence. It preserves opaque evidence references, separate RFC
email fields, project hints, cutoff exclusion, channel limitations, and a
deterministic request digest without reading Naruon's database or claiming
Naruon's authoritative project status. Nested email references and project
hints have explicit request-level ceilings so callers cannot bypass the
bounded-work contract with oversized collections.

Provider failures now become an explicit unavailable-channel limitation and
rerun with renormalized non-LLM weights. Long body text is retained in the
request envelope without being flattened into the short pairwise comparison
label.
