## Added

- Added a LineageWeave-owned dichotomous measurement-policy contract that keeps missing/abstain/adjudication states outside 0/1 responses, keeps Rasch distinct from generic one-parameter logistic IRT, exposes only `rasch`, `irt_2plm`, `irt_3plm`, and `irt_4plm` as normal production model families, does not infer a family from domain labels or hand-authored flags, allows draft/pilot instruments to preserve observations without a latent model, and requires published instruments to bind both an explicit governed model family and a canonical non-empty activation-evidence reference.
