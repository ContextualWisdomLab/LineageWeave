# Storybook inventory

**Status:** Component inventory for the repeating home-page objects.
Storybook itself is the next frontend toolchain slice; do not add a
second Node package manager while adding it (`frontend/mise.toml`
pins Node 24, Corepack pnpm only).

## Repeating objects

| Object | Module | States a Storybook story must cover |
|---|---|---|
| Analysis run list | `frontend/src/AnalysisRunsPanel.tsx` | empty (`make seed` hint), loading, one succeeded Demo Corp run with snapshot-count badge, hidden-run error |
| Analysis run detail | same | cutoff + requested date, status history, digest prefixes, snapshot-count labels, in-cutoff posts, no posts at cutoff |
| Post list chip | `frontend/src/App.tsx` | public / private badges |
| Calendar commitment | `frontend/src/App.tsx` | dated open ticket |
| Period report row | `frontend/src/App.tsx` | mean θ, CAT item, member click-through |
| Post popup | `frontend/src/App.tsx` | summary, lineage, Keyman, tickets, chat |

## Design tokens

Repeating chips, badges, and list rows must use the CSS custom
properties in `frontend/src/index.css` (`--lw-space-*`,
`--lw-radius-*`, `--lw-color-danger`) rather than one-off hex values
when those objects are next extracted.

## Next action

Add Storybook via `pnpm` in `frontend/` with `@storybook/react-vite`,
then write CSF stories for `AnalysisRunsPanel` first. Keep stories on
synthetic Demo Corp fixtures only.
