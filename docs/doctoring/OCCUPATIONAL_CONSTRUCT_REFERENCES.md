# Occupational construct evidence register

Supporting research for [ADR 0248](../adr/0248-occupational-construct-evidence-boundary.md).
This register does not create mappings. It records which relationships a
source actually supports and which tempting inferences remain prohibited.

## Adopted sources and limits

- The O*NET 31.0 database is the maintained source for ability, work-style,
  skill, work-activity, work-context, task, and published linkage identifiers.
  It is CC BY 4.0; derived products must credit USDOL/ETA, link the license,
  and identify modifications. LineageWeave links rather than remints these
  resources.
<<<<<<< HEAD
=======
- The O*NET 31.0 Content Model Reference publishes 3,006 hierarchy elements.
  ADR 0250 admits only the source-defined cognitive-ability (`1.A.1`), work-
  style (`1.D`), and work-activity (`4.A`) roots and descendants; it preserves
  blank descriptions as unavailable and stores no occupation rating.
>>>>>>> origin/main
- The O*NET Content Model separates worker characteristics and requirements
  from occupational requirements. It does not make FJA worker functions
  equivalent to abilities, dispositions, or affect.
- O*NET publishes Ability-to-Work-Activity and Work-Style-to-Work-Activity
  linkage datasets. Those source records may be reused with their identifiers
  and provenance; transitive DPT mappings may not be inferred from them.
- EmotionML defines a representation mechanism, not a universal emotion
  taxonomy. Every affective assertion must identify its vocabulary.
- PROV-O qualified relations and SHACL validation support evidence-bearing,
  fail-closed assertions. They do not establish occupational-psychology
  validity by themselves.

## Explicit non-adoptions

- Data = cognitive, People = affective, and Things = behavioral.
- FJA rank as ability intensity, affect, performance, or interval measurement.
- O*NET work styles as moods or emotions.
- `owl:sameAs`, `owl:equivalentClass`, `skos:exactMatch`, or
  `skos:closeMatch` between FJA functions and psychological constructs.
- Causal or person-level claims derived only from a job title, work function,
  aggregate occupation rating, or source-system label.

## APA 7 references

Hansen, M. C., Norton, J. J., Gregory, C. M., Meade, A. W., Foster Thompson,
L., Rivkin, D., Lewis, P., & Nottingham, J. (2014). *A multi-phase rational
method for developing area work activities*. National Center for O*NET
Development. https://www.onetcenter.org/dl_files/DWA_2014.pdf

Knublauch, H., & Kontokostas, D. (Eds.). (2017). *Shapes Constraint Language
(SHACL).* World Wide Web Consortium. https://www.w3.org/TR/shacl/

Lebo, T., Sahoo, S., & McGuinness, D. (Eds.). (2013). *PROV-O: The PROV
ontology.* World Wide Web Consortium. https://www.w3.org/TR/prov-o/

Miles, A., & Bechhofer, S. (Eds.). (2009). *SKOS simple knowledge
organization system reference.* World Wide Web Consortium.
https://www.w3.org/TR/skos-reference/

National Center for O*NET Development. (2026). *O*NET 31.0 database* [Data
set]. U.S. Department of Labor, Employment and Training Administration.
https://www.onetcenter.org/database.html

<<<<<<< HEAD
=======
National Center for O*NET Development. (2026). *O*NET 31.0 Content Model
Reference* [Data set]. U.S. Department of Labor, Employment and Training
Administration. https://www.onetcenter.org/dl_files/database/db_31_0_json/content_model_reference.json

>>>>>>> origin/main
Peterson, N. G., Mumford, M. D., Borman, W. C., Jeanneret, P. R., Fleishman,
E. A., Levin, K. Y., Campion, M. A., Mayfield, M. S., Morgeson, F. P.,
Pearlman, K., Gowing, M. K., Lancaster, A. R., Silver, M. B., & Dye, D. M.
(2001). Understanding work using the Occupational Information Network
(O*NET): Implications for practice and research. *Personnel Psychology,
54*(2), 451–492. https://doi.org/10.1111/j.1744-6570.2001.tb00100.x

Putka, D. J., Kell, H. J., Voss, N., Oswald, F. L., & Lewis, P. (2024).
*Revisiting the work styles domain of the O*NET Content Model* (Report No.
090). Human Resources Research Organization.
https://www.onetcenter.org/dl_files/Work_Styles_New.pdf

Schröder, M., Pirker, H., & Lamolle, M. (Eds.). (2014). *Emotion Markup
Language (EmotionML) 1.0.* World Wide Web Consortium.
https://www.w3.org/TR/emotionml/

Weiss, H. M., & Cropanzano, R. (1996). Affective events theory: A theoretical
discussion of the structure, causes and consequences of affective experiences
at work. *Research in Organizational Behavior, 18*, 1–74.
https://web.mit.edu/curhan/www/docs/Articles/15341_Readings/Affect/AffectiveEventsTheory_WeissCropanzano.pdf
