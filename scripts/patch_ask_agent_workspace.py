from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
PR_NUMBER = os.environ.get("PR_NUMBER", "").strip()
PR_LABEL = f"#{PR_NUMBER}" if PR_NUMBER else "this PR"
BASE_HEAD = "39f21261052a9d2ae82c4b851a54831eaf909805"

app_path = FRONTEND / "src/App.tsx"
app = app_path.read_text(encoding="utf-8")
component_import = (
    'import {\n'
    '  AskAgentWorkspace as AskAgentPanel,\n'
    '  GLOBAL_ASK_SESSION_STORAGE_KEY,\n'
    '} from "./components/AskAgentWorkspace";\n'
)
if component_import not in app:
    app = app.replace("  askAgent,\n", "", 1)
    app = app.replace("  type AskAgentResponse,\n", "", 1)
    customer_import = (
        'import { CustomerMasterTree, CustomerRelatedPostCard } '
        'from "./components/CustomerMasterTree";\n'
    )
    if customer_import not in app:
        raise SystemExit("Customer Master import anchor changed")
    app = app.replace(customer_import, customer_import + component_import, 1)
    app = app.replace(
        '\nconst GLOBAL_ASK_SESSION_STORAGE_KEY = "lineageweave.globalAskSessionId";\n',
        "\n",
        1,
    )
    app, label_count = re.subn(
        r'\nconst CHAT_EVIDENCE_KIND_LABELS: Record<string, string> = \{.*?\n\};\n\n'
        r'function chatEvidenceKindLabel\(kind: string\): string \{.*?\n\}\n',
        "\n",
        app,
        count=1,
        flags=re.DOTALL,
    )
    if label_count != 1:
        raise SystemExit("Ask evidence label helper anchor changed")
    start = app.find("function AskAgentPanel({")
    end = app.find("\nexport default function App", start)
    if start < 0 or end < 0:
        raise SystemExit("Inline AskAgentPanel anchor changed")
    app = app[:start] + app[end:]
if "function AskAgentPanel({" in app:
    raise SystemExit("Legacy inline AskAgentPanel remains")
app_path.write_text(app, encoding="utf-8")

package_path = FRONTEND / "package.json"
package = package_path.read_text(encoding="utf-8")
if '"version": "2.17.0"' in package:
    package = package.replace('"version": "2.17.0"', '"version": "2.18.0"', 1)
elif '"version": "2.18.0"' not in package:
    raise SystemExit("Frontend version anchor changed")
package_path.write_text(package, encoding="utf-8")

baseline_path = ROOT / "docs/product-technical-gap-baseline.md"
baseline = baseline_path.read_text(encoding="utf-8")
if "**Active Ask Agent design head:**" not in baseline:
    baseline = baseline.replace(
        "# Product & Technical Gap Baseline\n",
        (
            "# Product & Technical Gap Baseline\n\n"
            f"**Active Ask Agent design head:** PR {PR_LABEL}, stacked directly "
            f"on #264 exact head `{BASE_HEAD}`; this is proposed work until merged.\n"
        ),
        1,
    )
if "| FR-14 |" not in baseline:
    fr14 = (
        "| FR-14 | Global Ask presents a dedicated evidence workspace: semantic form submission, IME-safe keyboard behavior, explicit empty/loading/error/answer states, separated timeline and cited evidence, answer focus, responsive phone/tablet/PC layout, and the existing authorized cited-post → Event Lineage handoff. | ADR 0126, ADR 0002, ADR 0032, ADR 0090 | `AskAgentWorkspace.tsx`, focused component/token tests, Storybook state inventory, and existing App navigation regressions on "
        f"{PR_LABEL} |\n"
    )
    baseline, count = re.subn(r"(\| FR-13 \|[^\n]+\n)", r"\1" + fr14, baseline, count=1)
    if count != 1:
        raise SystemExit("FR-13 baseline anchor changed")
if "| NFR-08 |" not in baseline:
    nfr8 = (
        "| NFR-08 | Ask Agent uses shared UI-standard button/focus/color/radius tokens, clear focus differentiation, a primary content action, and 1024px/768px responsive transitions without horizontal scrolling | Focused component and CSS-contract tests, complete frontend build, Storybook state build, and UI/UX Standard Guide v3.0 review |\n"
    )
    baseline, count = re.subn(r"(\| NFR-07 \|[^\n]+\n)", r"\1" + nfr8, baseline, count=1)
    if count != 1:
        raise SystemExit("NFR-07 baseline anchor changed")
if "Ask Agent had no dedicated UI component" not in baseline:
    gap_row = (
        "| Ask Agent had no dedicated UI component or executable state inventory; its chatbox reused a Keyman link-style action and mixed answer, timeline, citations, and evidence facts in one generic section. | The Global Ask feature accumulated inside `App.tsx` while the stack focused on authorization and cross-surface navigation, leaving presentation without its own ownership boundary. | "
        f"{PR_LABEL} extracts a token-based evidence workspace, uses a semantic and IME-safe form, focuses completed answers, separates source-backed result regions, and adds five Storybook scenes plus focused regressions. | Streaming and persisted conversation history remain separate future product work; final-head hosted Checks and independent approval are still required. |\n"
    )
    section = baseline.index("## Active-PR gap closure evidence")
    marker = "|---|---|---|---|\n"
    location = baseline.index(marker, section) + len(marker)
    baseline = baseline[:location] + gap_row + baseline[location:]
if PR_NUMBER and f"| #{PR_NUMBER} | Ask Agent evidence workspace" not in baseline:
    row = (
        f"| #{PR_NUMBER} | Ask Agent evidence workspace and semantic chatbox | `#264` → `v2.18.0` | Exact-head verification and independent review required |\n"
    )
    section = baseline.index("## Active PR audit")
    marker = "|---|---|---|---|\n"
    location = baseline.index(marker, section) + len(marker)
    baseline = baseline[:location] + row + baseline[location:]
baseline_path.write_text(baseline, encoding="utf-8")

inventory_path = ROOT / "docs/storybook-inventory.md"
inventory = inventory_path.read_text(encoding="utf-8")
if "`Ask/AskAgentWorkspace`" not in inventory:
    row = (
        "| `Ask/AskAgentWorkspace` | Review empty, loading, answered, unavailable, and phone states; open cited evidence after an answer. | UI-standard primary-button/focus tokens, responsive layout, `AskAgentWorkspace` |\n"
    )
    anchor = "|---|---|---|\n"
    inventory = inventory.replace(anchor, anchor + row, 1)
inventory_path.write_text(inventory, encoding="utf-8")

print("Ask Agent evidence workspace patch applied")
