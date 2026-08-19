# Actual runtime evidence: Vision capability boundary (2026-08-19)

This note records aggregate local Compose observations only. It contains no
access token, API key, source title, organization name, post id, or image body.

## Verified observations

| Check | Observed result |
| --- | --- |
| contextual-orchestrator text route | Synthetic text request returned HTTP 200 with a choice. |
| contextual-orchestrator Vision route | A valid synthetic PNG request through the local VLM gateway returned HTTP 200 with one choice and usage metadata. |
| backend Vision client | `orchestrator_vision_client` returned a caption and three tags through the same orchestrator route. |
| text-provider capability probe | The separate text-only gateway returned HTTP 404 with `Only 'text' content type is supported.` for a multimodal request. |
| Vision model bootstrap | Vision requests omit a model; contextual-orchestrator selects the registered vision-capable agent. |
| local VLM executable | `mlx-vlm 0.6.15` served `gemma-4-e4b-it-4bit` on `http://host.docker.internal:18082/v1`. |

The successful check used a shell override for the VLM gateway. Persistent
configuration must set `LLM_GATEWAY_API_URL` to that multimodal endpoint and
provide `LLM_GATEWAY_API_KEY`; `LLM_GATEWAY_URL` remains a compatibility
fallback. Vision is considered available only after a real multimodal request
succeeds through `contextual-orchestrator`. The text-only gateway failure is
not converted into OCR, a caption, or a placeholder success.
