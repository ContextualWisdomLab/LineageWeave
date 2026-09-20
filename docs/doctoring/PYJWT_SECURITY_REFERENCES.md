# PyJWT security-floor references

## Decision trace

LineageWeave declares `pyjwt[crypto]>=2.13.0` for both the `dev` and `backend` install surfaces. The committed resolver state already selects PyJWT 2.13.0. The floor is a security invariant rather than a convenience upgrade: GitHub Reviewed advisories identify 2.13.0 as the patched release for the 2026 algorithm-policy, JWKS-refresh, detached-JWS decoding, and mixed HMAC/asymmetric-family findings listed below.

The owned verification paths additionally keep an explicit `RS256`-only allow-list. That defense-in-depth constraint directly avoids the mixed-family precondition described by CVE-2026-48526; it does not replace the dependency floor.

Executable traceability lives in `tests/test_pyjwt_security_floor_contract.py`, which binds the declared floor, committed lock, and owned verifier allow-lists.

## References (APA 7th)

GitHub. (2026, May 21). *PyJWT: Algorithm allow-list bypass when decoding with PyJWK / PyJWKClient keys* (CVE-2026-48523; GHSA-jq35-7prp-9v3f). GitHub Advisory Database. https://github.com/advisories/GHSA-jq35-7prp-9v3f

GitHub. (2026, May 21). *PyJWKClient unbounded JWKS endpoint requests via attacker-controlled kid values (DoS)* (CVE-2026-48524; GHSA-fhv5-28vv-h8m8). GitHub Advisory Database. https://github.com/advisories/GHSA-fhv5-28vv-h8m8

GitHub. (2026, May 21). *PyJWT: Unauthenticated DoS via unbounded Base64URL decoding of unused payload segment in b64=false detached JWS* (CVE-2026-48525; GHSA-w7vc-732c-9m39). GitHub Advisory Database. https://github.com/advisories/GHSA-w7vc-732c-9m39

GitHub. (2026, May 21). *PyJWT: Public-key JWK accepted as HMAC secret enables forged HS256 tokens when mixed families are allowed* (CVE-2026-48526; GHSA-xgmm-8j9v-c9wx). GitHub Advisory Database. https://github.com/advisories/GHSA-xgmm-8j9v-c9wx

## Evidence interpretation

- CVE-2026-48523: GitHub Reviewed lists PyJWT `>=2.9.0, <2.13.0` as affected and 2.13.0 as patched.
- CVE-2026-48524: GitHub Reviewed lists `>=2.0.0, <=2.12.1` as affected and 2.13.0 as patched.
- CVE-2026-48525: GitHub Reviewed lists the vulnerable line through 2.12.1 and 2.13.0 as patched.
- CVE-2026-48526: GitHub Reviewed lists `<2.13.0` as affected and 2.13.0 as patched. Exploitation requires a verifier that mixes HMAC and asymmetric algorithms with a public JWK used as the HMAC secret; LineageWeave's owned verifier contract remains `RS256`-only.
