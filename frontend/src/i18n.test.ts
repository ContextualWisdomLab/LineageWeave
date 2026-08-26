import { afterEach, describe, expect, it } from "vitest";
import {
  ANALYST_GNB_LABELS,
  CALENDAR_CONSUME_UNAVAILABLE,
} from "./gnbChrome";
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
  const requiredSharedLabels = [
    "Language",
    "Evidence",
    "Ask",
    "linked",
    "Post body preview",
    "unresolved",
    "Keymen",
    "Unknown",
    "Image tags",
    "Image regions",
    "Region location",
    "Counterparties",
    "due",
    "Activity",
    "Refresh",
    "Close",
    "Post body",
    "Post",
    "Summary",
    "Calendar",
    "Board",
    "Search",
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
    "Leftover map reconstructs R̂ {value} after IRT main effects. Open this post to read {criterion}.",
    "Two leftover-map axes leave identity remainder {value} of raw residual after IRT main effects. Open this post to read {criterion}.",
    "Read observed Y {observed} and expected E {expected} after IRT main effects, then open this post.",
    "Leftover map has no leftover structure after IRT main effects. Open this post.",
    "Leftover map rank {rank} after IRT main effects. Open this post.",
    "Read leftover map rank {rank}, observed Y {observed}, and expected E {expected} after IRT main effects, then open this post.",
    "Leftover map rank 0 means no leftover structure after IRT main effects. Read observed Y {observed} and expected E {expected}, then open this post.",
    "Showing the first {shown} of {total} posts known at this cutoff.",
    "Connection evidence",
    "Each connection is inferred from independent signals. It is not a causal claim.",
    "No LLM adjudication participated in this connection.",
    "Temporal proximity",
    "Contains",
    "Overlaps",
    "Interval relations",
    "Inspect ontology neighborhood",
    "Ontology neighborhood",
    "This is an ontology neighborhood, not Event Lineage.",
    "Rankings",
    "Title overlap",
    "RankWeave fused newest-first and title-overlap ranks. This is not a calibrated score.",
    "Workspace navigation",
    "Project history",
    "Open project history: {name}",
    "Loading project history. Review the timeline when it appears.",
    "Observed calendar events",
    "No observed calendar events are available.",
    "Open this observed occurrence. It is not a LineageWeave commitment.",
  ] as const;

  it("supports the five product locales", () => {
    expect(SUPPORTED_LOCALES).toEqual(["en", "ko", "zh", "ja", "vi"]);
    expect(Object.keys(LOCALE_LABELS)).toHaveLength(5);
  });

  it.each([
    ["en", "Workspace navigation"],
    ["ko", "워크스페이스 메뉴"],
    ["zh", "工作区导航"],
    ["ja", "ワークスペースナビゲーション"],
    ["vi", "Điều hướng không gian làm việc"],
  ] as const)("drops Buyer from the GNB accessible name in %s", (locale, expected) => {
    setLocale(locale);
    expect(t("Workspace navigation")).toBe(expected);
    expect(t("Workspace navigation")).not.toMatch(/Buyer|Cubee/i);
    expect(t("Buyer navigation")).toBe("Buyer navigation");
  });

  it.each(["ko", "zh", "ja", "vi"] as const)(
    "translates all shared product labels in %s",
    (locale) => {
      setLocale(locale);
      for (const key of requiredSharedLabels) {
        expect(t(key), `${locale}:${key}`).not.toBe(key);
      }
    },
  );

  it("keeps analyst GNB chrome on the Dashboard and four Korean labels", () => {
    expect(ANALYST_GNB_LABELS).toEqual(["Dashboard", "게시판", "고객 마스터", "달력", "Ask Agent"]);
    expect(ANALYST_GNB_LABELS.join(" ")).not.toMatch(/Buyer|Cubee|Board|Customer master/);
    expect(CALENDAR_CONSUME_UNAVAILABLE).toBe("이 범위의 일정을 아직 받을 수 없습니다");
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
    ["ko", "프로젝트 이력", "프로젝트 이력 열기: DEMO"],
    ["zh", "项目历史", "打开项目历史：DEMO"],
    ["ja", "プロジェクト履歴", "プロジェクト履歴を開く: DEMO"],
    ["vi", "Lịch sử dự án", "Mở lịch sử dự án: DEMO"],
  ] as const)("translates project history actions in %s", (locale, heading, action) => {
    setLocale(locale);
    expect(t("Project history")).toBe(heading);
    expect(tf("Open project history: {name}", { name: "DEMO" })).toBe(action);
  });

  it.each([
    ["ko", "글"],
    ["zh", "文章"],
    ["ja", "投稿"],
    ["vi", "Bài viết"],
  ] as const)("translates the ontology Post node label in %s", (locale, expected) => {
    setLocale(locale);
    expect(t("Post")).toBe(expected);
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
    ["ko", "부모", "자식", "부모의 자식에 대한 관계: 포함; 부모 열기"],
    ["zh", "父", "子", "父 与 子 的关系：包含；打开 父"],
    ["ja", "親", "子", "親から子への関係: 含む; 親を開く"],
    ["vi", "cha", "con", "Quan hệ từ cha đến con: Chứa; mở cha"],
  ] as const)("formats directed interval evidence in %s", (locale, from, to, expected) => {
    setLocale(locale);
    expect(
      tf("{from} relates to {to} as {relation}; open {label}", {
        from,
        to,
        relation: t("Contains"),
        label: from,
      }),
    ).toBe(expected);
  });

  it.each([
    ["ko", "영역 위치"],
    ["zh", "区域位置"],
    ["ja", "領域の位置"],
    ["vi", "Vị trí vùng"],
  ] as const)("translates image region location in %s", (locale, expected) => {
    setLocale(locale);
    expect(t("Region location")).toBe(expected);
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
    [
      "ko",
      "잔여 지도의 두 축이 IRT 주효과 이후 원시 잔차의 항등식 나머지 -0.24을(를) 남깁니다. sales-lead 기준을 읽으려면 이 글을 여세요.",
    ],
    [
      "zh",
      "残差图的两个轴在 IRT 主效应后留下原始残差的恒等式余项 -0.24。打开这篇帖子阅读 sales-lead。",
    ],
    [
      "ja",
      "残差マップの2軸はIRT主効果後の生の残差の恒等式の余り -0.24 を残します。この投稿を開いて sales-lead を読んでください。",
    ],
    [
      "vi",
      "Hai trục của bản đồ phần dư để lại phần giao -0.24 của phần dư thô sau hiệu ứng chính IRT. Mở bài viết này để đọc sales-lead.",
    ],
  ] as const)("formats leftover-map cross share next action in %s", (locale, expected) => {
    setLocale(locale);
    expect(
      tf(
        "Two leftover-map axes leave identity remainder {value} of raw residual after IRT main effects. Open this post to read {criterion}.",
        { value: "-0.24", criterion: "sales-lead" },
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

  it.each([
    ["ko", "잔여 지도가 IRT 주효과 이후 R̂ +0.35을(를) 재구성합니다. sales-lead 기준을 읽으려면 이 글을 여세요."],
    ["zh", "残差图在 IRT 主效应后重建 R̂ +0.35。打开这篇帖子阅读 sales-lead。"],
    ["ja", "残差マップはIRT主効果後の R̂ +0.35 を再構成します。この投稿を開いて sales-lead を読んでください。"],
    ["vi", "Bản đồ phần dư tái dựng R̂ +0.35 sau hiệu ứng chính IRT. Mở bài viết này để đọc sales-lead."],
  ] as const)("formats leftover-map reconstruction next action in %s", (locale, expected) => {
    setLocale(locale);
    expect(
      tf(
        "Leftover map reconstructs R̂ {value} after IRT main effects. Open this post to read {criterion}.",
        { value: "+0.35", criterion: "sales-lead" },
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
