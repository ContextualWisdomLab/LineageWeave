# ADR 0246: Expanded Voice-of-X post taxonomy

## Status

Accepted (2026-08-26). Extends ADR 0207 decision 8 without claiming that the
result is an exhaustive stakeholder taxonomy.

## Context

`source_post.voc_type_code` records what kind of voice a source post carries.
The existing five-code scheme (`voc`, `vocc`, `voco`, `vom`, `vop`) cannot
represent supplier, employee, internal-business, regulator, investor,
society, or process-generated source records without changing the source
classification or rejecting the import.

`post_counterparty_entity.relationship_type_code` answers a different
question: how a named organization relates to the post author's organization.
A post voice is not evidence that every organization named in the post has the
same relationship. This ADR therefore does not mirror post-type codes into the
counterparty relationship vocabulary. Any future relationship term requires
its own direction, evidence contract, and source-grounded definition.

## Decision

Add seven product-controlled concepts to the existing `voc_type` scheme:

| Code | Label | Source category represented |
| --- | --- | --- |
| `vos` | Voice of Supplier | supplier-authored or supplier-originated record |
| `voe` | Voice of Employee | employee-authored or employee-originated record |
| `vob` | Voice of Business | internal-management or business-unit record |
| `vor` | Voice of Regulator | regulator-authored or regulator-originated record |
| `voi` | Voice of Investor | investor-authored or investor-originated record |
| `voso` | Voice of Society | community or public-stakeholder record |
| `vops` | Voice of Process | process- or system-generated record |

These are governed LineageWeave codes, not a claim that Freeman (1984),
Mitchell et al. (1997), ISO 16355-4, or quality-engineering literature defines
this exact twelve-code list. The cited works support distinguishing stakeholder
voices and process evidence; they do not establish an exact term-level
crosswalk. `vocc`, `vom`, and the product's code abbreviations remain existing
local vocabulary.

The scheme stays open to a later evidence-backed extension. Import preserves
the supplied code and provenance; no classifier, keyword rule, default, or
weight assigns one of these values. Missing or unsupported source codes remain
unavailable rather than being forced into a nearby category.

Codes remain globally unique lowercase literals in
`common_lookup_value.lookup_code`.

## Consequences

- `migrations/0235_voice_of_x_post_taxonomy.sql` adds the seven `voc_type`
  values idempotently and does not alter existing rows.
- `docs/ontology/lineageweave-kg.ttl` publishes one SKOS concept for each new
  code under `:postTypeScheme`.
- The ontology round-trip test proves that the migration and published
  vocabulary agree.
- The API's existing lookup-label path supplies filter values and labels; no
  customer-facing explanation exposes database, migration, or classifier
  boundaries.
- The counterparty relationship classifier remains on its independently
  governed six-code vocabulary.

## References

AccountAbility. (2015). *AA1000 stakeholder engagement standard*.
https://www.accountability.org/standards/aa1000-stakeholder-engagement

AccountAbility. (2025). *AccountAbility launches public consultation for the
AA1000 Stakeholder Engagement Standard (AA1000SES v3)*.
https://www.accountability.org/insights/accountability-launches-public-consultation-for-the-aa1000-stakeholder-engagement-standard-aa1000ses-v3

Freeman, R. E. (1984). *Strategic management: A stakeholder approach*.
Pitman.

Heskett, J. L., Jones, T. O., Loveman, G. W., Sasser, W. E., &
Schlesinger, L. A. (1994). Putting the service-profit chain to work.
*Harvard Business Review, 72*(2), 164-174.

International Organization for Standardization. (2017). *Applications of
statistical and related methods to new technology and product development
process—Part 4: Analysis of non-quantitative and quantitative Voice of
Customer and Voice of Stakeholder* (ISO Standard No. 16355-4:2017).
https://www.iso.org/standard/62607.html

International Organization for Standardization. (2023, December 19).
*Global Directory stakeholder categories*.
https://helpdesk-docs.iso.org/article/331-gd-stakeholders-categories

International Organization for Standardization. (2010). *Guidance on social
responsibility* (ISO Standard No. 26000:2010).
https://www.iso.org/standard/42546.html

Mitchell, R. K., Agle, B. R., & Wood, D. J. (1997). Toward a theory of
stakeholder identification and salience: Defining the principle of who and
what really counts. *Academy of Management Review, 22*(4), 853-886.
https://doi.org/10.5465/amr.1997.9711022105

Shewhart, W. A. (1931). *Economic control of quality of manufactured
product*. D. Van Nostrand.
