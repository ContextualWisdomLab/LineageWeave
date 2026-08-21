# Actual runtime evidence: gateway, Vision, worker (2026-08-18)

This note records aggregate local Compose observations only. It contains no
access token, API key, source title, organization name, post id, or model
response body.

## Verified observations

| Check | Observed result |
| --- | --- |
| Backend health after rebuild | `GET /healthz` returned HTTP 200 with `status=ok`. |
| Text LLM route | A synthetic text request through contextual-orchestrator returned HTTP 200 with one choice, an id, and usage metadata. |
| Vision route | A synthetic 1x1 PNG multimodal request through contextual-orchestrator returned HTTP 200 with one choice, string message content, an id, and usage metadata. |
| Analysis-run worker | The backend image rebuilt and started with the Valkey stream consumer enabled; no worker exception appeared in the bounded post-start backend log sample. |
| Durable wake-up stream | Valkey contained the `analysis-run-outbox` stream with 107 entries at observation time. |
| Python suite after worker addition | `549 passed, 16 skipped, 4 warnings`. |

The text and Vision calls used synthetic prompts and image bytes. The
application still routes provider credentials through contextual-orchestrator;
this note deliberately does not record them.
