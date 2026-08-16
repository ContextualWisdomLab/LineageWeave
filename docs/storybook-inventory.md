# Storybook inventory

Open the walk chips before you seed a graph:

```bash
cd frontend && pnpm install && pnpm run storybook
```

Then compare the three affiliation states. Click a person or
organization chip to rehearse the next walk. When the caption says
`multiple organizations`, open the Keyman list. Click the post chip
to open that source.

| Story | Caption a buyer should see | Next action |
|---|---|---|
| `Walk/RelatedNodeChip/UniqueAffiliation` | `Ada West, Demo Corp (Our side)` | Continue the walk to Ada |
| `Walk/RelatedNodeChip/PluralAffiliations` | `Priya Nair, multiple organizations (Counterparty)` | Open the Keyman list |
| `Walk/RelatedNodeChip/MissingAffiliation` | `Priya Nair (Counterparty)` | Continue the walk; no org is known |
| `Walk/RelatedNodeChip/OrganizationLevel` | `Demo Corp (Company)` | Continue the walk to Demo Corp |
| `Walk/RelatedNodeChip/RelatedPost` | `Linked post` | Open that source post |

Tokens for these chips live in
`frontend/src/tokens/design-tokens.json` (ADR-0016). Do not add a
one-off hex for a repeating chip, panel, or radius.

Figma remains optional and must not import real-organization frames
(ADR 0002). Storybook is the public visual inventory.
