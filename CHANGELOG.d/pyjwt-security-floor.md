# Security

- Raise both LineageWeave PyJWT install surfaces to `pyjwt[crypto]>=2.13.0`, matching the committed resolver state and excluding the 2026 PyJWT releases affected by CVE-2026-48523, CVE-2026-48524, CVE-2026-48525, and CVE-2026-48526. Keep owned JWT verification paths on an explicit RS256-only allow-list rather than mixed symmetric/asymmetric algorithm families.
