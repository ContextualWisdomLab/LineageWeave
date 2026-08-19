#!/usr/bin/env python3
"""Apply the test-first PR 264 analysis-run cutoff navigation repair."""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend" / "src"
HELPER = FRONTEND / "analysisRunNavigation.ts"
HELPER_TEST = FRONTEND / "analysisRunNavigation.test.ts"
APP = FRONTEND / "App.tsx"
APP_TEST = FRONTEND / "App.test.tsx"

HELPER_TEST_CONTENT = '''import { describe, expect, it } from "vitest";
import { analysisRunTargetClock } from "./analysisRunNavigation";

describe("analysisRunTargetClock", () => {
  const context = {
    knowledgeCutoff: "2026-01-15T12:00:00Z",
    visiblePosts: [
      { post_id: "unchanged", live_after_cutoff: false },
      { post_id: "rewritten", live_after_cutoff: true },
    ],
  };

  it("uses the selected DAG target's own live_after_cutoff value", () => {
    expect(analysisRunTargetClock(context, "rewritten")).toEqual({
      liveAfterCutoff: true,
      knowledgeCutoff: context.knowledgeCutoff,
    });
    expect(analysisRunTargetClock(context, "unchanged")).toEqual({
      liveAfterCutoff: false,
      knowledgeCutoff: context.knowledgeCutoff,
    });
  });

  it("keeps the run cutoff and fails closed for a target absent from visible_posts", () => {
    expect(analysisRunTargetClock(context, "missing")).toEqual({
      liveAfterCutoff: false,
      knowledgeCutoff: context.knowledgeCutoff,
    });
  });
});
'''

