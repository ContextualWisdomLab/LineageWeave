from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
PR_NUMBER = os.environ.get("PR_NUMBER", "").strip()
PR_LABEL = f"#{PR_NUMBER}" if PR_NUMBER else "this PR"
BASE_HEAD = "8832216fcd2b0a1dcb486ea83269e25695ce378a"

app_path = FRONTEND / "src/App.tsx"
app = app_path.read_text(encoding="utf-8")
app = app.replace("  askAgent,\n", "")
app = app.replace("  type AskAgentResponse,\n", "")
app = app.replace(
    'import { CustomerMasterTree, CustomerRelatedPostCard } from "./components/CustomerMasterTree";\n',
    'import { CustomerMasterTree, CustomerRelatedPostCard } from "./components/CustomerMasterTree";\n'
    'import {\n'
    '  AskAgentWorkspace as AskAgentPanel,\n'
    '  GLOBAL_ASK_SESSION_STORAGE_KEY,\n'
    '} from "./components/AskAgentWorkspace";\n',
)
app = app.replace(
    '\nconst GLOBAL_ASK_SESSION_STORAGE_KEY = "lineageweave.globalAskSessionId";\n',
    "\n",
)
app = re.sub(
    r'\nconst CHAT_EVIDENCE_KIND_LABELS: Record<string, string> = \{.*?\n\}\;\n\nfunction chatEvidenceKindLabel\(kind: string\): string \{.*?\n\}\n',
    "\n",
    app,
    count=1,
    flags=re.DOTALL,
)
start = app.index("function AskAgentPanel({")
end = app.index("\nexport default function App", start)
app = app[:start] + app[end:]
app_path.write_text(app, encoding="utf-8")

package_path = FRONTEND / "package.json"
package = package_path.read_text(encoding="utf-8")
package = package.replace('"version": "2.17.0"', '"version": "2.18.0"', 1)
package_path.write_text(package, encoding="utf-8")

baseline_path = ROOT / "docs/product-technical-gap-baseline.md"
baseline = baseline_path.read_text(encoding="utf-8")
if "**Active Ask Agent design head:**" not in baseline:
    baseline = baseline.replace(
        "**Purpose:**",
        f"**Active Ask Agent design head:** {PR_LABEL}, stacked directly on #264 exact head `{BASE_HEAD}`; this is proposed work until merged.\n**Purpose:**",
        1,
    )
if "| FR-14 |" not in baseline:
    fr14 = (
        "| FR-14 | Global Ask presents a dedicated evidence workspace: semantic form submission, IME-safe keyboard behavior, explicit empty/loading/error/answer states, separated timeline and cited evidence, answer focus, responsive phone/tablet/PC layout, and the existing authorized cited-post → Event Lineage handoff. | ADR 0125, ADR 0002, ADR 0032, ADR 0090 | `AskAgentWorkspace.tsx`, component tests, Storybook scene inventory, and the existing App navigation regressions on "
        f"{PR_LABEL} |\n"
    )
    baseline = re.sub(r"(\| FR-13 \|[^\n]+\n)", r"\1" + fr14, baseline, count=1)
if "| NFR-08 |" not in baseline:
    nfr8 = (
        "| NFR-08 | Ask Agent uses the shared token system, clear focus differentiation, a primary content action, and 1024px/768px responsive transitions without horizontal scrolling | Focused component tests, full frontend build, Storybook state builds, and UI/UX Standard Guide v3.0 review |\n"
    )
    baseline = re.sub(r"(\| NFR-07 \|[^\n]+\n)", r"\1" + nfr8, baseline, count=1)
if "Ask Agent had no dedicated UI component" not in baseline:
    gap_row = (
        "| Ask Agent had no dedicated UI component or executable state inventory; its chatbox reused a Keyman link-style action and mixed answer, timeline, citations, and evidence facts in one generic section. | The Global Ask feature accumulated inside `App.tsx` while the stack focused on authorization and cross-surface navigation, leaving presentation without its own ownership boundary. | "
        f"{PR_LABEL} extracts a token-based evidence workspace, uses a semantic and IME-safe form, focuses completed answers, separates source-backed result regions, and adds five Storybook scenes plus focused regressions. | Streaming and persisted conversation history remain separate future product work; final-head hosted Checks and independent approval are still required. |\n"
    )
    marker = "|---|---|---|---|\n"
    location = baseline.index(marker, baseline.index("## Active-PR gap closure evidence")) + len(marker)
    baseline = baseline[:location] + gap_row + baseline[location:]
if PR_NUMBER and f"| #{PR_NUMBER} | Ask Agent evidence workspace" not in baseline:
    row = (
        f"| #{PR_NUMBER} | Ask Agent evidence workspace and semantic chatbox | `#264` → `v2.18.0` | Exact-head verification and independent review required |\n"
    )
    marker = "|---|---|---|---|\n"
    location = baseline.index(marker, baseline.index("## Active PR audit")) + len(marker)
    baseline = baseline[:location] + row + baseline[location:]
baseline_path.write_text(baseline, encoding="utf-8")

print("Ask Agent evidence workspace patch applied")
