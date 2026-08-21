# ADR 0105: Preserve explicit metric scripts in semantic text

- Status: Accepted
- Date: 2026-08-21

## Context

Source posts may encode a metric unit such as `m<sup>3</sup>` or an indexed
quantity such as `m<sub>3</sub>`. Removing the script element loses searchable
and buyer-visible mathematical meaning, while treating every numeric
superscript as mathematics would break the existing footnote contract.

## Decision

1. Preserve the original source body unchanged.
2. In derived semantic text, normalize only an explicit bounded metric base
   (`m`, `cm`, `mm`, `km`, or `kg`, optionally preceded by a number) followed
   by one-to-three numeric `sup` or `sub` elements into Unicode
   superscript/subscript digits. For example, `5m<sup>3</sup>` becomes `5m³`.
3. Leave ordinary numeric superscripts on prose under the existing footnote
   role contract.
4. Apply the same normalization in backend chunks and frontend rendering.

## Consequences

Metric exponents remain searchable and readable without inventing formula
semantics. Arbitrary mathematical markup beyond this bounded case remains an
explicit open gap and must be covered by a later ADR and fixture before being
normalized.
