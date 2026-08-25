# External lineage analysis v1 authorization contract

LineageWeave does not infer authorization from an opaque reference, source kind, group, project, or caller identity. The caller must authorize evidence before projection and must reauthorize any source drill-through after receiving a result.

The package does not accept provider bearer tokens, browser cookies, mailbox credentials, database DSNs, or caller SQL. A future remote service must use its own audience-scoped service credential and may not forward an end-user token to model providers.
