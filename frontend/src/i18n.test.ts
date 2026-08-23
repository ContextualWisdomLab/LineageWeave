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
    "Leftover pairs",
    "Closest leftover",
    "Farthest leftover",
    "Open this post to read the criterion it sat closest to after main effects.",
    "Open this post to read the criterion it sat farthest from after main effects.",
    "Two leftover-map axes explain {value} of centered leftover after IRT main effects. Open this post to read {criterion}.",
    "Open leftover {kind} pair: {title} · {criterion}",
    "Showing the first {shown} of {total} posts known at this cutoff.",
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
    [
      "ko",
      "잔여 지도의 두 축이 IRT 주효과 이후 중심화 잔여의 0.88을(를) 설명합니다. sales-lead 기준을 읽으려면 이 글을 여세요.",
    ],
    [
      "zh",
      "残差图的两个轴解释 IRT 主效应后中心化残差的 0.88。打开这篇帖子阅读 sales-lead。",
    ],
    [
      "ja",
      "残差マップの2軸はIRT主効果後の中心化残差の 0.88 を説明します。この投稿を開いて sales-lead を読んでください。",
    ],
    [
      "vi",
      "Hai trục của bản đồ phần dư giải thích 0.88 phần dư đã căn giữa sau hiệu ứng chính IRT. Mở bài viết này để đọc sales-lead.",
    ],
  ] as const)("formats leftover-map explained share next action in %s", (locale, expected) => {
    setLocale(locale);
    expect(
      tf(
        "Two leftover-map axes explain {value} of centered leftover after IRT main effects. Open this post to read {criterion}.",
        { value: "0.88", criterion: "sales-lead" },
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
