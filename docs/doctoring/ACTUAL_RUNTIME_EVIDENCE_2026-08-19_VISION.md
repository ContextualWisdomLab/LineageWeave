# Actual runtime evidence: Vision capability boundary (2026-08-19)

This note records aggregate local Compose observations only. It contains no
access token, API key, source title, organization name, post id, or image body.

## Verified observations

| Check | Observed result |
| --- | --- |
| contextual-orchestrator text route | Synthetic text request returned HTTP 200 with a choice. |
| contextual-orchestrator Vision route | Synthetic 1x1 PNG request returned HTTP 500 with `internal_error`. |
| provider capability probe | The configured local gateway returned HTTP 404 with `Only 'text' content type is supported.` for the same multimodal request. |
| Vision model bootstrap | An explicit `VISION_MODEL` is now applied only to agents tagged `vision`; text agents keep `LLM_GATEWAY_MODEL`. |
| local VLM executable | `mlx_vlm.server` is installed, but the cached Gemma checkpoint failed its local load with a tensor-shape mismatch before serving requests. |

The application therefore has no valid Vision result in this environment. It
must use a provider/model that accepts OpenAI-compatible `image_url` blocks;
the text-only gateway failure is not converted into OCR, a caption, or a
placeholder success.
