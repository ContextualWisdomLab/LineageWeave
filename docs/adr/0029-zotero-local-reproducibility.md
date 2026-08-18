# ADR 0029: Local Zotero research reproducibility

Status: accepted

## Decision

Zotero is an optional research-workstation dependency, not a LineageWeave
runtime service. Store literature locally through Zotero's Connector HTTP
server and verify it through the local Web API.

The local Web API at `http://127.0.0.1:23119/api/` is read-only in the current
Zotero release. Do not script writes to `/api/users/0/items`; use
`/connector/saveItems` instead.

The reproducibility seed for the summarization/evidence experiments is:

- title: `Get to the Point: Summarization with Pointer-Generator Networks`
- DOI: `10.18653/v1/P17-1099`
- open PDF: `https://aclanthology.org/P17-1099.pdf`

## Save and verify

With Zotero running and the Connector HTTP server enabled:

```bash
SESSION_ID="lineageweave-p17-1099-$(date +%s)"
curl -fsS -X POST http://127.0.0.1:23119/connector/saveItems \
  -H 'Content-Type: application/json' \
  -H 'X-Zotero-Connector-API-Version: 3' \
  --data "$(jq -cn --arg session_id \"$SESSION_ID\" '{items:[{itemType:\"journalArticle\",title:\"Get to the Point: Summarization with Pointer-Generator Networks\",DOI:\"10.18653/v1/P17-1099\",url:\"https://aclanthology.org/P17-1099.pdf\",publicationTitle:\"Proceedings of the 55th Annual Meeting of the Association for Computational Linguistics\"}],uri:\"https://aclanthology.org/P17-1099/\",sessionID:$session_id}')"

curl -fsS 'http://127.0.0.1:23119/api/users/0/items?limit=100' \
  | jq '.[] | select(.data.DOI == "10.18653/v1/P17-1099") | {key, title: .data.title, DOI: .data.DOI, url: .data.url}'
```

The first command may return an empty `201` response. Connector `items` is an
array, not the keyed object accepted by older examples; a unique `sessionID`
prevents replay collisions. The second command is
the persisted-library check. A missing Zotero instance does not disable the
product or fabricate literature evidence.

## Consequences

- Zotero setup is reproducible without adding a Python or frontend package.
- OA literature remains linked by DOI and URL rather than copied into this
  repository.
- Tests and fixtures do not depend on a user's local Zotero library.
