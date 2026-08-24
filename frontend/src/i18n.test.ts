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
    "leftover axis {axis} {share}%",
    "Leftover-map axis share",
    "Leftover-map axis share is Gabriel inertia of residual SVD axes 1 and 2. Open a leftover pair to read the post–criterion cell. The shares do not invent a leftover score.",
    "Leftover pairs",
    "Closest leftover",
    "Farthest leftover",
    "Leftover residual R {residual} after IRT main effects. Open this post to read {criterion}.",
    "Open leftover {kind} pair: {title} · {criterion}",
    "Open this post to read the criterion it sat closest to after main effects.",
    "Open this post to read the criterion it sat farthest from after main effects.",
    "Leftover map leaves unexplained U {value} after IRT main effects. Open this post to read {criterion}.",
    "Read observed Y {observed} and expected E {expected} after IRT main effects, then open this post.",
    "Leftover map has no leftover structure after IRT main effects. Open this post.",
    "Leftover map rank {rank} after IRT main effects. Open this post.",
    "Read leftover map rank {rank}, observed Y {observed}, and expected E {expected} after IRT main effects, then open this post.",
    "Leftover map rank 0 means no leftover structure after IRT main effects. Read observed Y {observed} and expected E {expected}, then open this post.",
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
  const boardAndRoleRelationshipLabels = [
    "Account",
    "Affiliation",
    "Answers cite authorized posts when available.",
    "Authorized evidence",
    "Board advanced review",
    "Evidence workspace",
    "Existing workspace surface",
    "Explicit semantic relationships",
    "None",
    "Open in Board",
    "Organization member of",
    "Organization unit of",
    "Permissions",
    "R&R affiliation: {name}",
    "Responsible for",
    "Sub-organization of",
    "Summary could not be generated.",
    "Summary is not created for writing posts.",
    "Supports",
    "The existing Board owns the selected post and its provenance, so this action opens there instead of duplicating the workflow.",
    "routes",
  ] as const;
  const sourceLineageHintLabels = [
    "Source process unit catalog hint",
    "Catalog hint",
    "Source order pool",
    "Source sales order",
    "Source sales order item",
    "Source inspection point",
    "Source context",
    "Source fields",
    "Source lineage combination",
    "Combination code",
    "Field combination",
    "Present",
    "Not present",
    "Inferred from field presence",
    "Lifecycle vector",
    "Raw codes only",
    "No sales identifier candidate",
    "Customer only candidate",
    "Customer + order-pool candidate",
    "Sales-order item context",
    "Sales-order item without customer",
    "Order-pool only candidate",
    "Sales order without item candidate",
    "Customer + sales order without item",
    "Mixed source identifier context",
    "Customer code",
    "Order pool",
    "Sales order",
    "Sales-order item",
  ] as const;
  const knowledgeGraphRelationLabels = [
    "Legend",
    "Category",
    "Time order",
    "Hierarchy",
    "Cause and effect",
    "Other relation",
  ] as const;
  const roleEvidenceAndCustomerIdentitySearchLabels = [
    "Quantitative evidence",
    "Quantity",
    "Connected clues",
    "Negated clue",
    "Source-grounded facts",
    "Subject type",
    "Object type",
    "Negated condition",
    "Normalized date",
    "Normalization evidence",
    "Specific business unit not stated in source",
    "Find source customer code",
    "Paste an observed customer code",
    "Find",
    "Searches all authorized source hints, not only the ranked first page.",
    "No source customer evidence matches {code}.",
    "The source is still being written; analysis starts after approval.",
    "Rankings",
    "Title overlap",
    "RankWeave fused newest-first and title-overlap ranks. This is not a calibrated score.",
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

  it.each(["ko", "zh", "ja", "vi"] as const)(
    "translates Board and R&R relationship labels in %s",
    (locale) => {
      setLocale(locale);
      for (const key of boardAndRoleRelationshipLabels) {
        expect(t(key), `${locale}:${key}`).not.toBe(key);
      }
    },
  );

  it.each(["ko", "zh", "ja", "vi"] as const)(
    "translates source lineage combination hint labels in %s",
    (locale) => {
      setLocale(locale);
      for (const key of sourceLineageHintLabels) {
        expect(t(key), `${locale}:${key}`).not.toBe(key);
      }
    },
  );

  it.each(["ko", "zh", "ja", "vi"] as const)(
    "translates Knowledge Graph relation category labels in %s",
    (locale) => {
      setLocale(locale);
      for (const key of knowledgeGraphRelationLabels) {
        expect(t(key), `${locale}:${key}`).not.toBe(key);
      }
    },
  );

  it.each(["ko", "zh", "ja", "vi"] as const)(
    "translates role-evidence and customer-identity-search labels in %s",
    (locale) => {
      setLocale(locale);
      for (const key of roleEvidenceAndCustomerIdentitySearchLabels) {
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
    ["ko", "DEMO은(는) 이벤트 계보의 현재 항목입니다. 다음으로 Keyman과 평가를 읽으세요."],
    ["zh", "DEMO 是事件谱系中的当前记录。接下来查看关键联系人和评估。"],
    ["ja", "DEMOはイベント系譜の現在の記録です。次にキーパーソンと評価を確認してください。"],
    ["vi", "DEMO là bản ghi hiện tại trong Dòng sự kiện. Hãy xem người liên hệ chính và đánh giá tiếp theo."],
  ] as const)("formats dynamic reader guidance in %s", (locale, expected) => {
    setLocale(locale);
    expect(tf("{post} is current in Event Lineage. Read Keyman and evaluation next.", { post: "DEMO" })).toBe(expected);
  });

  it.each([
    ["ko", "IRT 주효과 이후 잔여 R +0.40. sales-lead 기준을 읽으려면 이 글을 여세요."],
    ["zh", "IRT 主效应后的残余 R +0.40。打开这篇帖子阅读 sales-lead。"],
    ["ja", "IRT主効果後の残差 R +0.40。この投稿を開いて sales-lead を読んでください。"],
    ["vi", "Phần dư R +0.40 sau hiệu ứng chính IRT. Mở bài viết này để đọc sales-lead."],
  ] as const)("formats leftover residual next action in %s", (locale, expected) => {
    setLocale(locale);
    expect(
      tf(
        "Leftover residual R {residual} after IRT main effects. Open this post to read {criterion}.",
        { residual: "+0.40", criterion: "sales-lead" },
      ),
    ).toBe(expected);
  });

  it.each([
    ["ko", "IRT 주효과 이후 관측 Y 2.40와 기대 E 2.00를 읽은 다음, 이 글을 여세요."],
    ["zh", "阅读 IRT 主效应后的观测 Y 2.40 与期望 E 2.00，然后打开这篇帖子。"],
    ["ja", "IRT主効果後の観測 Y 2.40 と期待 E 2.00 を読んでから、この投稿を開いてください。"],
    ["vi", "Đọc Y quan sát 2.40 và E kỳ vọng 2.00 sau hiệu ứng chính IRT, rồi mở bài viết này."],
  ] as const)("formats leftover observed and expected next action in %s", (locale, expected) => {
    setLocale(locale);
    expect(
      tf(
        "Read observed Y {observed} and expected E {expected} after IRT main effects, then open this post.",
        { observed: "2.40", expected: "2.00" },
      ),
    ).toBe(expected);
  });

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

  it.each([
    ["ko", "IRT 주효과 이후 잔여 맵 랭크 1, 관측 Y 2.40, 기대 E 2.00를 읽은 다음, 이 글을 여세요."],
    ["zh", "阅读 IRT 主效应后的残余图秩 1、观测 Y 2.40 与期望 E 2.00，然后打开这篇帖子。"],
    ["ja", "IRT主効果後の残差マップランク 1、観測 Y 2.40、期待 E 2.00 を読んでから、この投稿を開いてください。"],
    ["vi", "Đọc hạng bản đồ phần dư 1, Y quan sát 2.40 và E kỳ vọng 2.00 sau hiệu ứng chính IRT, rồi mở bài viết này."],
  ] as const)("formats combined leftover evidence next action in %s", (locale, expected) => {
    setLocale(locale);
    expect(
      tf(
        "Read leftover map rank {rank}, observed Y {observed}, and expected E {expected} after IRT main effects, then open this post.",
        { rank: "1", observed: "2.40", expected: "2.00" },
      ),
    ).toBe(expected);
  });

  it.each([
    [
      "ko",
      "잔여 지도가 IRT 주효과 이후 설명되지 않은 U +0.05을(를) 남깁니다. sales-lead 기준을 읽으려면 이 글을 여세요.",
    ],
    [
      "zh",
      "残差图在 IRT 主效应后留下未解释的 U +0.05。打开这篇帖子阅读 sales-lead。",
    ],
    [
      "ja",
      "残差マップはIRT主効果後の未説明 U +0.05 を残します。この投稿を開いて sales-lead を読んでください。",
    ],
    [
      "vi",
      "Bản đồ phần dư để lại U +0.05 chưa giải thích sau hiệu ứng chính IRT. Mở bài viết này để đọc sales-lead.",
    ],
  ] as const)("formats leftover-map unexplained next action in %s", (locale, expected) => {
    setLocale(locale);
    expect(
      tf(
        "Leftover map leaves unexplained U {value} after IRT main effects. Open this post to read {criterion}.",
        { value: "+0.05", criterion: "sales-lead" },
      ),
    ).toBe(expected);
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
