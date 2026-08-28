# External lineage analysis v1 security boundary

The contract is an analysis interface, not an authorization interface.

## Caller responsibilities

- authenticate the caller and authorize every submitted evidence record;
- enforce tenant, workspace, purpose, retention, and export policy;
- minimize text and participant evidence according to data classification;
- retain provider credentials, raw access tokens, browser sessions, and unrelated mailbox content inside the caller boundary;
- pin and record the immutable LineageWeave artifact used for an analysis;
- retain adjudicator and provider/model provenance beside any model-backed result;
- verify the returned contract version and result digest before persistence or display.

## LineageWeave boundary

- rejects unsafe opaque references, unknown fields, invalid timestamps, duplicate evidence, and over-budget inferred work;
- returns only references present in the admitted request from the supported analysis adapter;
- distinguishes observed caller relations from inferred reconstruction;
- does not rescore or disclose a caller-observed child to the optional LLM merely to generate an alternative edge that would be discarded;
- never promotes a proposed project projection to caller authority;
- performs no provider mutation and receives no provider credential through this contract.
