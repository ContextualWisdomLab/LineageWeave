# ADR 0369 — Persisted unexplained leftover share in grouping comparison pair actions

**Decision status:** Proposed

## Problem
The period-report pair model persists `leftover_map_unexplained_share` (`s = U² / R²`) for authorized leftover pairs, but exact #828's grouping-comparison read path omits that field, so the frontend cannot receive it from `GET /api/reports/compare/{period_code}`. Historical #829 proved the buyer-visible delta but used stale ancestry/identity and put the metric only in a child badge while the parent button supplied an explicit accessible name.

## Constraints
- Consume persisted psychometric truth; never derive `s` from `U`, `R`, reconstruction, distance, geometry, rank, coverage, or other shares.
- Missing/non-finite values are omitted. Zero and finite values above 1 remain explicit and unclamped.
- Whole-population authorization remains current-parent authority; no visible-subset recomputation.
- The actionable pair button and visible badge communicate the same finite persisted value.
- Inline KO/ZH/JA/VI copy is compatibility presentation only; #922/#929/#932 remain canonical eight-locale translation-ledger authority.

## Alternatives and decision
Hiding `s` loses persisted buyer evidence. Recomputing it duplicates psychometric authority. A child-only badge fails the actionable accessible-name contract. Therefore consume persisted finite `s`, append its localized label/value to the button accessible name, and mark the duplicate visible badge `aria-hidden`.

This is the serialized successor of exact #828 `7b6dbbb99a09d0523bce43c6872bbd9fa382a43a`, adopts the distinct historical #829 delta, and allocates v2.55.0. ADR0295/v2.52.0 is historical evidence only.

## Verification
The accessibility test must RED while the parent name omits `U²/R² 0.02`, then GREEN after only the accessible-name/duplicate-badge fix. The transport regression must independently RED while the comparison SELECT omits the persisted field, then GREEN without deriving or clamping it. A real authenticated PostgreSQL/Keycloak/Valkey `GET /api/reports/compare/2026-W02` acceptance must prove the persisted key/value reaches authorized leftover pairs. Full backend, frontend lint/test/build/Storybook, version parity, clean-tree authority, and non-force promotion are required. Hosted exact-product-head checks, browser/keyboard/focus/a11y evidence, and qualifying independent approval remain separate merge gates.

## Evidence
Gabriel, K. R. (1971). The biplot graphic display of matrices with application to principal component analysis. *Biometrika, 58*(3), 453–467.

Jeon, M., Jin, I. H., Schweinberger, M., & Baugh, S. (2021). Mapping unobserved item–respondent interactions: A latent space item response model with interaction map. *Psychometrika, 86*(2), 378–403.
