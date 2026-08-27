# LineageWeave MCP manual

LineageWeave exposes authenticated, asynchronous Global Ask over Streamable
HTTP. MCP and the browser use the same durable Ask jobs, access rules, status
values, citations, related public sources, limitations, and knowledge cutoff.

## Before connecting

Ask the deployment operator for:

- the HTTPS MCP resource URL;
- the exact OAuth resource audience and required scopes; and
- an access token issued for that resource to a provisioned LineageWeave
  account with record-read permission.

Do not reuse a browser client secret, provider credential, or analysis-service
key as an MCP credential. Clients must preserve the `Mcp-Session-Id` returned
by initialization and send it on subsequent requests.

For local synthetic testing only, the optional Compose profile exposes
`http://localhost:18001/mcp`. Start it after the operator has supplied quota
values derived from that deployment's k6 evidence:

```bash
MCP_RATE_LIMIT_REQUESTS=<measured-count> \
MCP_RATE_LIMIT_WINDOW_SECONDS=<measured-window> \
docker compose --profile mcp up -d mcp
```

## Tools

### `submit_global_ask`

Queues a question and returns without waiting for analysis.

| Argument | Required | Meaning |
| --- | --- | --- |
| `question` | yes | The question to answer from authorized evidence. |
| `verify_external` | no | Compare eligible public claims with public sources. Defaults to `false`. |
| `knowledge_cutoff` | no | ISO-8601 cutoff; evidence later than this instant is excluded. |

Save the returned `ask_job_id`. Submission is not an answer and clients must
not repeat it merely because the job remains queued or running.

### `read_global_ask_job`

Reads one job owned by the authenticated account.

| Argument | Required | Meaning |
| --- | --- | --- |
| `ask_job_id` | yes | UUID returned by `submit_global_ask`. |

Poll with bounded backoff until the status is terminal. A completed result can
include cited records, event cards, images, report and alert delivery, and
`cited_source_references`. Open only the returned URLs; absence of a title or
URL is an unavailable source, not permission to synthesize one.

## Status and recovery

| Observation | Client action |
| --- | --- |
| queued or running | Keep the job id and poll later with bounded backoff. |
| succeeded | Render the persisted answer and keep citations linked to their record ids. |
| failed | Show the returned safe failure detail and allow a new submission after the operator restores the dependency. |
| 401 | Renew the resource token, initialize a new MCP session, and retry the read. |
| 403 | Request the required permission or affiliation; do not broaden the query locally. |
| not found | Confirm the job id and account. Jobs are owner-scoped. |
| rate limited | Wait for the returned `Retry-After` interval. |
| limiter unavailable | Retry later; the service cannot safely admit the call. |

Never infer a completed result from a transport timeout. Re-read the saved job
id after connectivity returns.

## Response handling

- Preserve each citation's record id and event-clock metadata when rendering
  the answer.
- Render related public sources only from the persisted citation payload.
- Treat an unavailable TEPP or topic/importance measurement as unavailable;
  do not manufacture a score, weight, or journey edge.
- Do not log bearer tokens, prompts, answers, source text, provider responses,
  tenant identifiers, or raw MCP session ids.
- Keep provider selection outside the MCP client. LineageWeave accepts no
  client-selected provider model.

## End-to-end capacity check

Use the repository's synthetic harness with explicit observation bounds:

```bash
LINEAGEWEAVE_VUS=<concurrency> \
LINEAGEWEAVE_DURATION=<duration-with-unit> \
LINEAGEWEAVE_REQUEST_TIMEOUT=<timeout-with-unit> \
make load-mcp
```

The output is deployment evidence, not a universal SLO. Set production quota
values only from a representative run whose environment, concurrency,
duration, job-state counts, and bottleneck observations are retained outside
the repository without source records or identifiers.

See the [operations manual](operations-manual.md) for deployment and recovery.
