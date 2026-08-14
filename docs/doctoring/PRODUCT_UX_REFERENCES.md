# Product UX and access-control references

Reviewed: **2026-08-14**

This bibliography records the primary standards used by the DB-grounded
product UX contract. It does not claim certification. Implementation evidence
must be produced by tests, accessibility review, security controls, operating
records, and the applicable assessor.

## Normative and authoritative sources — APA 7th

Campbell, A., Adams, C., Bradley Montgomery, R., Cooper, M., & Kirkpatrick,
A. (Eds.). (2024). *Web Content Accessibility Guidelines (WCAG) 2.2*
(W3C Recommendation, 12 December 2024). World Wide Web Consortium.
https://www.w3.org/TR/2024/REC-WCAG22-20241212/

Chandramouli, R., & Butcher, Z. (2023). *A zero trust architecture model for
access control in cloud-native applications in multi-cloud environments*
(NIST Special Publication 800-207A). National Institute of Standards and
Technology. https://doi.org/10.6028/NIST.SP.800-207A

Diggs, J., Nurthen, J., Cooper, M., & MacLeod, C. (Eds.). (2023).
*Accessible Rich Internet Applications (WAI-ARIA) 1.2*
(W3C Recommendation, 6 June 2023). World Wide Web Consortium.
https://www.w3.org/TR/2023/REC-wai-aria-1.2-20230606/

International Organization for Standardization, & International
Electrotechnical Commission. (2023). *Systems and software engineering —
Systems and software Quality Requirements and Evaluation (SQuaRE) — Product
quality model* (ISO/IEC 25010:2023, 2nd ed.).
https://www.iso.org/standard/78176.html

International Organization for Standardization, & International
Electrotechnical Commission. (2025). *Information technology — W3C Web
Content Accessibility Guidelines (WCAG) 2.2* (ISO/IEC 40500:2025, 2nd ed.).
https://www.iso.org/standard/91029.html

Joint Task Force. (2020). *Security and privacy controls for information
systems and organizations* (NIST Special Publication 800-53, Revision 5,
including Update 1). National Institute of Standards and Technology.
https://doi.org/10.6028/NIST.SP.800-53r5

Rose, S., Borchert, O., Mitchell, S., & Connelly, S. (2020). *Zero trust
architecture* (NIST Special Publication 800-207). National Institute of
Standards and Technology. https://doi.org/10.6028/NIST.SP.800-207

## Currency notes

- The current W3C Recommendation for WCAG 2.2 is dated 12 December 2024.
- ISO/IEC 40500:2025 was published in September 2025 as the international
  standard edition of WCAG 2.2. ISO lists an edition 3 draft under development,
  so the implementation should continue to track W3C and ISO publication
  status rather than freezing an accessibility program around a label.
- ISO/IEC 25010:2023 is the published second edition of the product quality
  model and replaces the 2011 edition.
- NIST issued SP 800-53 Release 5.2.0 on 27 August 2025. Control mappings must
  name the exact catalog release used by an assessment.

## Implementation traceability

| Source | LineageWeave design or control |
|---|---|
| WCAG 2.2 | Keyboard operation, focus order and visibility, target size, contrast, accessible authentication, error identification, status messages |
| WAI-ARIA 1.2 | Accessible names, roles, states, dialog/evidence-drawer semantics, non-visual graph navigation |
| ISO/IEC 25010:2023 | Functional suitability, interaction capability, reliability, security, maintainability, flexibility, and acceptance criteria |
| NIST SP 800-207 | Authentication is not sufficient authorization; access is resource- and identity-focused |
| NIST SP 800-207A | Application-level identity and granular policy enforcement for modular services |
| NIST SP 800-53 Rev. 5 | Access control, identification and authentication, audit, configuration, system integrity, supply-chain, and privacy control families |

## Product-specific decisions grounded by the sources

1. The account screen separates identity, affiliation, role assignment, and
   derived permissions because each has a distinct persistence and control
   meaning.
2. The row-level rule is evaluated after coarse permission membership; a valid
   token alone never grants record access.
3. Graph interactions require an equivalent semantic list or tree so SVG
   position is not the only way to understand or operate the lineage.
4. Account lifecycle and access-audit interfaces remain absent until the
   persistence and immutable audit evidence exist.
5. Explanatory copy names the available next action and does not assert causal
   or historical facts absent from stored evidence.
6. Product quality acceptance is tied to testable contracts, not visual
   similarity alone.

## Certification boundary

CSAP, SOC 2, and other assurance programs require organizational evidence
beyond repository code. This repository can provide technical controls and
traceability, but it must not claim certification from implementation alone.
A deployment readiness package should map the exact deployed configuration,
operating procedures, evidence retention, access review, incident handling,
supplier controls, and assessor scope.
