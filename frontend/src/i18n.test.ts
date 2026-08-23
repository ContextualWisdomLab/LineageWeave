import { afterEach, describe, expect, it, vi } from "vitest";
import {
  LOCALE_LABELS,
  SUPPORTED_LOCALES,
  getLocale,
  setLocale,
  t,
  tf,
} from "./i18n";

afterEach(() => {
  vi.unstubAllGlobals();
  window.localStorage.clear();
  setLocale("en");
});

describe("i18n", () => {
  const requiredWorkspaceLabels = [
    "Language",
    "Evidence",
    "Ask",
    "linked",
    "Post body preview",
    "unresolved",
    "Keymen",
    "Unknown",
    "Image tags",
    "Counterparties",
    "due",
    "Activity",
    "Refresh",
    "Close",
    "Post body",
    "Summary",
    "Calendar",
    "Board",
    "Search",
    "Site map",
    "Conversation",
    "Conversation history",
    "New conversation",
    "Switch between saved questions and source links.",
    "Ask a question to save your first conversation.",
    "No saved conversations yet.",
    "Start with a question about the evidence",
    "Ask about an event, decision, or source post.",
    "You",
    "Thinking...",
    "Open source",
    "Open source in new tab: {title}",
    "Enter to send. Shift+Enter for a new line.",
    "Filter customer entities",
    "All customer scopes",
    "Own company",
    "Granted company",
    "Scope not classified",
    "Observed organization",
    "Observed hierarchy",
    "Name history",
    "Managed customer",
    "Former name",
    "Alternate name",
    "No customer entities match this scope.",
    "Page",
    "Answer",
    "Leftover pairs",
    "Closest leftover",
    "Farthest leftover",
    "Open this post to read the criterion it sat closest to after main effects.",
    "Open this post to read the criterion it sat farthest from after main effects.",
    "Leftover-map inner product ξ·ζ {value} reconstructs leftover residual after IRT main effects. Open this post to read {criterion}.",
    "Open leftover {kind} pair: {title} · {criterion}",
    "Showing the first {shown} of {total} posts known at this cutoff.",
    "Persist the brand, system, and copyright metadata used by the workspace shell.",
    "Review the source body or related posts for this dimension.",
    "Review source evidence for this dimension.",
    "Source reference research",
    "Persisted web evidence; opening this post does not run a search.",
    "Research sources",
    "Researching sources...",
    "Loading source research...",
    "No persisted source research yet.",
    "Supported",
    "Refuted",
    "Not enough information",
    "Evidence provenance",
    "Image regions",
    "Sharing actor",
    "Uncertainty remains; do not infer a sharing actor from the address or URL alone.",
    "Research citations",
    "No cited public evidence.",
    "Next action",
    "Retry, or continue with saved evidence.",
    "{action} could not be completed.",
    "Correct the highlighted fields, then retry.",
    "Sign-in could not be completed.",
    "Log in again to open the workspace.",
    "Retry opening this source, or keep reading the saved answer.",
    "Retry evidence",
    "Retry loading this conversation, or continue with saved evidence.",
    "Source evidence is unavailable. Continue with the saved answer.",
    "Knowledge Graph directed relations",
    "Arrows show source → target; use arrow keys to pan and controls to zoom.",
    "Source",
    "Relation",
    "Target",
    "Confidence",
    "Before",
    "After",
    "Not linked to catalog",
    "Not linked to a catalog row",
    "Keep reading this mention as unbound, or open the catalog to bind it. This is not a missing analysis channel and not a negative extraction.",
    "This analysis channel is unavailable",
    "Continue with the remaining evidence, or retry when the channel is connected. A missing signal is not a negative fact.",
    "The source evidence is confidently negative",
    "Read the source sentence, then continue. This is a measured negative, not an unavailable channel.",
    "This R&R row is one source phrase. Do not treat it as a catalog relationship until job title and relationship type are stored separately.",
  ] as const;
  const eventLineageLabels = [
    "Authorized scope",
    "Customer scope",
    "Open navigation",
    "Skip to main content",
    "Lineage legend",
    "Root record",
    "Branch point",
    "Current record",
    "Parent to child",
    "Inference boundary",
    "Edges explain reconstructed continuation only. They are not causal or authoritative facts.",
    "Evidence (fused_score)",
  ] as const;
  const adminPanelLabels = [
    "Account scope",
    "Admin control center",
    "Admin endpoint catalog",
    "Admin navigation",
    "Administrator mode",
    "Authorized entities",
    "Board & posts",
    "Calendar & commitments",
    "Endpoint catalog",
    "Entities and relationship network",
    "Find the right operational surface without losing the source and permission context.",
    "Not available",
    "Open post operations",
    "post_admin enabled",
    "Routes are shown with the permission gate enforced by the backend.",
    "Search authorized posts",
    "Tenant settings",
    "These values come from the authenticated account and are not editable here.",
    "This name is used in the authenticated workspace shell.",
    "Workspace shortcuts",
    "Admin operations and workspace handoffs",
    "Admin overview",
    "Branding and tenant configuration",
    "Compare and rebuild period reports",
    "Content operations",
    "Control center",
    "Create a pending cutoff lineage for an authorized account.",
    "Create analysis run",
    "Create the evaluation evidence for a selected post.",
    "Cutoff, start, and run evidence",
    "Derive a commitment from source-grounded post evidence.",
    "Entities, people, and relationship network",
    "Keymen, relations, evaluation, tickets",
    "Lineage & analysis",
    "Lineage rebuild",
    "Manage tickets",
    "Permission and authorized entity scope",
    "Post evidence operations",
    "Rankings",
    "Reader-facing ranking evidence",
    "Rebuild a period report from the persisted report inputs.",
    "Rebuild period report",
    "Reconstruct authorized lineage",
    "Reconstruct the authorized lineage projection.",
    "Run the orchestrated Keyman extraction for a selected post.",
    "Start analysis run",
    "Start the persisted run from its pending cutoff lineage.",
    "Upcoming commitments and CalDAV events",
    "Update tenant settings",
    "Update the status of an issue ticket opened from a post.",
    "Validate extracted ontology relationships against source evidence.",
    "Verify post relations",
    "Workspace",
  ] as const;

  it("supports the five product locales", () => {
    expect(SUPPORTED_LOCALES).toEqual(["en", "ko", "zh", "ja", "vi"]);
    expect(Object.keys(LOCALE_LABELS)).toHaveLength(5);
  });

  it("detects stored, browser, restricted, and unsupported locale environments", async () => {
    window.localStorage.setItem("lineageweave.locale", "ko");
    vi.resetModules();
    expect((await import("./i18n")).getLocale()).toBe("ko");

    window.localStorage.clear();
    const getItem = vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });
    vi.stubGlobal("navigator", { language: "ja-JP" });
    vi.resetModules();
    expect((await import("./i18n")).getLocale()).toBe("ja");
    getItem.mockRestore();

    vi.stubGlobal("navigator", undefined);
    vi.stubGlobal("document", undefined);
    vi.resetModules();
    expect((await import("./i18n")).getLocale()).toBe("en");

    vi.unstubAllGlobals();
    vi.stubGlobal("navigator", { language: "xx-YY" });
    vi.resetModules();
    expect((await import("./i18n")).getLocale()).toBe("en");
    vi.unstubAllGlobals();
  });

  it.each(["ko", "zh", "ja", "vi"] as const)(
    "translates all shared workspace labels in %s",
    (locale) => {
      setLocale(locale);
      for (const key of requiredWorkspaceLabels) {
        expect(t(key), `${locale}:${key}`).not.toBe(key);
      }
    },
  );

  it.each(["ko", "zh", "ja", "vi"] as const)(
    "translates Event Lineage and authorization labels in %s",
    (locale) => {
      setLocale(locale);
      for (const key of eventLineageLabels) {
        expect(t(key), `${locale}:${key}`).not.toBe(key);
      }
    },
  );

  it.each(["ko", "zh", "ja", "vi"] as const)(
    "translates Admin Panel labels in %s",
    (locale) => {
      setLocale(locale);
      for (const key of adminPanelLabels) {
        expect(t(key), `${locale}:${key}`).not.toBe(key);
      }
    },
  );

  it.each([
    ["ko", "작업공간 메뉴"],
    ["zh", "工作区导航"],
    ["ja", "ワークスペースナビゲーション"],
    ["vi", "Điều hướng không gian làm việc"],
  ] as const)("uses workspace terminology for navigation in %s", (locale, expected) => {
    setLocale(locale);
    expect(t("Workspace navigation")).toBe(expected);
    expect(t("Workspace navigation").toLocaleLowerCase()).not.toContain("buyer");
  });

  it.each([
    ["ko", "관련 글"],
    ["zh", "相关文章"],
    ["ja", "関連する投稿"],
    ["vi", "Bài viết liên quan"],
  ] as const)("translates the related-post product surface in %s", (locale, expected) => {
    setLocale(locale);
    expect(getLocale()).toBe(locale);
    expect(t("Related posts")).toBe(expected);
    expect(document.documentElement.lang).toBe(locale);
  });

  it.each([
    [
      "ko",
      "잔여 지도 코사인 +0.95이(가) 거리와 무관한 잔여 지도 정렬을 이름합니다. sales-lead 기준을 읽으려면 이 글을 여세요.",
    ],
    [
      "zh",
      "残差图余弦 +0.95 命名与距离无关的残差图对齐。打开这篇帖子阅读 sales-lead。",
    ],
    [
      "ja",
      "残差マップ余弦 +0.95 は距離に依存しない残差マップの向きを示します。この投稿を開いて sales-lead を読んでください。",
    ],
    [
      "vi",
      "Cosin bản đồ phần dư +0.95 đặt tên sự thẳng hàng độc lập với khoảng cách. Mở bài viết này để đọc sales-lead.",
    ],
  ] as const)("formats leftover-map cosine next action in %s", (locale, expected) => {
    setLocale(locale);
    expect(
      tf(
        "Leftover-map cosine {value} names leftover-map alignment independent of distance. Open this post to read {criterion}.",
        { value: "+0.95", criterion: "sales-lead" },
      ),
    ).toBe(expected);
  });

  it.each([
    ["ko", "DEMO은(는) 이벤트 계보의 현재 항목입니다. 다음으로 Keyman과 평가를 읽으세요."],
    ["zh", "DEMO 是事件谱系中的当前记录。接下来查看关键联系人和评估。"],
    ["ja", "DEMOはイベント系譜の現在の記録です。次にキーパーソンと評価を確認してください。"],
    ["vi", "DEMO là bản ghi hiện tại trong Dòng sự kiện. Hãy xem người liên hệ chính và đánh giá tiếp theo."],
  ] as const)("formats dynamic reader guidance in %s", (locale, expected) => {
    setLocale(locale);
    expect(tf("{post} is current in Event Lineage. Read Keyman and evaluation next.", { post: "DEMO" })).toBe(expected);
  });

});

describe("locale-aware source labels", () => {
  it.each([
    ["en", "Voice of Customer", "Public"],
    ["ko", "고객의 소리", "공개"],
    ["zh", "客户之声", "公开"],
    ["ja", "顧客の声", "公開"],
    ["vi", "Tiếng nói khách hàng", "Công khai"],
  ] as const)("translates filter labels in %s", (locale, customerVoice, visibility) => {
    setLocale(locale);
    expect(t("Voice of Customer")).toBe(customerVoice);
    expect(t("Public")).toBe(visibility);
  });
});

describe("leftover-map rank next action", () => {
  it.each([
    ["ko", "IRT 주효과 이후 잔여 맵 랭크 1. 이 글을 여세요."],
    ["zh", "IRT 主效应后的残余图秩 1。打开这篇帖子。"],
    ["ja", "IRT主効果後の残差マップランク 1。この投稿を開いてください。"],
    ["vi", "Hạng bản đồ phần dư 1 sau hiệu ứng chính IRT. Mở bài viết này."],
  ] as const)("formats leftover-map rank next action in %s", (locale, expected) => {
    setLocale(locale);
    expect(
      tf("Leftover map rank {rank} after IRT main effects. Open this post.", { rank: "1" }),
    ).toBe(expected);
  });
});
