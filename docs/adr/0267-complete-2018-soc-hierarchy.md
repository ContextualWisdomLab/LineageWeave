# ADR 0267: Complete 2018 SOC hierarchy as a generated ontology fragment

**Status:** Accepted
**Date:** 2026-08-27

## Context

ADR 0245 publishes only the 23 SOC major groups. That is insufficient for
occupation-level evidence: the official 2018 SOC contains four aggregation
levels and 1,447 classifications. A label-derived parent or a locally invented
job-family crosswalk would violate the repository's evidence boundary.

## Decision

1. Import the complete official 2018 SOC structure: 23 major groups, 98 minor
   groups, 459 broad occupations, and 867 detailed occupations.
2. Preserve the source row's level and parent exactly. Publish `skos:broader`
   only from that parent column; never derive hierarchy from code digits or
   titles.
3. Keep the normalized source snapshot at
   `docs/ontology/data/soc-2018-structure.csv` and generate
   `docs/ontology/soc-2018-structure.ttl` deterministically. The source XLSX
   SHA-256 is
   `ade08af40923266f3a854842e888ca3e93c15b26a147c20a2b12a61f4c4f4077`;
   the normalized CSV SHA-256 is
   `7de1c9d4da14d8eeb95197974d9dc1989752ebda235dd234b1693f336891f68e`.
4. Treat SOC as a statistical occupational classification, not an employer's
   job family, job series, position, person trait, or psychometric score. Those
   bindings require separately authorized source assertions.
5. Runtime and publication loaders merge the governed Turtle fragments into
   one graph. The public artifact remains one canonical ontology namespace and
   is serialized from that merged graph, rather than concatenating independent
   Turtle documents. Its manifest identifies and hashes every governed input.

## Consequences

Occupation evidence can address every official 2018 SOC level without an
invented mapping. The generated fragment is larger, but review remains bounded
by the pinned source digests, deterministic renderer, exact counts, parent
closure, and graph tests.

## References

U.S. Bureau of Labor Statistics. (2018). *2018 Standard Occupational
Classification system*. U.S. Department of Labor.
https://www.bls.gov/soc/2018/

U.S. Bureau of Labor Statistics. (2018). *Standard Occupational
Classification and coding structure, 2018 SOC*. U.S. Department of Labor.
https://www.bls.gov/soc/2018/soc_2018_class_and_coding_structure.pdf
