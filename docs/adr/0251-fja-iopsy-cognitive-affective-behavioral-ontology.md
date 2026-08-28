# ADR 0251: I/O Psychology Cognitive, Affective, and Behavioral Ontology and Semantic Layer

**Status:** Accepted
**Date:** 2026-08-27
**Deciders:** LineageWeave Architecture, ContextualWisdomLab Core

---

## Context

Sydney A. Fine's Functional Job Analysis (FJA; Fine & Wiley, 1971; Fine &
Cronshaw, 1999) establishes that every job involves the worker's relationship to
three universal domains: **Data**, **People**, and **Things**. ADR 0232
formalized the 24 DOT worker functions (U.S. Department of Labor, 1991,
Appendix B) in the LineageWeave knowledge-graph ontology (`lineageweave-kg.ttl`).

However, worker functions do not exist in a psychological vacuum. In Industrial
and Organizational (I/O) Psychology, occupational demands across Data, People,
and Things systematically activate and elicit:

1. **Cognitive Processes & Demands**: Working memory allocation (Baddeley, 2000),
   complex problem solving (Funke, 2010), strategic decision making (Eisenhardt,
   1989), cognitive appraisal (Lazarus & Folkman, 1984), executive functioning
   (Miyake et al., 2000), situational awareness (Endsley, 1995), selective and
   divided attention (Wickens, 2002), mental workload (Sweller, 1988), and
   diagnostic reasoning (Patel et al., 1989).
2. **Affective States & Emotional Regulation**: Emotional labor (surface acting,
   deep acting, genuine expression; Grandey, 2000; Hochschild, 1983), emotion
   regulation (Gross, 1998), burnout dimensions (emotional exhaustion,
   depersonalization/cynicism, reduced personal accomplishment; Maslach et al.,
   2001), work engagement (vigor, dedication, absorption; Schaufeli et al.,
   2002), psychological safety (Edmondson, 1999), job satisfaction (Locke,
   1976), organizational commitment (Meyer & Allen, 1991), and occupational
   strain (Karasek, 1979; Bakker & Demerouti, 2007).
3. **Behavioral Manifestations & Outcomes**: Core task performance (Campbell,
   1990; Borman & Motowidlo, 1993), technical precision, organizational
   citizenship behavior (OCB-I altruism and courtesy; OCB-O conscientiousness,
   civic virtue, sportsmanship; Organ, 1988; Williams & Anderson, 1991),
   counterproductive work behavior (CWB interpersonal, organizational,
   production, and property deviance; Bennett & Robinson, 2000; Spector et al.,
   2006), proactive problem solving and voice behavior (Parker et al., 2010; Van
   Dyne & LePine, 1998), safety compliance and participation (Christian et al.,
   2009; Neal & Griffin, 2006), adaptive performance (Pulakos et al., 2000),
   leadership and mentoring (Bass, 1985; Kram, 1985), and withdrawal behaviors
   (turnover, absenteeism, presenteeism; Johns, 2010; Mobley, 1977).

Without a formal ontology and semantic layer mapping FJA worker functions to
their cognitive, affective, and behavioral nomological network, downstream
psychometric analysis risks fragmented heuristics and unanchored assumptions.

---

## Decision

1. **Formal Ontology Extension (`docs/ontology/lineageweave-kg.ttl`)**:
   - Declare the core class `:IOPsyConstruct` and its disjoint subclasses
     `:CognitiveConstruct`, `:AffectiveConstruct`, and `:BehavioralConstruct`.
   - Declare corresponding `skos:ConceptScheme` schemes (`:iopsyConstructScheme`,
     `:cognitiveConstructScheme`, `:affectiveConstructScheme`,
     `:behavioralConstructScheme`).
   - Declare datatype properties `:constructDimension` and
     `:constructTheoreticalBasis`.
   - Declare object properties establishing tripartite demands and nomological
     relations:
     - `:requiresCognitiveDemand`, `:imposesMentalWorkload`
     - `:elicitsEmotionalDemand`, `:requiresEmotionalLabor`
     - `:manifestsInBehavior`, `:requiresPsychomotorBehavior`,
       `:requiresInterpersonalBehavior`
     - `:cognitivelyMediates`, `:affectivelyDrives`, `:moderatesStrain`,
       `:buffersBurnout`, `:inducesBurnoutRisk`, `:reciprocallyInfluences`
   - Formally declare 20 cognitive constructs, 23 affective constructs, and 31
     behavioral constructs with preferred labels, definitions, dimensions, and
     APA 7th citations.
   - Enforce explicit tripartite demand and manifestation relationships for all
     24 DOT/FJA worker functions.

