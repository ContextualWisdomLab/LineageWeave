# External lineage analysis v1 limitations

- The contract does not read IMAP, JMAP, CalDAV, Naruon, or other provider systems.
- It does not authenticate users, authorize tenant access, persist jobs, or retry remote work.
- It does not make semantic lineage equivalent to RFC reply/thread identity.
- It does not turn project groupings, responsibility context, or reconstructed edges into authoritative caller facts.
- It does not infer unavailable evidence as a zero-valued channel.
- It does not guarantee causal relations; reconstructed continuation is an evidence-weighted related-history hypothesis.
- Canonical request/result serialization and digests are deterministic, but an optional remote adjudication channel is not automatically repeatable unless the consumer pins the LineageWeave artifact, adjudicator, provider/model revision, and determinism policy.
- Contract v1 does not carry a remote provider/model receipt inside the result; production wrappers must retain that provenance alongside the result digest before model-backed integration is enabled.
- It does not replace Naruon's canonical email identity, project/task/commitment state, provider mutation, or reconciliation authority.
