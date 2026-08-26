# ADR 0232: Complete general Voice-of-X taxonomy for post types and counterparty relationships

## Status

Accepted (2026-08-26). Extends ADR 0207 decision 8 (the then-governed
five-value `voc_type` scheme) and the six-code `entity_relationship_type`
vocabulary; supersedes the "vos is relationship-only" asymmetry.

## Context

`source_post.voc_type_code` classifies what a post records, and
`post_counterparty_entity.relationship_type_code` classifies each named
organization's relation to the post author's org. Both draw on a shared
"Voice of X" mental model, but until now only five post types
(`voc`, `vocc`, `voco`, `vom`, `vop`) and six relationship codes
(`rel_voc`, `rel_vocc`, `rel_voco`, `rel_vom`, `rel_vop`, `rel_vos`)
were governed. Real correspondence sources speak with more distinct
voices than those five: staff write about their own workplace, regulators
issue notices, investors comment, communities and media react, suppliers
answer (previously expressible only as a *relationship*, never as a post
type), internal business units report, and automated systems emit process
signal. A closed five-value scheme forced every such record into the
nearest of five buckets or blocked import.

## Decision

Adopt the complete stakeholder-voice taxonomy as the governed vocabulary,
grounded in stakeholder identification theory and quality-engineering
measurement practice:

1. **Stakeholder classes** (Freeman, 1984; Mitchell, Agle, & Wood, 1997)
   enumerate who can hold a voice toward an organization: customers,
   employees, owners/investors, suppliers, government/regulators,
   communities/society, competitors, partners. Each class that can author
   correspondence becomes one `voc_type` code.
2. **Quality-engineering voices** add the two non-personal voices Six
   Sigma measurement practice recognizes alongside Voice of the Customer:
   Voice of the Business (internal management) and Voice of the Process
   -- the system speaking through its own signal (Shewhart, 1931;
   Deming, 1986).
3. **Customer-chain depth** keeps the B2B2C chain extension already
   governed (`vocc`, one hop down the chain per Griffin & Hauser's
   (1993) need-interrogation practice of following the use chain).
4. **Market** stays the aggregate residual voice not attributable to one
   named party (`vom`).

The complete `voc_type` set becomes twelve codes:

| Code | Label | Grounding |
| --- | --- | --- |
| `voc` | Voice of Customer | Griffin & Hauser (1993) |
| `vocc` | Voice of Customer's Customer | chain extension of (1) |
| `voco` | Voice of Competitor | Freeman (1984): competitors |
| `vom` | Voice of Market | aggregate residual signal |
| `vop` | Voice of Partner | Freeman (1984): partners/alliances |
| `vos` | Voice of Supplier | Freeman (1984): suppliers |
| `voe` | Voice of Employee | Heskett et al. (1994), service-profit chain |
| `vob` | Voice of Business | internal-management voice (quality practice) |
| `vor` | Voice of Regulator | Mitchell et al. (1997): government/regulatory salience |
| `voi` | Voice of Investor | Freeman (1984): owners/stockholders |
| `voso` | Voice of Society | Mitchell et al. (1997): community/media stakeholders |
| `vops` | Voice of Process | Shewhart (1931); Deming (1986): process signal |

Mirror each new voice class in `entity_relationship_type` so a post of
any voice class can still type its named counterparties:

| Code | Meaning for the named organization |
| --- | --- |
| `rel_voe` | employee-voice signal involving this organization |
| `rel_vob` | internal-business-unit signal involving this organization |
| `rel_vor` | this organization regulates the post author's org |
| `rel_voi` | this organization invests in / holds capital in the author's org |
| `rel_voso` | community/society-level signal involving this organization |
| `rel_vops` | process/system-generated signal involving this organization |

`rel_vos` already existed and now has its matching post type `vos`.

Deliberate non-proliferation (documented, not invented):

- **Reseller/channel intermediaries stay under Partner.** Distribution
  economics distinguishes resellers from strategic alliances, but both
  are "organizations the author works through"; minting a separate code
  would duplicate evidence without changing any downstream decision.
- **Prospects and churned customers stay under Customer.** In Voice-of-
  Customer practice lost and prospective buyers are customers' voices at
  different lifecycle stages (Griffin & Hauser, 1993 sample across
  current and lost users), not a different stakeholder class.
- **End-user vs buyer within a customer account stays under Customer**
  plus existing person-level Keyman structure; the account-level voice
  class does not change.

Codes remain globally unique lowercase literals in
`common_lookup_value.lookup_code`; relationship codes keep the `rel_`
prefix because bare `voc`-style codes are claimed by the post-type
category itself.

## Consequences

- `migrations/0222_voice_of_x_complete_taxonomy.sql` seeds both
  categories idempotently (`ON CONFLICT ... DO UPDATE`, scoped by
  category, mirroring migration 0042).
- `docs/ontology/lineageweave-kg.ttl` declares seven more SKOS concepts
  under `:postTypeScheme` and six more `owl:ObjectProperty` relationship
  projections; the round-trip test in `tests/test_ontology.py` reads the
  new migration file and no longer asserts the five-value cap or the
  "vos is never a post type" invariant.
- `lineageweave/entity_relationship_classification.py` extends the valid
  code set and the classification prompt; unknown codes are still
  dropped, never guessed.
- Existing rows and stored data are untouched: all seven new codes are
  additive, display orders 5-11 follow the seeded order, and no code is
  renamed or retired.
- The API resolves labels from `common_lookup_value`, so filter options
  and labels flow to clients without frontend changes.

## References

Deming, W. E. (1986). *Out of the crisis*. MIT Press.

Freeman, R. E. (1984). *Strategic management: A stakeholder approach*.
Pitman.

Griffin, A., & Hauser, J. R. (1993). The voice of the customer.
*Marketing Science, 12*(1), 1-27. https://doi.org/10.1287/mksc.12.1.1

Heskett, J. L., Jones, T. O., Loveman, G. W., Sasser, W. E., &
Schlesinger, L. A. (1994). Putting the service-profit chain to work.
*Harvard Business Review, 72*(2), 164-174.

Mitchell, R. K., Agle, B. R., & Wood, D. J. (1997). Toward a theory of
stakeholder identification and salience: Defining the principle of who
and what really counts. *Academy of Management Review, 22*(4), 853-886.
https://doi.org/10.5465/amr.1997.9711022105

Shewhart, W. A. (1931). *Economic control of quality of manufactured
product*. D. Van Nostrand.