2. **SHACL Closed-World Validation (`docs/ontology/lineageweave-kg-shapes.ttl`)**:
   - Declare `:IOPsyConstructShape`, `:CognitiveConstructShape`,
     `:AffectiveConstructShape`, and `:BehavioralConstructShape`.
   - Validate non-empty dimensions and theoretical basis strings, and enforce
     class disjointness at the validation boundary.

3. **Typed Application Semantic Layer (`lineageweave/iopsy_taxonomy.py`)**:
   - Provide immutable, strongly-typed records: `IOPsyConstructRecord`,
     `IOPsyRelationRecord`, and `WorkerFunctionIOPsyProfile`.
   - Implement deterministic accessors: `cognitive_construct_records()`,
     `affective_construct_records()`, `behavioral_construct_records()`,
     `all_iopsy_construct_records()`, `iopsy_construct_record()`,
     `iopsy_profile_for_worker_function()`, `relations_for_construct()`,
     `all_iopsy_relation_records()`, and `derive_composite_job_profile()`.
   - Ensure 100% public docstring coverage with comprehensive APA 7th literature
     citations.

4. **Measurement & Estimation Boundary (ADR 0145 / ADR 0231)**:
   - Ranks and relations remain grounded in published scientific literature.
   - No ad hoc numeric weights, speculative coefficients, or heuristic scorings
     are fabricated; mathematical and psychometric estimation remains governed
     by external Rust engines (TEPP, fast-mlsirm).

---

## Consequences

- **Formal Traceability**: Enables direct traversal from occupational functional
  codes (FJA Data/People/Things) to psychological processes and outcomes.
- **Evidence Grounding**: Every construct carries its APA 7th academic literature
  anchor.
- **Deterministic Publication**: Published static ontology site (GitHub Pages)
  renders the complete I/O psychology graph with zero dangling fragments.
- **Fail-Closed Verification**: Unsupported constructs or malformed ratings
  fail closed loudly without synthetic defaults.

---

## References

Bakker, A. B., & Demerouti, E. (2007). The job demands-resources model: State
    of the art. *Journal of Managerial Psychology*, 22(3), 309–328.

Borman, W. C., & Motowidlo, S. J. (1993). Expanding the criterion domain to
    include elements of contextual performance. In N. Schmitt & W. C. Borman
    (Eds.), *Personnel selection in organizations* (pp. 71–98). Jossey-Bass.

Campbell, J. P. (1990). Modeling the performance prediction problem in
    industrial and organizational psychology. In M. D. Dunnette & L. M. Hough
    (Eds.), *Handbook of industrial and organizational psychology* (2nd ed.,
    Vol. 1, pp. 687–732). Consulting Psychologists Press.

Christian, M. S., Bradley, J. C., Wallace, J. C., & Burke, M. J. (2009).
    Workplace safety: A meta-analysis of the roles of person and situation
    factors. *Journal of Applied Psychology*, 94(5), 1103–1127.

Edmondson, A. (1999). Psychological safety and learning behavior in work
    teams. *Administrative Science Quarterly*, 44(2), 350–383.

Fine, S. A., & Cronshaw, S. F. (1999). *Functional job analysis: A foundation
    for human resources management*. Lawrence Erlbaum Associates.

Grandey, A. A. (2000). Emotion regulation in the workplace: A new way to
    conceptualize emotional labor. *Journal of Occupational Health Psychology*,
    5(1), 95–110.

Hochschild, A. R. (1983). *The managed heart: Commercialization of human
    feeling*. University of California Press.

Karasek, R. A. (1979). Job demands, job decision latitude, and mental strain:
    Implications for job redesign. *Administrative Science Quarterly*, 24(2),
    285–308.

Maslach, C., Schaufeli, W. B., & Leiter, M. P. (2001). Job burnout. *Annual
    Review of Psychology*, 52(1), 397–422.

Organ, D. W. (1988). *Organizational citizenship behavior: The good soldier
    syndrome*. Lexington Books.

Pulakos, E. D., Arad, S., Donovan, M. A., & Plamondon, K. E. (2000).
    Adaptability in the workplace: Development of a taxonomy of adaptive
    performance. *Journal of Applied Psychology*, 85(4), 612–624.

Schaufeli, W. B., Salanova, M., González-Romá, V., & Bakker, A. B. (2002).
    The measurement of engagement and burnout: A two sample confirmatory
    factor analytic approach. *Journal of Happiness Studies*, 3(1), 71–92.

Spector, P. E., Fox, S., Penney, L. M., Bruursema, K., Goh, A., & Kessler,
    S. (2006). The dimensionality of counterproductivity: Are all
    counterproductive behaviors created equal? *Journal of Vocational
    Behavior*, 68(3), 446–460.
