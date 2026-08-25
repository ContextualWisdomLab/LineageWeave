# ADR 0156: Bind Keyverse account claims to one local authorization scope

## Status

Accepted for the next release.

## Context

ADR 0028 validates a production Keyverse token and resolves its `sub` to a
provisioned `user_account`, while keeping affiliations and permissions in the
normalized LineageWeave database. Keyverse ADR 0009 now defines the
`lineageweave-web` relying-party profile more narrowly: `org`, `workspace`, and
the multivalued `role` claim are account-derived and atomic. A consumer must
reject a partial or ambiguous profile before ABAC or RBAC.

Resolving only `sub` permits a valid but stale or differently scoped Keyverse
session to inherit every locally provisioned affiliation and role. Signature
verification alone therefore does not prove the requested authorization scope.

## Decision

When `KEYVERSE_ISSUER` selects the production Keyverse profile:

1. Require non-empty scalar `org` and `workspace` claims and a non-empty,
   duplicate-free list of non-empty scalar `role` values.
   The verified JWT must also contain `exp`, `iat`, and `sub`.
2. Resolve `sub` + `org` + `workspace` to exactly one normalized
   `user_account` / `account_affiliation` / `corporate_entity` / `process_unit`
   row. `org` matches `corporate_entity_code`; `workspace` matches
   `process_unit_code`, and the process unit must belong to that organization.
3. Load permissions only from locally assigned roles whose `role_code` is also
   present in the verified token. The token selects current issuer state; the
   database remains the permission authority.
4. Restrict private post reads to both the selected organization and selected
   process unit. Public records retain their existing visibility contract.
5. Keep local Compose Keycloak compatible with its synthetic development claim
   profile; the stricter account-derived contract activates only for an
   explicitly configured Keyverse issuer.
6. Persist the exact corporate-entity and process-unit scope in normalized
   child tables when asynchronous work is queued. Workers intersect that scope
   with current affiliations; they never reconstruct it from every affiliation
   on the account after the bearer token leaves the request boundary.

Missing, malformed, ambiguous, or unprovisioned scope is denied. No claim is
used to create an affiliation, process unit, role, or permission.

## Consequences

- A membership or role change requires a new token or session renewal and a
  matching local provisioned row.
- A Keyverse token cannot widen access beyond the intersection of issuer claims
  and local 3NF authorization state.
- Multi-membership tokens and delimiter conventions remain unsupported; a
  future profile requires a separate ADR and cross-scope regression evidence.

## References

ContextualWisdomLab. (2026). *ADR 0009: Bind LineageWeave relying-party claims
to Keyverse accounts*. Keyverse.

Lodderstedt, T., Bradley, J., Labunets, A., & Fett, D. (2025). *Best current
practice for OAuth 2.0 security* (RFC 9700). Internet Engineering Task Force.
https://doi.org/10.17487/RFC9700

OpenID Foundation. (2014). *OpenID Connect Core 1.0 incorporating errata set
2*. https://openid.net/specs/openid-connect-core-1_0.html
