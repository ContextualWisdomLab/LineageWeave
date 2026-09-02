## Added

- Added the versioned `lineageweave_dynamic_evaluation_lineage/v1` projection for dynamically resolved evaluation item and run snapshots.
- Preserved generator, rater, adjudication-case/resolution, calibration, anchor-promotion, linking, and supersession references as separate immutable evidence instead of overwriting source observations or inventing decision authority.
- Permitted zero-anchor cold-start and within-run projections while requiring separate calibration, promotion, and linking evidence before an item/run can be represented as an anchor or cross-version linked.
- Rejected provider credentials/endpoints, scores, embedded adjudication decisions, mixed-blueprint item sets, duplicate identities, unsupported linking claims, Unicode format controls, Unicode line/paragraph separators, and the 66 Unicode noncharacters in opaque provenance references at the LineageWeave Anti-Corruption Layer. Other unassigned `Cn` code points are not rejected merely for being unassigned.
- Rejected directed cycles among in-run supersession references and bounded cycle admission to linear graph work at the 10,000-item contract limit without claiming a runner-specific wall-clock SLO.
