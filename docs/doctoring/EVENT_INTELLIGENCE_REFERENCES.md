# Event Intelligence research and standards traceability

**Reviewed:** 2026-08-21
**Applies to:** ADR 0120, `lineageweave.event_intelligence`,
`docs/ontology/event-intelligence-profile.ttl`, and
`docs/ontology/event-intelligence-profile.shacl.ttl`

## Design traceability

| Requirement | Product decision | Evidence |
|---|---|---|
| Separate event occurrence from reporting and availability | Preserve event, assertion, document, available, recorded, and cutoff clocks | ISO-TimeML; TEPP temporal contract |
| Express instants, intervals, and ordering | Use OWL-Time `Interval` and `Instant` resources plus typed forward/retrospective relations | W3C/OGC OWL-Time |
| Keep a generated artifact distinct from the process that generated it | Model `EventIntelligenceDossier` as `prov:Entity` and `DossierGenerationActivity` as `prov:Activity`; bind `prov:used` and `prov:generated` only through the activity | W3C PROV-O |
| Keep source evidence distinct from the real-world event | Model `EventAssertion` between the source post and `EventEpisode`; specialize `prov:wasDerivedFrom` for source support and keep the compact `evidencesEvent` projection outside PROV influence | W3C PROV-O; evidence-grounding contract |
| Publish interoperable closed-world graph constraints | Version a SHACL shapes graph for activity, assertion, evidence-bundle, and temporal cardinalities | W3C SHACL |
| Preserve source/model provenance across products | Every artifact and claim cites immutable evidence IDs and SHA-256 digests | W3C PROV-O; TEPP export manifest |
| Treat event detection/tracking as multiple tasks | Keep graph/link evidence, event/topic artifacts, and claims separate | NIST Topic Detection and Tracking |
| Combine neural extraction with symbolic event schemas | Compose LLM judgment with typed ontology and source provenance rather than allowing prose-only output | CHRONOS |
| Represent topic change through a model artifact, not UI heuristics | TEPP remains the temporal/topic authority and exposes model/version/digest | Dynamic Topic Models; TEPP API contract |
| Use LLMs as complementary evaluators | Orchestrator returns a structured evidence-bounded verdict; it does not replace statistical metrics | Stammbach et al.; Yang et al. |
| Keep LLM judgment calibratable | fast-mlsirm retains criterion/IRT and uncertainty authority; judge output has no psychometric score field | fast-mlsirm LLM judge contract; G-Eval limitations |
| Adjust test-time computation without changing evidence authority | Record orchestrator operation, policy, prompt digest, and trace identity | contextual-orchestrator paper-grounded contract |

## Internal contract sources

- `ContextualWisdomLab/TEPP`, `docs/API_CONTRACT.md`: TEPP owns temporal/topic
  scientific truth; artifacts bind snapshot, cutoff, model contract, engine,
  validation, and digest.
- `ContextualWisdomLab/TEPP`, `crates/tepp_api/src/export.rs`:
  `ReproducibilityManifest` v1 field contract.
- `ContextualWisdomLab/fast-mlsirm`,
  `python/fast_mlsirm/llm_judge.py`: bounded rubric validation, strict JSON,
  orchestration trace, and intentional IRT projection boundary.
- `ContextualWisdomLab/contextual-orchestrator`,
  `conductor/tracks/001-paper-grounded-orchestrator/spec.md`: direct versus
  thinker/worker/verifier/synthesizer routing, access lists, trace and audit,
  and Fugu/TRINITY/Conductor contract tests.
- `ContextualWisdomLab/LineageWeave`, ADR 0004 and
  `docs/ontology/lineageweave-kg.ttl`: current graph and semantic vocabulary.
- `ContextualWisdomLab/LineageWeave`, ADR 0065 and
  `docs/PROV_O_IMPLEMENTATION.md`: standards-complete PROV-O persistence and
  deterministic materialization boundary.

## APA 7th references

Rundgren, A., Jordan, B., & Erdtman, S. (2020). *JSON canonicalization scheme
(JCS) (RFC 8785).* RFC Editor. https://www.rfc-editor.org/rfc/rfc8785

Blei, D. M., & Lafferty, J. D. (2006). Dynamic topic models. In *Proceedings
of the 23rd International Conference on Machine Learning* (pp. 113–120).
Association for Computing Machinery. https://doi.org/10.1145/1143844.1143859

Chang, M., Fokoue, A., Uceda-Sosa, R., Awasthy, P., Barker, K., Kumaravel, S.,
Hassanzadeh, O., Soares, E., Gao, T., Bhattacharjya, D., Florian, R., &
Roukos, S. (2024). CHRONOS: A schema-based event understanding and prediction
system. *Proceedings of the AAAI Conference on Artificial Intelligence,
38*(21), 22871–22877. https://doi.org/10.1609/aaai.v38i21.30323

Cox, S. J. D., & Little, C. (Eds.). (2022). *Time ontology in OWL*.
World Wide Web Consortium. https://www.w3.org/TR/owl-time/

Fiscus, J. G., & Doddington, G. R. (2002). Topic detection and tracking
evaluation overview. In J. Allan (Ed.), *Topic detection and tracking:
Event-based information organization*. Springer.
https://www.nist.gov/publications/topic-detection-and-tracking-evaluation-overview

International Organization for Standardization. (2012). *Language resource
management—Semantic annotation framework (SemAF)—Part 1: Time and events
(SemAF-Time, ISO-TimeML) (ISO 24617-1:2012).* The standard was confirmed in
2023. https://www.iso.org/standard/37331.html

Knublauch, H., & Kontokostas, D. (Eds.). (2017). *Shapes constraint language
(SHACL).* World Wide Web Consortium. https://www.w3.org/TR/shacl/

Lebo, T., Sahoo, S., McGuinness, D., Belhajjame, K., Cheney, J., Corsar, D.,
Garijo, D., Soiland-Reyes, S., Zednik, S., & Zhao, J. (Eds.). (2013).
*PROV-O: The PROV ontology*. World Wide Web Consortium.
https://www.w3.org/TR/prov-o/

Liu, Y., Iter, D., Xu, Y., Wang, S., Xu, R., & Zhu, C. (2023). G-Eval: NLG
evaluation using GPT-4 with better human alignment. In *Proceedings of the
2023 Conference on Empirical Methods in Natural Language Processing*
(pp. 2511–2522). Association for Computational Linguistics.
https://doi.org/10.18653/v1/2023.emnlp-main.153

Stammbach, D., Zouhar, V., Hoyle, A., Sachan, M., & Ash, E. (2023).
Revisiting automated topic model evaluation with large language models. In
*Proceedings of the 2023 Conference on Empirical Methods in Natural Language
Processing* (pp. 9348–9357). Association for Computational Linguistics.
https://doi.org/10.18653/v1/2023.emnlp-main.581

Yang, X., Zhao, H., Phung, D., Buntine, W., & Du, L. (2025). LLM reading tea
leaves: Automatically evaluating topic models with large language models.
*Transactions of the Association for Computational Linguistics, 13*, 357–375.
https://doi.org/10.1162/tacl_a_00744

## Interpretation limits

These sources support typed temporal representation, event detection/tracking,
provenance, closed-world RDF validation, temporal topic artifacts,
neuro-symbolic event schemas, and LLMs as complementary evaluators. They do
**not** establish that a LineageWeave dossier is a causal model, that an LLM
verdict is ground truth, or that outputs from different numerical scales can
be averaged. ADR 0120 therefore preserves each authority and uncertainty
instead of making those claims.
