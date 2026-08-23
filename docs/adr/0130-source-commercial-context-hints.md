# ADR 0130: Source commercial-context combination hints

## Status

Accepted

## Decision

The import boundary accepts explicit mappings for source customer, order-pool,
sales-order, sales-order-item, and inspection/status-point fields. Raw values
are retained on `source_post` with their source-state fields; the importer does
not infer a catalog identity or a lifecycle label from a code.

The product computes a small combination code from field presence. For the
sales-order-item field, a positive numeric value is present and the source
zero sentinel is absent. Combination labels such as
`customer_only_candidate` and `no_sales_identifier_candidate` are explicitly
inferred candidates, not facts. The exact raw lifecycle vector remains visible
alongside the inference.

The same bounded hint is passed to contextual-orchestrator, Ask Agent evidence,
and the post knowledge-graph view. Customer-name resolution continues through
the existing corroborated customer-hint path; a raw customer code never creates
a catalog entity by itself.

## Rationale

Independent null rates cannot distinguish a customer-only record from an
order-pool record or an order item. The current source distribution shows that
the four presence bits form multiple materially different populations. Keeping
the combination deterministic, provenance-bearing, and weakly labeled gives
lineage reconstruction and readers the useful distinction without turning
unknown SAP codes into invented semantics.
