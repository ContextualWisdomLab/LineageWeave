import { afterEach, describe, expect, it } from "vitest";
import {
  LOCALE_LABELS,
  SUPPORTED_LOCALES,
  getLocale,
  setLocale,
  t,
  tf,
} from "./i18n";

afterEach(() => {
  setLocale("en");
});

describe("i18n", () => {
  const requiredBuyerLabels = [
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
    "Page",
    "Answer",
    "Showing the first {shown} of {total} posts known at this cutoff.",
    "Weekly VOC",
    "Filter by ISO week",
    "All weeks",
    "Authorized commitments are current. Open a commitment to read Event Lineage.",
    "Authorized customer entities are current. Open a related post to read Event Lineage.",
    "Authorized cited posts are current. Open a cited post to read Event Lineage.",
    "Use the LLM channel",
    "Rebuild is queued. Event Lineage updates when it succeeds.",
    "Rebuild succeeded on three channels. Open Event Lineage, then connect contextual-orchestrator to use the LLM channel.",
    "No authorized source posts are available for this question.",
    "Enable public verification to check eligible public claims.",
    "Configure public search and contextual-orchestrator, then retry.",
    "Inspect the internal cited posts; no public claim was eligible.",
    "Inspect public evidence separately before any governed graph review.",
    "Collect stronger authoritative evidence before accepting the claim.",
    "Inspect the authorized cited posts and their evidence.",
    "Event Lineage timeline",
    "Open timeline post:",
  ] as const;

  it("supports the five product locales", () => {
    expect(SUPPORTED_LOCALES).toEqual(["en", "ko", "zh", "ja", "vi"]);
    expect(Object.keys(LOCALE_LABELS)).toHaveLength(5);
  });

  it.each(["ko", "zh", "ja", "vi"] as const)(
    "translates all shared Buyer labels in %s",
    (locale) => {
      setLocale(locale);
      for (const key of requiredBuyerLabels) {
        expect(t(key), `${locale}:${key}`).not.toBe(key);
      }
    },
  );

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
  ] as const)("formats dynamic buyer guidance in %s", (locale, expected) => {
    setLocale(locale);
    expect(tf("{post} is current in Event Lineage. Read Keyman and evaluation next.", { post: "DEMO" })).toBe(expected);
  });

  it.each([
    ["ko", "2026-W01 Voice of Customer 글이 현재 표시되어 있습니다. 이벤트 계보를 읽으려면 글을 여세요."],
    ["zh", "2026-W01 的 Voice of Customer 文章为当前内容。打开一篇文章阅读事件谱系。"],
    ["ja", "2026-W01のVoice of Customer投稿が現在表示されています。イベント系譜を読むには投稿を開いてください。"],
    ["vi", "Các bài Voice of Customer của 2026-W01 đang hiện tại. Hãy mở một bài để đọc Dòng sự kiện."],
  ] as const)("formats weekly VOC next action in %s", (locale, expected) => {
    setLocale(locale);
    expect(
      tf("Voice of Customer posts for {week} are current. Open a post to read Event Lineage.", {
        week: "2026-W01",
      }),
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
