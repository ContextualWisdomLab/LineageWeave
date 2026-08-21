#!/usr/bin/env python3
"""Finalize customer-hierarchy evidence after exact code verification."""

from __future__ import annotations

from pathlib import Path

CODE_SHA = "21074cf80cbf"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    """Replace one exact block and fail closed when the baseline has drifted."""
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def replace_row(lines: list[str], prefix: str, replacement: str) -> None:
    """Replace exactly one Markdown table row selected by a stable prefix."""
    indexes = [index for index, line in enumerate(lines) if line.startswith(prefix)]
    if len(indexes) != 1:
        raise RuntimeError(f"{prefix}: expected one row, found {len(indexes)}")
    lines[indexes[0]] = replacement


def main() -> None:
    """Remove stale placeholders and synchronize the current PR/gap evidence."""
    path = Path("docs/product-technical-gap-baseline.md")
    text = path.read_text(encoding="utf-8")
    old_header = """**Audited PR head:** #258 code commit `__TREE_CODE_SHA__` for customer-master hierarchy hardening.
**Active PR update:** Customer Master now has a cycle-safe, accessible hierarchy projection; exact-head
frontend and Storybook verification is required before merge.
"""
    new_header = f"""**Audited PR code head:** #258 customer-hierarchy commit `{CODE_SHA}`; this active branch is not protected-main truth.
**Active PR update:** Customer Master now has an ORG-grounded, cycle-safe hierarchy projection with
explicit WAI-ARIA ownership; final-head hosted Checks and independent approval remain required.
"""
    text = replace_once(text, old_header, new_header, "baseline header")
    text = replace_once(
        text,
        "## Closed gap evidence\n",
        "## Active-PR gap closure evidence\n",
        "gap closure heading",
    )
    old_audit = """GitHub reported 18 open PRs at the snapshot: all were marked Ready and 8
required review; merge state was 8 `BLOCKED`, 8 `UNSTABLE`, and 2 `DIRTY`.
Queued checks and review gates mean none of these rows is protected-main truth.
"""
    new_audit = f"""A focused 2026-08-21 refresh found PR #258 open and mergeable at customer-hierarchy
code commit `{CODE_SHA}`. The organization queue has changed since the 18-row inventory below, so the
table is retained only as historical stack topology. Current acceptance must be read from the final
PR head, valid unresolved threads, qualifying independent review, and terminal hosted Checks.
"""
    text = replace_once(text, old_audit, new_audit, "active PR audit summary")

    lines = text.splitlines()
    replace_row(
        lines,
        "| FR-13 |",
        f"| FR-13 | Customer Master projects authorized corporate entities as a Group → Company → Plant tree. Real organization containment uses W3C ORG while Group/Company/Plant remain separate SKOS level concepts. Missing-parent, self-parent, and cyclic edges remain visible as unresolved roots; the UI owns nested `group` elements from their parent `treeitem`, supports Arrow/Home/End and Enter/Space operation, and opens source-backed evidence outside the tree. | ADR 0124, ADR 0004, ADR 0010 | Ontology/SHACL interoperability tests, `customerMasterTree.ts`, `CustomerMasterTree.tsx`, component tests, Storybook, and code commit `{CODE_SHA}` |",
    )
    replace_row(
        lines,
        "| NFR-07 |",
        "| NFR-07 | Buyer hierarchy controls meet WCAG 2.2 keyboard operation and the WAI-ARIA tree ownership contract without inventing ontology facts | Ontology tests, focused hierarchy tests, full frontend test/lint/build, Storybook build, and final-head hosted verification |",
    )
    replace_row(
        lines,
        "| Customer entities could disappear",
        f"| Customer entities could disappear from the buyer surface when `parent_entity_id` formed a self-parent or cycle; the first tree refactor also placed child `group` content beside rather than inside its parent `treeitem`. | The old projection assembled only root-reachable nodes, overloaded evidence state with hierarchy semantics, and did not satisfy the APG ownership rule. | Code commit `{CODE_SHA}` promotes malformed edges to visible unresolved roots, keeps ORG containment separate from SKOS classification, makes every parent `treeitem` own its child `group`, separates evidence into an external region, and adds navigation, failure, stale-response, ontology, and Storybook regressions. | The API still exposes one parent context; authoritative acyclicity, level-transition rules, legal/operating/sales/billing contexts, and effective-dated history remain future normalized-model work. |",
    )
    replace_row(
        lines,
        "| #258 |",
        f"| #258 | buyer evidence board, standards-composed ontology, and cycle-safe Customer Master tree | `main` → `{CODE_SHA}` | Ready / mergeable / final-head Checks and independent approval pending |",
    )
    replace_row(
        lines,
        "| P0 | PR #258 is not review/CI complete",
        f"| P0 | PR #258 still requires final-head review and hosted CI | Customer hierarchy code is at `{CODE_SHA}`; branch-local verification does not transfer to the following documentation-only head | Re-read review threads, obtain qualifying independent approval, require all final-head hosted Checks to reach terminal success, and merge only through normal protection |",
    )

    text = "\n".join(lines) + "\n"
    if "__TREE_CODE_SHA__" in text:
        raise RuntimeError("unresolved customer-tree SHA placeholder remains")
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
