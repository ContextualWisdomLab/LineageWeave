# CLAUDE.md

Read [AGENTS.md](AGENTS.md) first. This file is a pointer, not a second
policy.

LineageWeave is a synthetic-data BI prototype. Do not add real
organization records. Reuse ThreadWeave, RankWeave, TEPP, and
contextual-orchestrator rather than reimplementing them.

Frontend walk chips and tokens: [ADR-0016](docs/adr/0016-storybook-and-design-tokens.md)
and [docs/storybook-inventory.md](docs/storybook-inventory.md). Run
`cd frontend && pnpm run storybook` to compare unique, plural, and
missing affiliation captions before walking a seeded graph.
