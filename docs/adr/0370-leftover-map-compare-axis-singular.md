# ADR 0370 — Persisted leftover-map singular values in grouping comparison axes

**Decision status:** Proposed

## Problem
The grouping-comparison read model persists `leftover_singular_value` for each Gabriel leftover-map axis, but exact predecessor #829 (`07301271f813b8bb0e40f57aa22373baf5efbf01`, ADR 0369 / v2.55.0) does not expose that scale on the comparison strip. Historical #830 demonstrated the buyer-visible delta on stale ancestry and historical ADR 0294 / v2.51.0, which are evidence only because those identities now belong to different serialized decisions.

## Constraints
- Consume only persisted `leftover_singular_value`; LineageWeave must not derive `σ_k` from axis share, pair or marker counts, coordinates, distance, rank, coverage, incomplete counts, reconstruction, or any other psychometric value.
- Accept only finite, non-negative persisted values. Persisted zero is meaningful and must remain visible as `0.00`; missing, non-finite, or negative values omit only the singular-value caption.
- Singular-value availability and axis-share availability are independent. An invalid or missing value on one axis metric must not suppress a valid value on the other.
- Preserve the existing full-visible-grouping authorization boundary for persisted grouping aggregates; do not reconstruct a hidden population from caller-visible members.
- The comparison caption remains a LineageWeave read-model/UI concern. Psychometric estimation and true-parameter validation remain owned by the released `fast-mlsirm` boundary.
- The canonical eight-locale translation resource remains the versioned database ledger serialized through #922/#929/#932. This decision must not create a competing inline ES/DE/FR store.

## Alternatives and decision
Omitting `σ_k` hides persisted Gabriel scale that is already available in the authorized read model. Recomputing it in the client would duplicate psychometric authority and can diverge from the persisted factorization. Coupling singular display to axis-share validity would also discard valid evidence. Therefore the grouping-comparison strip consumes the persisted scalar directly, formats finite non-negative values independently from axis share, preserves zero, and fail-closes only the invalid singular caption.

This is the serialized successor of exact #829 `07301271f813b8bb0e40f57aa22373baf5efbf01` and allocates v2.56.0. Historical #830 ADR 0294 / v2.51.0 remains provenance only; current ADR 0294 continues to govern grouping-comparison incomplete-item coverage.

## Verification
A current-parent test must first RED because exact #829 lacks the grouping-comparison singular formatter. The causal implementation then requires focused formatter/render/API regressions, the full PostgreSQL-backed backend suite, frontend lint/test/build/Storybook, release-version parity, and a clean exact-head tree. Material UI completion additionally requires current-head responsive, keyboard, focus, and accessibility evidence. Hosted security gates and qualifying independent review remain separate merge gates; this ADR stays Proposed until the protected-main release is actually accepted.

## Evidence
Gabriel, K. R. (1971). The biplot graphic display of matrices with application to principal component analysis. *Biometrika, 58*(3), 453–467.

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping unobserved item–respondent interactions: A latent space item response model with interaction map. *Psychometrika, 86*(2), 378–403.
