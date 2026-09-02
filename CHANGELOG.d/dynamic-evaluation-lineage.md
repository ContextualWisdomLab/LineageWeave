## Added

- Added the versioned `lineageweave_dynamic_evaluation_lineage/v1` projection for dynamically resolved evaluation item and run snapshots.
- Preserved generator, rater, adjudication-case/resolution, calibration, anchor-promotion, linking, and supersession references as separate immutable evidence instead of overwriting source observations or inventing decision authority.
- Permitted zero-anchor cold-start and within-run projections while requiring separate calibration, promotion, and linking evidence before an item/run can be represented as an anchor or cross-version linked.
- Rejected provider credentials/endpoints, scores, embedded adjudication decisions, mixed-blueprint item sets, duplicate identities, unsupported linking claims, and invisible Unicode format controls in opaque provenance references at the LineageWeave Anti-Corruption Layer.
