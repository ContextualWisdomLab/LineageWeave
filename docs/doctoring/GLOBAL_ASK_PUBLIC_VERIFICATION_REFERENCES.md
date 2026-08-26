# Global Ask public-verification research register

ADR 0234 adopts three distinct contracts:

- FEVER supplies the evidence-dependent `supported`, `refuted`, and
  `not_enough_information` outcome model.
- W3C PROV-O keeps internal source evidence, external web evidence, and the
  verification activity separate.
- SearXNG's Search API defines the bounded JSON retrieval transport; public
  instance defaults are not assumed. The checked 2026-08-26 documentation
  states that `/search` accepts GET query parameters and that JSON output must
  be enabled by the instance; disabled formats return HTTP 403.

The implementation does not infer claim eligibility from question-token
overlap or rendered-string patterns. It projects typed project and non-person
graph claims from normalized PostgreSQL evidence after authorization. Model
and orchestration selection remains contextual-orchestrator authority.

## APA 7 references

Lebo, T., Sahoo, S., & McGuinness, D. (Eds.). (2013). *PROV-O: The PROV
ontology*. World Wide Web Consortium. https://www.w3.org/TR/prov-o/

SearXNG. (2026). *Search API*. https://docs.searxng.org/dev/search_api.html

Thorne, J., Vlachos, A., Christodoulopoulos, C., & Mittal, A. (2018). FEVER: A
large-scale dataset for fact extraction and verification. In *Proceedings of
the 2018 Conference of the North American Chapter of the Association for
Computational Linguistics: Human Language Technologies* (Vol. 1, pp. 809–819).
Association for Computational Linguistics. https://doi.org/10.18653/v1/N18-1074
