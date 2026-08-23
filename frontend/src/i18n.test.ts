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
    "Leftover residual R {residual} after IRT main effects. Open this post to read {criterion}.",
    "Open leftover {kind} pair: {title} · {criterion}",
    "Open this post to read the criterion it sat closest to after main effects.",
    "Open this post to read the criterion it sat farthest from after main effects.",
    "Read observed Y {observed} and expected E {expected} after IRT main effects, then open this post.",
    "Leftover map has no leftover structure after IRT main effects. Open this post.",
    "Leftover map rank {rank} after IRT main effects. Open this post.",
    "Read leftover map rank {rank}, observed Y {observed}, and expected E {expected} after IRT main effects, then open this post.",
    "Leftover map rank 0 means no leftover structure after IRT main effects. Read observed Y {observed} and expected E {expected}, then open this post.",
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
