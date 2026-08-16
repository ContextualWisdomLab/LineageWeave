# Home-list accessible-name standards and research traceability

**Status:** Active PR evidence; not protected-main truth until merge.  
**Scope:** Calendar, period-report, comparison, and post-list buttons on
the product home page (ADR 0024). Analysis-run list names remain ADR 0014.

## Standards mapped to implementation

| Source | Product implication | Implemented evidence |
|---|---|---|
| W3C Accessible Name and Description Computation 1.1 | `aria-label` replaces descendant text; the name must include every visible fact the operator uses to choose a row. | `calendarCommitmentAccessibleName`, `reportPeriodAccessibleName`, `reportPostAccessibleName`, `reportCompareAccessibleName`, and `postListAccessibleName` in `frontend/src/App.tsx`. |
| WCAG 2.2 Success Criterion 4.1.2 Name, Role, Value | A button's programmatic name must identify the control. | Tests lock the Demo Corp due date, report θ, FIPC delta, and VOC/visibility labels in `getByRole` names. |
| ISO 8601-1:2019 | Due dates stay calendar dates, not localized prose. | Seeded commitments use `due 2026-01-12` / `due 2026-01-14`. |
| AERA, APA, & NCME (2014) *Standards* | Report θ remains a labeled estimate from TEPP/fast-mlsirm persistence; this slice does not invent a score. | AccName repeats the already-calibrated `theta_eap` / `mean_theta` the API returned. |

## Verification matrix

| Claim | Falsifiable test |
|---|---|
| Calendar name includes due date | `Open commitment for: Public post. … due 2026-01-12` is the button name. |
| Period name includes θ and FIPC delta | `Open report period 2026-W03. mean θ 0.92. vs 2026-W02: +0.92. …` is the button name. |
| Shared-metric week does not invent a delta | `Open report period 2026-W02. mean θ 0.00. shared metric. …` is the button name. |
| Report post name includes θ and ticket | `Open report post: Public post. θ 0.91. Send Northridge Grid the revised quote. Open. due 2026-01-12`. |
| Comparison uses the kind label, not the wire code | `Compare Process unit: Demo Report High. mean θ 0.81. 4 posts`. |
| Post list includes VOC and visibility | `View post: Public post. Voice of Customer. Public.` |

## APA 7th references

American Educational Research Association, American Psychological
Association, & National Council on Measurement in Education. (2014).
*Standards for educational and psychological testing*. American
Educational Research Association.

International Organization for Standardization. (2019). *ISO 8601-1:2019:
Date and time—Representations for information interchange—Part 1: Basic
rules* (confirmed 2024; Amendment 1:2022).

World Wide Web Consortium. (2018). *Accessible name and description
computation 1.1* (W3C Recommendation).
https://www.w3.org/TR/accname-1.1/

World Wide Web Consortium. (2023). *Web content accessibility
guidelines (WCAG) 2.2* (W3C Recommendation).
https://www.w3.org/TR/WCAG22/
