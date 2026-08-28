# ADR 0232: Worker-function taxonomy in the published ontology

**Status:** Accepted
**Date:** 2026-08-26
**Extends:** [ADR 0004](0004-knowledge-graph-ontology.md), [ADR 0145](0145-psychometric-channel-weight-estimation.md), [ADR 0207](0207-repository-case-ontology-namespace-canonical.md)

## Context

Industrial and organizational psychology describes work through
worker functions rather than job titles. Functional Job Analysis (FJA)
expresses every job's relationship to *Data*, *People*, and *Things*
through three ordered lists, carried verbatim in the Dictionary of
Occupational Titles Appendix B (U.S. Department of Labor, 1991): Data
ranks 0-6, People ranks 0-8, Things ranks 0-7, each ordered so that the
lower digit names the more complex function (Fine & Cronshaw, 1999).
The cited Fleishman and O*NET sources define separate ability, skill,
and work-style taxonomies, but do not publish a crosswalk from these 24
DOT worker functions. Mapping them locally would be an unsupported
semantic assertion.

The repository had no representation for this vocabulary: a post or
analysis cannot yet say "this evidence describes Analyzing-level data
work" without inventing an untracked term. The ontology is the correct
home -- it already publishes the governed semantic layer over
PostgreSQL graph facts -- but two constraints bind any addition:

1. The lookup-code round trip (`tests/test_ontology.py`) requires every
   `:lookupCode` term to exist as a seeded `common_lookup_value` row and
   vice versa. Worker functions are not relational lookup rows today.
2. Measurement stays governed by ADR 0145: nothing may mint a numeric
   weight from a qualitative taxonomy.

## Decision

1. Publish all 24 worker functions as a `skos:ConceptScheme`
   (`:workerFunctionScheme`) of `:WorkerFunction` concepts in
   `docs/ontology/lineageweave-kg.ttl`, each carrying the official DOT
   Appendix B definition verbatim as its `skos:definition`, its definitional
   rank (`:fjaRank`), and its domain (`:fjaDomain`). No DOT-to-O*NET or
   Fleishman crosswalk is asserted without an authoritative mapping source.
2. Like column-projection datatype properties, these concepts carry no
   `:lookupCode`: they are not `common_lookup_value` rows, so the round
   trip is untouched. Binding a function to stored rows needs a separate
   schema-and-seed decision.
3. Ranks are scale positions copied from the published table. They are
   never fitted, calibrated, renormalized, or used as weights; this
   decision adds zero arithmetic to the measurement layer.
4. The application read model lives in
   `lineageweave/worker_function_taxonomy.py`: cached, deterministically
   sorted records; `(domain, rank)` lookups that return ``None``/``{}``
   for absent ranks (honest unknown) and raise ``ValueError`` for an
   unrecognized domain (caller error); fail-closed ``ValueError`` on a
   malformed TTL declaration.
5. The canonical repository-case namespace (ADR 0207) mints every IRI;
   no lowercase compatibility form is introduced.

## Consequences

- The IO-psychology worker-function vocabulary becomes addressable and
  citable inside the published semantic layer before any persistence
  decision exists.
- A future crosswalk requires its own provenance-bearing decision and an
  authoritative mapping source; shared labels alone are not such evidence.
- Adding DB-backed function annotations later means one migration plus
  seed rows and `:lookupCode` declarations -- the extension path is
  additive by construction.
- `tests/test_worker_function_taxonomy.py` pins the complete published text,
  so truncation, paraphrase, and spelling drift fail CI.

## Verification

- `tests/test_worker_function_taxonomy.py`: completeness (24 concepts),
  per-domain rank extents, complete verbatim official definitions,
  deterministic ordering, canonical namespace, fail-closed lookups.
- `tests/test_ontology.py` continues to pass unchanged: the round trip
  sees no new lookup codes.

## References

Fine, S. A., & Cronshaw, S. F. (1999). *Functional job analysis: A
foundation for human resources management*. Lawrence Erlbaum
Associates.

Fleishman, E. A., & Quaintance, M. K. (1984). *Taxonomies of human
performance: The description of human tasks*. Academic Press.

Fleishman, E. A., Costanza, D. P., & Marshall-Mies, J. C. (1999).
Abilities. In N. G. Peterson, M. D. Mumford, W. C. Borman, P. R.
Jeanneret, & E. A. Fleishman (Eds.), *An occupational information system
for the 21st century: The development of O*NET* (pp. 97-112). American
Psychological Association.

Mumford, M. D., Peterson, N. G., & Childs, R. A. (1999). Basic and
cross-functional skills. In N. G. Peterson, M. D. Mumford, W. C. Borman,
P. R. Jeanneret, & E. A. Fleishman (Eds.), *An occupational information
system for the 21st century: The development of O*NET* (pp. 49-69).
American Psychological Association.

Peterson, N. G., Mumford, M. D., Borman, W. C., Jeanneret, P. R., &
Fleishman, E. A. (Eds.). (1999). *An occupational information system for
the 21st century: The development of O\*NET*. American Psychological
Association.

U.S. Department of Labor. (1991). *Dictionary of occupational titles*
(4th ed., rev., Appendix B). U.S. Government Printing Office.
https://www.dol.gov/agencies/oalj/PUBLIC/DOT/REFERENCES/DOTAPPB

Cyganiak, R., Wood, D., & Lanthaler, M. (Eds.). (2014). *RDF 1.1
concepts and abstract syntax*. World Wide Web Consortium.
https://www.w3.org/TR/rdf11-concepts/
