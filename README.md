# LineageWeave

Reconstructs git-branch-style lineage DAGs from scattered short records --
turns a flat pile of loosely-grouped, timestamped items into a browsable set
of branching threads, without any explicit "this follows from that" link
existing in the source data.

```
group A-100
  rec-001  Initial site visit and project scope discussion
      └─ rec-002  Pricing renegotiation follow-up
           ├─ rec-003  Pricing renegotiation: revised quote sent
           └─ rec-004  Delivery schedule question raised
                └─ rec-005  Delivery schedule confirmed with logistics
  rec-006  Unrelated: annual account review   (own root -- no forced match)
```

This is a **demo prototype**: it ships with synthetic sample data only
(`lineageweave/fixtures.py`) and no connection to any real dataset or
organization.

## Why

Given a pile of records with no native cross-record link, no single cheap
signal reliably tells you which record continues which -- see
[`docs/lineage-bi-research-notes.md`](docs/lineage-bi-research-notes.md) for
the validation numbers and the literature this design follows. LineageWeave
fuses several independent, individually-weak signals (temporal proximity, a
shared grouping key, text similarity, and an optional LLM judgment) instead
of trusting any one of them alone.

## How it fits with the rest of the ecosystem

LineageWeave is a thin orchestration/BI layer. It does not do its own
psychometric or statistical estimation -- that stays inside
[TEPP](https://github.com/ContextualWisdomLab/TEPP) (Rust), consumed here
purely through TEPP's own published wire contract
(`lineageweave/tepp_client.py`, `AnalysisRunRequest` v1), never by reading
TEPP's tables or reimplementing TEPP's model. See
[ARCHITECTURE.md](ARCHITECTURE.md) for why the "computation layer must be
Rust + GPU/CPU multithreaded" rule that applies to TEPP does not apply to
this repo.

The optional LLM-adjudication channel calls
[contextual-orchestrator](https://github.com/ContextualWisdomLab/contextual-orchestrator)
(`lineageweave/adjudication_client.py`). Tree assembly reuses
[ThreadWeave](https://github.com/ContextualWisdomLab/ThreadWeave) (JWZ
message threading) and channel fusion reuses
[RankWeave](https://github.com/ContextualWisdomLab/RankWeave) (weighted
score fusion) -- both real dependencies, not reimplemented here.

## Run it

```bash
pip install -e .
python -m lineageweave.server
# -> http://127.0.0.1:8420
```

Or use the library directly:

```python
from lineageweave import reconstruct
from lineageweave.fixtures import sample_records

trees = reconstruct(sample_records())
for tree in trees:
    print(tree.group_key, "branch points:", tree.branch_points())
```

## Bring your own data

Map your records into `lineageweave.Record` (see `lineageweave/models.py`
for the field docs) and call `reconstruct()` directly -- nothing in this
package assumes any particular source schema.

To turn on the embedding or LLM channels, pass a real client instead of the
`Null*` defaults:

```python
from lineageweave import reconstruct
from lineageweave.adjudication_client import ContextualOrchestratorAdjudicationClient

llm = ContextualOrchestratorAdjudicationClient(base_url="http://localhost:8000", api_key="...")
trees = reconstruct(my_records, llm=llm)
```

## Test

```bash
pip install -e ".[dev]"
pytest
```

## Modular / standalone

This repo runs standalone (own server, own tests, own CI) and is equally
usable as a library module (`import lineageweave`) inside a larger service
-- no global state, no required environment variables, every external
dependency (embeddings, LLM adjudication, TEPP) is injected, not hardcoded.

## License

MIT -- see [LICENSE](LICENSE).
