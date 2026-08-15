# Integrations

| Integration | Boundary | Runtime setting | Status |
| --- | --- | --- | --- |
| PostgreSQL | direct `psycopg` source and analysis tables | `LINEAGEWEAVE_DSN`, `LINEAGE_SOURCE_TABLE` | live-tested |
| Keyverse | OIDC authorization-code/PKCE and verified actor claims | `KEYVERSE_ISSUER`, `LINEAGEWEAVE_OIDC_*` | compose runtime hard-resets issuer/client/redirect/ca to empty in product profile; operator Keyverse required for login |
| Keyverse Admin REST | Server-only same-corp account claim and `lineageweave-web` client-role reconciliation for the admin mode | `KEYVERSE_ADMIN_TOKEN_URL`, `KEYVERSE_ADMIN_USERNAME`, `KEYVERSE_ADMIN_PASSWORD` | live adapter; first admin/client role remains Keyverse bootstrap responsibility; secrets never reach React |
| LLM gateway | HTTPS task-specific JSON adapters | `LLM_GATEWAY_URL`, `LLM_GATEWAY_API_KEY` or `NVIDIA_NIM_API_KEY`; Compose reads `${LINEAGEWEAVE_ENV_FILE:-$HOME/.env}` | live health/models endpoint tested |
| contextual-orchestrator | HTTP-compatible worker boundary only | `ORCHESTRATOR_BASE_URL`, worker URL settings | startup rechecks (read-only) run in `run_real_lineageweave.sh`; PRs #563/#566 have passing technical checks but remain review-required, so open-branch behavior is not treated as merged integration |
| Valkey | transactional outbox to Stream | `LINEAGEWEAVE_VALKEY_URL` | Compose-configured |
| SearXNG | organization-only external evidence for verification and contextual alias cross-check | `LINEAGEWEAVE_SEARXNG_URL` | Compose image and live JSON search health-tested; canonical aliases are accepted only when cited results contain both alias and canonical text; optional and fail-closed outside Compose |
| Zotero | local read API plus Connector metadata/original-attachment writes | `LINEAGEWEAVE_ZOTERO_API`, `LINEAGEWEAVE_ZOTERO_ATTACHMENTS` | 13 parents and 13 bounded originals stored; outcome/digest persisted, including four multimodal document-analysis papers and the RAGAS evaluator |
| fast-mlsirm | report-score HTTP or sibling local connector | `LINEAGEWEAVE_MLSIRM_URL`, `LINEAGEWEAVE_MLSIRM_PYTHON` | real-data local connector verified; production deployment should require the package path and preserve its Rust/GPU boundary |
| report scoring resilience | bounded retries and budgeted attempts for weekly/monthly judge loop | `LINEAGEWEAVE_REPORT_JUDGE_MAX_ATTEMPTS`, `LINEAGEWEAVE_REPORT_JUDGE_TOTAL_ATTEMPTS` | bounded by default; set total attempts to `0` to keep legacy full-retry behavior |
| RAGAS-aligned report evaluation | live evidence-scoped LLM Judge returns factor items plus four normalized evaluation metrics | `analysis_evaluation_metrics`, `analysis_report_metric_scores`, `analysis_report_metric_evidence` | 80/80 report slices re-evaluated; 320 metric rows and 2,440 normalized evidence rows persisted |
| Evidence-bound factor-item catalog | live LLM derives candidate dichotomous items from supplied writings; Rust-backed fast-mlsirm calibrates the item bank | `analysis_factor_items`, `analysis_factor_item_evidence`, `analysis_factor_item_calibrations` | 10 fixed anchors + 5 LLM candidates, 10 evidence links, 15 finite calibration rows; 290 linked scores across 58 slices and 22 explicit unlinked slices |
| Figma | design reference only | none | reference frame recorded in `design-qa.md` |

TEPP and contextual-orchestrator internals are not imported or copied into this product.

## Evidence

- `lineageweave.py`
- `lineageweave_server.py`
- `compose.yaml`
- `compose/http_standin.py`
- `compose/keyverse_oidc.py` (offline OIDC test utility only; compose image does not ship/run it as an IdP)
- `design-qa.md`
