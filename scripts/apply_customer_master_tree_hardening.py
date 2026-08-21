#!/usr/bin/env python3
"""Apply the bounded Customer Master tree integration to PR #258."""

from __future__ import annotations

from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    """Replace one exact source region and fail closed when the expected head drifted."""
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def patch_app() -> None:
    """Replace the in-file tree implementation with the tested reusable component."""
    path = Path("frontend/src/App.tsx")
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '  type CustomerMasterEntity,\n',
        "",
        "remove obsolete CustomerMasterEntity import",
    )
    text = replace_once(
        text,
        'import { BuyerNav, type BuyerDestination } from "./components/BuyerNav";\n',
        'import { BuyerNav, type BuyerDestination } from "./components/BuyerNav";\n'
        'import { CustomerMasterTree, CustomerRelatedPostCard } from "./components/CustomerMasterTree";\n',
        "add CustomerMasterTree import",
    )

    tree_start = text.index("interface CustomerEntityTreeNode {")
    panel_start = text.index("function CustomerMasterPanel({", tree_start)
    text = text[:tree_start] + text[panel_start:]

    for state_line in (
        '  const [expandedEntityId, setExpandedEntityId] = useState<string | null>(null);\n',
        '  const [relatedByEntity, setRelatedByEntity] = useState<Record<string, RelatedNode[]>>({});\n',
        '  const [relatedLoading, setRelatedLoading] = useState<string | null>(null);\n',
    ):
        text = replace_once(text, state_line, "", f"remove state {state_line.strip()}")

    toggle_start = text.index("  async function toggleEntity(entityId: string) {")
    return_start = text.index("\n\n  return (", toggle_start)
    text = text[:toggle_start] + text[return_start + 2 :]

    hierarchy_start_marker = "      {master && master.corporate_entities.length > 0 ? (\n"
    hierarchy_start = text.index(hierarchy_start_marker, text.index("function CustomerMasterPanel"))
    relationship_start = text.index(
        "      {master && (master.relationship_network ?? []).length > 0 ? (",
        hierarchy_start,
    )
    hierarchy_replacement = """      {master && master.corporate_entities.length > 0 ? (
        <CustomerMasterTree
          entities={master.corporate_entities}
          loadRelated={(entityId) =>
            fetchRelatedEntity(accessToken, entityId).then((response) => response.related)
          }
          onOpenPost={onOpenPost}
        />
      ) : null}
"""
    text = text[:hierarchy_start] + hierarchy_replacement + text[relationship_start:]
    path.write_text(text, encoding="utf-8")


def patch_storybook_inventory() -> None:
    """Register the buyer-facing customer hierarchy component."""
    path = Path("docs/storybook-inventory.md")
    text = path.read_text(encoding="utf-8")
    anchor = "| `Analysis/LineageEntityPicker` | Choose which corp to reconstruct, then click Request a lineage reconstruction. | `--space-control-gap`, `--size-control-min`, `--radius-control`, `LineageEntityPicker` |\n"
    row = "| `Customers/CustomerMasterTree` | Traverse Group → Company → Plant, open source-backed posts, and review unresolved hierarchy relations. | `--space-control-gap`, `--size-control-min`, `--radius-control`, `CustomerMasterTree` |\n"
    text = replace_once(text, anchor, anchor + row, "storybook inventory row")
    path.write_text(text, encoding="utf-8")


def patch_gap_baseline() -> None:
    """Update PRD/NFR traceability and record the closed buyer gap."""
    path = Path("docs/product-technical-gap-baseline.md")
    text = path.read_text(encoding="utf-8")
    header_start = text.index("**Snapshot:**")
    purpose_start = text.index("**Purpose:**", header_start)
    header = """**Snapshot:** 2026-08-21 (Asia/Seoul)
**Protected-main baseline:** `origin/main`; this document does not claim the active PR is shipped.
**Audited PR head:** #258 code commit `__TREE_CODE_SHA__` for customer-master hierarchy hardening.
**Active PR update:** Customer Master now has a cycle-safe, accessible hierarchy projection; exact-head
frontend and Storybook verification is required before merge.
"""
    text = text[:header_start] + header + text[purpose_start:]

    fr_anchor = "| FR-12 | A hierarchy-enrichment timeout leaves the source-grounded summary readable and the actor unbound; it never creates a guessed catalog identity. | ADR 0101, ADR 0010, ADR 0026 | Commit `1c260f20` contains the boundary, ADR, and focused test; independent review, protected-main merge, and fresh runtime evidence remain pending |\n"
    fr_row = "| FR-13 | Customer Master projects authorized corporate entities as a Group → Company → Plant tree. Missing-parent, self-parent, and cyclic edges remain visible as unresolved roots; the UI supports WAI-ARIA tree keyboard navigation and opens source-backed posts independently from hierarchy disclosure. | ADR 0124, ADR 0004, ADR 0010 | `customerMasterTree.ts`, `CustomerMasterTree.tsx`, pure/component tests, and Storybook on code commit `__TREE_CODE_SHA__` |\n"
    text = replace_once(text, fr_anchor, fr_anchor + fr_row, "FR-13 traceability")

    nfr_anchor = "| NFR-06 | ADR-first architectural change and paper-grounded model policy | ADR link check and review; unsupported policies remain unavailable |\n"
    nfr_row = "| NFR-07 | Buyer hierarchy controls meet WCAG 2.2 keyboard operation and the WAI-ARIA tree interaction contract without inventing ontology facts | Customer-tree component tests, lint, build, and Storybook exact-head verification |\n"
    text = replace_once(text, nfr_anchor, nfr_anchor + nfr_row, "NFR-07 traceability")

    active_anchor = "## Active PR audit\n"
    closed_section = """## Closed gap evidence

| Closed gap | Root cause | Closure evidence | Remaining boundary |
|---|---|---|---|
| Customer entities could disappear from the buyer surface when `parent_entity_id` formed a self-parent or cycle, and the visual nesting lacked a real tree keyboard contract. | The UI recursively assembled only root-reachable nodes and reused `aria-expanded` for related-post evidence rather than hierarchy state. | Code commit `__TREE_CODE_SHA__` promotes malformed edges to visible unresolved roots, separates branch/evidence disclosure, and adds pure, component, and Storybook coverage. | The API still exposes one flat parent context; legal, operating, sales, billing, and time-valid hierarchies require a later normalized relation model. |

"""
    text = replace_once(text, active_anchor, closed_section + active_anchor, "closed gap evidence")
    path.write_text(text, encoding="utf-8")


def main() -> None:
    """Apply every bounded source and documentation edit."""
    patch_app()
    patch_storybook_inventory()
    patch_gap_baseline()


if __name__ == "__main__":
    main()