HELPER_CONTENT = '''/** Immutable analysis-run clock context carried across post navigation. */
export type AnalysisRunNavigationContext = {
  knowledgeCutoff: string;
  visiblePosts: Array<{ post_id: string; live_after_cutoff?: boolean }>;
};

/** Resolve the selected target's own write-clock flag under the originating run cutoff. */
export function analysisRunTargetClock(
  context: AnalysisRunNavigationContext,
  postId: string,
): { liveAfterCutoff: boolean; knowledgeCutoff: string } {
  const target = context.visiblePosts.find((post) => post.post_id === postId);
  return {
    liveAfterCutoff: Boolean(target?.live_after_cutoff),
    knowledgeCutoff: context.knowledgeCutoff,
  };
}
'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    """Replace one exact source anchor or accept an already-applied replacement."""
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one source anchor, found {count}")
    return text.replace(old, new, 1)


def write_red() -> None:
    """Write only the regression so the unpatched source must fail."""
    HELPER_TEST.write_text(HELPER_TEST_CONTENT, encoding="utf-8")


def apply_fix() -> None:
    """Write the helper and patch the buyer surface plus integration regression."""
    HELPER.write_text(HELPER_CONTENT, encoding="utf-8")
    HELPER_TEST.write_text(HELPER_TEST_CONTENT, encoding="utf-8")

    text = APP.read_text(encoding="utf-8")
    text = replace_once(
        text,
        'import { PopupCloseButton } from "./components/PopupCloseButton";\n',
        'import {\n'
        '  PopupCloseButton,\n'
        '} from "./components/PopupCloseButton";\n',
        "single-writer import guard",
    )
    text = replace_once(
        text,
        'import { isoWeekFromCreatedAt, latestIsoWeek } from "./isoWeek";\n',
        'import { isoWeekFromCreatedAt, latestIsoWeek } from "./isoWeek";\n'
        'import {\n'
        '  analysisRunTargetClock,\n'
        '  type AnalysisRunNavigationContext,\n'
        '} from "./analysisRunNavigation";\n',
        "navigation import",
    )
    text = replace_once(
        text,
        'type SelectPostOptions = {\n'
        '  liveAfterCutoff?: boolean;\n'
        '  knowledgeCutoff?: string;\n',
        'type SelectPostOptions = {\n'
        '  liveAfterCutoff?: boolean;\n'
        '  knowledgeCutoff?: string;\n'
        '  analysisRunContext?: AnalysisRunNavigationContext;\n',
        "select options",
    )
    text = replace_once(
        text,
        'function analysisRunPostOpenOptions(run: AnalysisRun, postId: string): SelectPostOptions {\n'
        '  const post = run.visible_posts?.find((item) => item.post_id === postId);\n'
        '  return {\n'
        '    liveAfterCutoff: Boolean(post?.live_after_cutoff),\n'
        '    knowledgeCutoff: run.knowledge_cutoff,\n'
        '  };\n'
        '}\n',
        'function analysisRunPostOpenOptions(run: AnalysisRun, postId: string): SelectPostOptions {\n'
        '  const analysisRunContext: AnalysisRunNavigationContext = {\n'
        '    knowledgeCutoff: run.knowledge_cutoff,\n'
        '    visiblePosts: run.visible_posts ?? [],\n'
        '  };\n'
        '  return {\n'
        '    ...analysisRunTargetClock(analysisRunContext, postId),\n'
        '    analysisRunContext,\n'
        '  };\n'
        '}\n',
        "analysis run open options",
    )
    text = replace_once(
        text,
        '  const [openedAfterCutoff, setOpenedAfterCutoff] = useState(false);\n'
        '  const [openedCutoffIso, setOpenedCutoffIso] = useState<string | null>(null);\n',
        '  const [openedAfterCutoff, setOpenedAfterCutoff] = useState(false);\n'
        '  const [openedCutoffIso, setOpenedCutoffIso] = useState<string | null>(null);\n'
        '  const [openedAnalysisRunContext, setOpenedAnalysisRunContext] =\n'
        '    useState<AnalysisRunNavigationContext | null>(null);\n',
        "analysis run state",
    )
    text = replace_once(
        text,
        '    setOpenedAfterCutoff(Boolean(options?.liveAfterCutoff));\n'
        '    setOpenedCutoffIso(options?.knowledgeCutoff ?? null);\n',
        '    setOpenedAfterCutoff(Boolean(options?.liveAfterCutoff));\n'
        '    setOpenedCutoffIso(options?.knowledgeCutoff ?? null);\n'
        '    setOpenedAnalysisRunContext(options?.analysisRunContext ?? null);\n',
        "select state",
    )
    text = replace_once(
        text,
        '    setOpenedAfterCutoff(false);\n'
        '    setOpenedCutoffIso(null);\n'
        '    setOpenedFromReportMember(false);\n',
        '    setOpenedAfterCutoff(false);\n'
        '    setOpenedCutoffIso(null);\n'
        '    setOpenedAnalysisRunContext(null);\n'
        '    setOpenedFromReportMember(false);\n',
        "close state",
    )
    text = replace_once(
        text,
        '                      onClick={() =>\n'
        '                        onSelectPost(post.post_id, {\n'
        '                          liveAfterCutoff: Boolean(post.live_after_cutoff),\n'
        '                          knowledgeCutoff: selected.knowledge_cutoff,\n'
        '                        })\n'
        '                      }\n',
        '                      onClick={() =>\n'
        '                        onSelectPost(\n'
        '                          post.post_id,\n'
        '                          analysisRunPostOpenOptions(selected, post.post_id),\n'
        '                        )\n'
        '                      }\n',
        "visible post open",
    )
    text = replace_once(
        text,
        '          onSelectPost={(postId) =>\n'
        '            selectPost(postId, {\n'
        '              fromReportMember: openedFromReportMember,\n'
        '              fromWeeklyVoc: openedFromWeeklyVoc,\n'
        '              fromCalendar: openedFromCalendar,\n'
        '              fromCustomerMaster: openedFromCustomerMaster,\n'
        '              fromAskAgent: openedFromAskAgent,\n'
        '            })\n'
        '          }\n',
        '          onSelectPost={(postId) => {\n'
        '            const cutoffOptions = openedAnalysisRunContext\n'
        '              ? analysisRunTargetClock(openedAnalysisRunContext, postId)\n'
        '              : {};\n'
        '            selectPost(postId, {\n'
        '              ...cutoffOptions,\n'
        '              analysisRunContext: openedAnalysisRunContext ?? undefined,\n'
        '              fromReportMember: openedFromReportMember,\n'
        '              fromWeeklyVoc: openedFromWeeklyVoc,\n'
        '              fromCalendar: openedFromCalendar,\n'
        '              fromCustomerMaster: openedFromCustomerMaster,\n'
        '              fromAskAgent: openedFromAskAgent,\n'
        '            });\n'
        '          }}\n',
        "popup navigation",
    )
    APP.write_text(text, encoding="utf-8")

    test_text = APP_TEST.read_text(encoding="utf-8")
    test_text = replace_once(
        test_text,
        '''    expect(screen.queryByRole("status", { name: "Live body warning" })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Close" }));
    await userEvent.click(
      screen.getByRole("button", {
        name: "Open live post: Private post",
      }),
    );
''',
        '''    expect(screen.queryByRole("status", { name: "Live body warning" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Body this run knew" })).not.toBeInTheDocument();

    const publicPosts = screen.getAllByLabelText("Open post: Public post");
    await userEvent.click(publicPosts[publicPosts.length - 1]);
    await waitFor(() => expect(screen.getByText("The full body text.")).toBeInTheDocument());
    expect(screen.getByRole("status", { name: "Live body warning" })).toHaveTextContent(
      "This is the live body, not a cutoff snapshot. Compare it with this 2026-01-12 run before you treat it as reconstructed evidence.",
    );
    expect(screen.getByRole("heading", { name: "Body this run knew" })).toBeInTheDocument();
    expect(screen.getByText("The cutoff body this run knew.")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Close" }));
    await userEvent.click(
      screen.getByRole("button", {
        name: "Open live post: Private post",
      }),
    );
''',
        "cutoff navigation regression",
    )
    APP_TEST.write_text(test_text, encoding="utf-8")


def main() -> None:
    """Dispatch the requested test-first stage."""
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("red", "apply"))
    args = parser.parse_args()
    if args.stage == "red":
        write_red()
    else:
        apply_fix()


if __name__ == "__main__":
    main()
