# Integration contracts

LineageWeave publishes strict, versioned contracts for separately governed consumers. These contracts do not grant source access and do not replace each consumer's authorization, persistence, provider, or audit authority.

## External lineage analysis v1

- JSON Schema: `external-lineage-analysis-v1.schema.json`
- Synthetic request: `external-lineage-analysis-v1.example.json`
- Python parser and immutable types: `lineageweave.external_lineage_contract`
- Store-agnostic execution adapter: `lineageweave.external_lineage_analysis`
- Decision record: `docs/adr/0214-external-email-project-lineage-contract.md`

A consumer must submit only bounded evidence it is already authorized to disclose. Outputs retain opaque caller references and explicit `observed`, `inferred`, or `proposed` truth boundaries. The contract performs no source-system access or provider mutation.
The execution adapter additionally requires an ADR-0200-compliant calibrated
channel-weight vector supplied by the host; it has no default weights.
