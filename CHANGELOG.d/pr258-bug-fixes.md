## Unreleased

- Preserve the buyer board's stacked search and filter layout by removing
  conflicting duplicate CSS rules.
- Keep lineage reconstruction running when an optional adjudication response
  is malformed, and report an admitted LLM as `not_invoked` when no candidate
  pair required a judgment.
