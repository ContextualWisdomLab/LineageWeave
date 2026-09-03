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
    "leftover axis {axis} σ {value}",
    "leftover axis {axis} σ {value} {share}%",
    "leftover axis {axis} tick {value}",
    "leftover axis {axis} tick {value} σ {singular}",
    "leftover axis {axis} tick {value} {share}%",
    "leftover axis {axis} tick {value} σ {singular} {share}%",
    "leftover axis {axis} origin tick {value}",
    "leftover axis {axis} origin tick {value} σ {singular}",
    "leftover axis {axis} origin tick {value} {share}%",
    "leftover axis {axis} origin tick {value} σ {singular} {share}%",
    "Leftover-map axis share",
    "Leftover-map axis share is Gabriel inertia of residual SVD axes 1 and 2. Leftover-map singular values are the Gabriel scale of those axes. Open a leftover pair to read the post–criterion cell. The shares and singular values do not invent a leftover score.",
    "Leftover pairs",
    "Closest leftover",
    "Farthest leftover",
    "Leftover residual R {residual} after IRT main effects. Open this post to read {criterion}.",
    "Open leftover {kind} pair: {title} · {criterion}",
    "leftover pair leftover-map post {title} at ξ {person}",
    "leftover pair leftover-map post {title} at leftover-map origin ξ {person}",
    "leftover pair leftover-map criterion {label} at ζ {item}",
    "leftover pair leftover-map criterion {label} at leftover-map origin ζ {item}",
    "leftover map comparison leftover pair leftover-map post {title} at ξ {person}",
    "leftover map comparison leftover pair leftover-map post {title} at leftover-map origin ξ {person}",
    "leftover map comparison leftover pair leftover-map criterion {label} at ζ {item}",
    "leftover map comparison leftover pair leftover-map criterion {label} at leftover-map origin ζ {item}",
    "Open this post to read the criterion it sat closest to after main effects.",
    "Open this post to read the criterion it sat farthest from after main effects.",
    "Leftover map leaves unexplained U {value} after IRT main effects. Open this post to read {criterion}.",
    "Leftover map reconstructs R̂ {value} after IRT main effects. Open this post to read {criterion}.",
    "Two leftover-map axes leave identity remainder {value} of raw residual after IRT main effects. Open this post to read {criterion}.",
    "Leftover map leaves unexplained leftover share {value} of raw residual after IRT main effects. Open this post to read {criterion}.",
    "Leftover map leaves explained leftover share {value} of raw residual after IRT main effects. Open this post to read {criterion}.",
    "Leftover map places this post at ξ {person} and the criterion at ζ {item} after IRT main effects. Open this post to read {criterion}.",
    "Leftover-map graphic display",
    "Leftover map",
    "Post ξ",
    "Criterion ζ",
    "leftover-map criterion {label} at ζ {item}",
    "leftover-map criterion {label} at leftover-map origin ζ {item}",
    "leftover map comparison graphic leftover-map criterion {label} at ζ {item}",
    "leftover map comparison graphic leftover-map criterion {label} at leftover-map origin ζ {item}",
    "leftover-map axis 1",
    "leftover-map axis 2",
    "leftover-map axis {axis} ({share}%)",
    "leftover-map axis {axis} σ {value}",
    "leftover-map axis {axis} σ {value} ({share}%)",
    "leftover-map axis {axis} tick {value}",
    "leftover-map axis {axis} tick {value} σ {singular}",
    "leftover-map axis {axis} tick {value} {share}%",
    "leftover-map axis {axis} tick {value} σ {singular} {share}%",
    "leftover-map axis {axis} origin tick {value}",
    "leftover-map axis {axis} origin tick {value} σ {singular}",
    "leftover-map axis {axis} origin tick {value} {share}%",
    "leftover-map axis {axis} origin tick {value} σ {singular} {share}%",
    "leftover-map origin {origin}",
    "leftover-map distance {label}",
    "leftover-map reconstruction {label}",
    "leftover-map explained leftover share {label}",
    "leftover-map unexplained leftover share {label}",
    "leftover-map cross share {label}",
    "leftover-map unexplained leftover {label}",
    "leftover residual {label}",
    "leftover observed {label}",
    "leftover expected {label}",
    "leftover-map rank {label}",
    "Leftover-map graphic coverage",
    "Leftover map comparison coverage",
    "Leftover map comparison graphic coverage",
    "Leftover map comparison graphic item coverage",
    "Leftover map comparison item coverage",
    "Leftover map comparison incomplete posts",
    "Leftover map comparison graphic incomplete posts",
    "Leftover map comparison incomplete items",
    "Leftover map comparison graphic incomplete items",
    "Leftover map comparison reconstruction",
    "leftover map comparison graphic reconstruction {label}",
    "leftover map comparison graphic explained leftover share {label}",
    "Leftover map comparison explained leftover share",
    "leftover map comparison graphic unexplained leftover share {label}",
    "Leftover map comparison unexplained leftover share",
    "leftover map comparison graphic cross share {label}",
    "Leftover map comparison cross share",
    "leftover map comparison graphic unexplained leftover {label}",
    "Leftover map comparison unexplained leftover",
    "leftover map comparison graphic leftover residual {label}",
    "Leftover map comparison residual",
    "leftover map comparison graphic leftover observed {label}",
    "Leftover map comparison observed",
    "leftover map comparison graphic leftover expected {label}",
    "Leftover map comparison expected",
    "leftover map comparison graphic leftover-map rank {label}",
    "Leftover map comparison rank",
    "leftover map comparison graphic leftover-map distance {label}",
    "leftover map comparison graphic leftover-map axis {axis} tick {value}",
    "leftover map comparison graphic leftover-map axis {axis} tick {value} σ {singular}",
    "leftover map comparison graphic leftover-map axis {axis} tick {value} {share}%",
    "leftover map comparison graphic leftover-map axis {axis} tick {value} σ {singular} {share}%",
    "leftover map comparison graphic leftover-map axis {axis} origin tick {value}",
    "leftover map comparison graphic leftover-map axis {axis} origin tick {value} σ {singular}",
    "leftover map comparison graphic leftover-map axis {axis} origin tick {value} {share}%",
    "leftover map comparison graphic leftover-map axis {axis} origin tick {value} σ {singular} {share}%",
    "leftover map comparison graphic leftover-map axis {axis} σ {value}",
    "leftover map comparison graphic leftover-map axis {axis} σ {value} ({share}%)",
    "leftover map comparison leftover axis {axis} σ {value}",
    "leftover map comparison leftover axis {axis} σ {value} {share}%",
    "leftover map comparison leftover axis {axis} {share}%",
    "leftover map comparison leftover axis {axis} tick {value}",
    "leftover map comparison leftover axis {axis} tick {value} σ {singular}",
    "leftover map comparison leftover axis {axis} tick {value} {share}%",
    "leftover map comparison leftover axis {axis} tick {value} σ {singular} {share}%",
    "leftover map comparison leftover axis {axis} origin tick {value}",
    "leftover map comparison leftover axis {axis} origin tick {value} σ {singular}",
    "leftover map comparison leftover axis {axis} origin tick {value} {share}%",
    "leftover map comparison leftover axis {axis} origin tick {value} σ {singular} {share}%",
    "Leftover map comparison leftover axis",
    "Leftover map comparison leftover-axis share is Gabriel inertia of residual SVD axes 1 and 2. Open a leftover pair to read the post–criterion cell. The shares do not invent a leftover score.",
    "Leftover map comparison coordinates",
    "Leftover map comparison graphic",
    "Leftover map comparison",
    "leftover map comparison axis 1",
    "leftover map comparison axis 2",
    "leftover map comparison axis {axis} ({share}%)",
    "Leftover map comparison graphic of already-named coordinates. Click a post marker to open that post. The plot does not invent a leftover score.",
    "Leftover-map graphic item coverage",
    "Leftover map item coverage",
    "Leftover map incomplete posts",
    "Leftover map incomplete items",
    "Leftover-map graphic incomplete posts",
    "Leftover-map graphic incomplete items",
    "Leftover map used {used} of {scored} scored criteria (complete-case)",
    "Leftover map dropped {dropped} incomplete posts",
    "Leftover map dropped {dropped} incomplete criteria",
    "Leftover map after IRT main effects. Axis ticks name persisted leftover-map coordinates. Pair segments name leftover-map distance d, leftover-map reconstruction R̂, leftover-map explained leftover share e, leftover-map unexplained leftover share s, leftover-map cross share x, leftover-map unexplained leftover U, leftover residual R, leftover observed Y, leftover expected E, and leftover-map rank. The plot names leftover-map complete-case coverage, leftover-map item complete-case coverage, leftover-map incomplete post coverage, and leftover-map incomplete item coverage when persisted. Click a post marker to open that post. The plot does not invent a leftover score.",
    "Open leftover-map post {title} at ξ {person}",
    "Open leftover-map post {title} at leftover-map origin ξ {person}",
    "Open leftover-map post {title}",
    "Open leftover map comparison graphic leftover-map post {title} at ξ {person}",
    "Open leftover map comparison graphic leftover-map post {title} at leftover-map origin ξ {person}",
    "leftover map comparison graphic leftover-map criterion {label} at leftover-map origin ζ {item}",
    "leftover pair leftover-map post {title} at leftover-map origin ξ {person}",
    "leftover map comparison leftover pair leftover-map post {title} at leftover-map origin ξ {person}",
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
    "Rankings combine newest-first and title-overlap evidence and are not calibrated scores. Open a ranked post to see its evidence.",
    "Workspace navigation",
    "Project history",
    "Open project history: {name}",
    "Loading project history. Review the timeline when it appears.",
    "Observed calendar events",
    "No observed calendar events are available.",
    "Open this observed occurrence. It is not a LineageWeave commitment.",
    "Collect stronger authoritative evidence before accepting the claim.",
    "Inspect the authorized cited posts and their evidence.",
    "Review unavailable historical channels before relying on this cutoff answer.",
    "Compare these cutoff-grounded citations with live evidence next.",
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
    [
      "ko",
      "잔여 지도가 IRT 주효과 이후 원시 잔차의 설명되지 않은 잔여 비율 0.02을(를) 남깁니다. sales-lead 기준을 읽으려면 이 글을 여세요.",
    ],
    [
      "zh",
      "残差图在 IRT 主效应后留下原始残差的未解释残余份额 0.02。打开这篇帖子阅读 sales-lead。",
    ],
    [
      "ja",
      "残差マップはIRT主効果後の生の残差の未説明残差シェア 0.02 を残します。この投稿を開いて sales-lead を読んでください。",
    ],
    [
      "vi",
      "Bản đồ phần dư để lại tỷ phần phần dư chưa giải thích 0.02 của phần dư thô sau hiệu ứng chính IRT. Mở bài viết này để đọc sales-lead.",
    ],
  ] as const)("formats leftover-map unexplained leftover share next action in %s", (locale, expected) => {
    setLocale(locale);
    expect(
      tf(
        "Leftover map leaves unexplained leftover share {value} of raw residual after IRT main effects. Open this post to read {criterion}.",
        { value: "0.02", criterion: "sales-lead" },
      ),
    ).toBe(expected);
  });

  it.each([
    [
      "ko",
      "잔여 지도가 IRT 주효과 이후 원시 잔차의 설명된 잔여 비율 0.76을(를) 남깁니다. sales-lead 기준을 읽으려면 이 글을 여세요.",
    ],
    [
      "zh",
      "残差图在 IRT 主效应后留下原始残差的已解释残余份额 0.76。打开这篇帖子阅读 sales-lead。",
    ],
    [
      "ja",
      "残差マップはIRT主効果後の生の残差の説明済み残差シェア 0.76 を残します。この投稿を開いて sales-lead を読んでください。",
    ],
    [
      "vi",
      "Bản đồ phần dư để lại tỷ phần phần dư đã giải thích 0.76 của phần dư thô sau hiệu ứng chính IRT. Mở bài viết này để đọc sales-lead.",
    ],
  ] as const)("formats leftover-map explained leftover share next action in %s", (locale, expected) => {
    setLocale(locale);
    expect(
      tf(
        "Leftover map leaves explained leftover share {value} of raw residual after IRT main effects. Open this post to read {criterion}.",
        { value: "0.76", criterion: "sales-lead" },
      ),
    ).toBe(expected);
  });

  it.each([
    [
      "ko",
      "잔여 지도가 IRT 주효과 이후 이 글을 ξ (+0.50, +0.10)에, 기준을 ζ (+0.50, −0.02)에 둡니다. sales-lead 기준을 읽으려면 이 글을 여세요.",
    ],
    [
      "zh",
      "残差图在 IRT 主效应后将这篇帖子放在 ξ (+0.50, +0.10)，将准则放在 ζ (+0.50, −0.02)。打开这篇帖子阅读 sales-lead。",
    ],
    [
      "ja",
      "残差マップはIRT主効果後にこの投稿を ξ (+0.50, +0.10) に、基準を ζ (+0.50, −0.02) に置きます。この投稿を開いて sales-lead を読んでください。",
    ],
    [
      "vi",
      "Bản đồ phần dư đặt bài viết này tại ξ (+0.50, +0.10) và tiêu chí tại ζ (+0.50, −0.02) sau hiệu ứng chính IRT. Mở bài viết này để đọc sales-lead.",
    ],
  ] as const)("formats leftover-map coordinates next action in %s", (locale, expected) => {
    setLocale(locale);
    expect(
      tf(
        "Leftover map places this post at ξ {person} and the criterion at ζ {item} after IRT main effects. Open this post to read {criterion}.",
        { person: "(+0.50, +0.10)", item: "(+0.50, −0.02)", criterion: "sales-lead" },
      ),
    ).toBe(expected);
  });

  it.each([
    [
      "ko",
      "IRT 주효과 이후 잔여 지도입니다. 축 눈금은 저장된 잔여 지도 좌표입니다. 쌍 선분은 잔여 지도 거리 d, 잔여 지도 재구성 R̂, 잔여 지도 설명 잔여 점유율 e, 잔여 지도 미설명 잔여 점유율 s, 잔여 지도 교차 점유율 x, 잔여 지도 미설명 잔여 U, 잔여 R, 관측 Y, 기대 E, 잔여 지도 순위입니다. 저장된 완전사례 포함 범위와 기준 포함 범위와 불완전 글과 불완전 기준이 있으면 그림이 그 범위를 표시합니다. 글 표식을 눌러 그 글을 여세요. 이 그림은 잔여 점수를 만들어내지 않습니다.",
    ],
    ["zh", "IRT 主效应后的残差图。轴刻度标出已保存的残差图坐标。配对线段标出残差图距离 d、残差图重建 R̂、残差图已解释残差份额 e、残差图未解释残差份额 s、残差图交叉份额 x、残差图未解释残差 U、残差 R、观测 Y、期望 E 与残差图秩。图在已保存时标出完全案例覆盖范围、准则完全案例覆盖范围、不完整帖文与不完整准则。点击帖子标记打开该帖子。此图不会虚构残差分数。"],
    [
      "ja",
      "IRT主効果後の残差マップです。軸目盛は保存済みの残差マップ座標です。ペア線分は残差マップ距離 d、残差マップ再構成 R̂、残差マップ説明済み残差割合 e、残差マップ未説明残差割合 s、残差マップ交差割合 x、残差マップ未説明残差 U、残差 R、観測 Y、期待 E、残差マップ階数です。保存済みの完全ケース対象範囲と基準の完全ケース対象範囲と不完全投稿と不完全基準があるときはその範囲を示します。投稿マーカーをクリックしてその投稿を開いてください。この図は残差スコアを作りません。",
    ],
    [
      "vi",
      "Bản đồ phần dư sau hiệu ứng chính IRT. Vạch trục ghi tọa độ bản đồ phần dư đã lưu. Đoạn cặp ghi khoảng cách bản đồ phần dư d, tái dựng bản đồ phần dư R̂, phần dư giải thích e, phần dư chưa giải thích s, phần giao x, phần dư chưa giải thích U, phần dư R, Y quan sát, E kỳ vọng và hạng bản đồ phần dư. Hình ghi phạm vi trường hợp đầy đủ của bài viết và tiêu chí cùng bài không đầy đủ và tiêu chí không đầy đủ khi đã lưu. Nhấn dấu bài viết để mở bài đó. Hình này không tạo ra điểm phần dư.",
    ],
  ] as const)("formats leftover-map graphic display caption in %s", (locale, expected) => {
    setLocale(locale);
    expect(
      t(
        "Leftover map after IRT main effects. Axis ticks name persisted leftover-map coordinates. Pair segments name leftover-map distance d, leftover-map reconstruction R̂, leftover-map explained leftover share e, leftover-map unexplained leftover share s, leftover-map cross share x, leftover-map unexplained leftover U, leftover residual R, leftover observed Y, leftover expected E, and leftover-map rank. The plot names leftover-map complete-case coverage, leftover-map item complete-case coverage, leftover-map incomplete post coverage, and leftover-map incomplete item coverage when persisted. Click a post marker to open that post. The plot does not invent a leftover score.",
      ),
    ).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 기준 sales-lead (ζ (+0.50, −0.02))"],
    ["zh", "残差图准则 sales-lead（ζ (+0.50, −0.02)）"],
    ["ja", "残差マップの基準 sales-lead（ζ (+0.50, −0.02)）"],
    ["vi", "tiêu chí bản đồ phần dư sales-lead tại ζ (+0.50, −0.02)"],
  ] as const)("formats leftover-map graphic leftover-map criterion ζ in %s", (locale, expected) => {
    setLocale(locale);
    expect(
      tf("leftover-map criterion {label} at ζ {item}", {
        label: "sales-lead",
        item: "(+0.50, −0.02)",
      }),
    ).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 원점 기준 sales-lead (ζ (0.00, 0.00))"],
    ["zh", "残差图原点准则 sales-lead（ζ (0.00, 0.00)）"],
    ["ja", "残差マップの原点基準 sales-lead（ζ (0.00, 0.00)）"],
    ["vi", "tiêu chí gốc bản đồ phần dư sales-lead tại ζ (0.00, 0.00)"],
  ] as const)(
    "formats leftover-map graphic leftover-map criterion leftover-map origin ζ in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("leftover-map criterion {label} at leftover-map origin ζ {item}", {
          label: "sales-lead",
          item: "(0.00, 0.00)",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 그림 원점 기준 sales-lead (ζ (0.00, 0.00))"],
    ["zh", "残差地图比较图形原点准则 sales-lead（ζ (0.00, 0.00)）"],
    ["ja", "残差マップの比較図原点基準 sales-lead（ζ (0.00, 0.00)）"],
    ["vi", "tiêu chí gốc đồ họa so sánh bản đồ phần dư sales-lead tại ζ (0.00, 0.00)"],
  ] as const)(
    "formats leftover map comparison graphic leftover-map criterion leftover-map origin ζ in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("leftover map comparison graphic leftover-map criterion {label} at leftover-map origin ζ {item}", {
          label: "sales-lead",
          item: "(0.00, 0.00)",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 쌍 잔여 지도 원점 글 Public post (ξ (0.00, 0.00))"],
    ["zh", "残差配对残差图原点帖子 Public post（ξ (0.00, 0.00)）"],
    ["ja", "残差ペアの残差マップ原点投稿 Public post（ξ (0.00, 0.00)）"],
    ["vi", "Cặp phần dư bài gốc bản đồ phần dư Public post tại ξ (0.00, 0.00)"],
  ] as const)(
    "formats leftover-map pair leftover-map post leftover-map origin ξ in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("leftover pair leftover-map post {title} at leftover-map origin ξ {person}", {
          title: "Public post",
          person: "(0.00, 0.00)",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 잔여 쌍 잔여 지도 원점 글 Public post (ξ (0.00, 0.00))"],
    ["zh", "残差图比较残差配对残差图原点帖子 Public post（ξ (0.00, 0.00)）"],
    ["ja", "残差マップ比較の残差ペアの残差マップ原点投稿 Public post（ξ (0.00, 0.00)）"],
    ["vi", "Cặp phần dư so sánh bản đồ phần dư bài gốc Public post tại ξ (0.00, 0.00)"],
  ] as const)(
    "formats leftover-map comparison leftover-pair leftover-map post leftover-map origin ξ in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("leftover map comparison leftover pair leftover-map post {title} at leftover-map origin ξ {person}", {
          title: "Public post",
          person: "(0.00, 0.00)",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 원점 글 Public post 열기 (ξ (0.00, 0.00))"],
    ["zh", "打开残差图原点帖子 Public post（ξ (0.00, 0.00)）"],
    ["ja", "残差マップの原点投稿 Public post を開く（ξ (0.00, 0.00)）"],
    ["vi", "Mở bài viết gốc bản đồ phần dư Public post tại ξ (0.00, 0.00)"],
  ] as const)(
    "formats leftover-map graphic leftover-map post leftover-map origin ξ in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("Open leftover-map post {title} at leftover-map origin ξ {person}", {
          title: "Public post",
          person: "(0.00, 0.00)",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 그림 기준 sales-lead (ζ (+0.50, −0.02))"],
    ["zh", "残差地图比较图形准则 sales-lead（ζ (+0.50, −0.02)）"],
    ["ja", "残差マップの比較図基準 sales-lead（ζ (+0.50, −0.02)）"],
    ["vi", "tiêu chí đồ họa so sánh bản đồ phần dư sales-lead tại ζ (+0.50, −0.02)"],
  ] as const)("formats leftover map comparison graphic leftover-map criterion ζ in %s", (locale, expected) => {
    setLocale(locale);
    expect(
      tf("leftover map comparison graphic leftover-map criterion {label} at ζ {item}", {
        label: "sales-lead",
        item: "(+0.50, −0.02)",
      }),
    ).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 비교 그림 글 Public post 열기 (ξ (+0.50, +0.10))"],
    ["zh", "打开残差地图比较图形帖子 Public post（ξ (+0.50, +0.10)）"],
    ["ja", "残差マップの比較図の投稿 Public post を開く（ξ (+0.50, +0.10)）"],
    ["vi", "Mở bài đồ họa so sánh bản đồ phần dư Public post tại ξ (+0.50, +0.10)"],
  ] as const)("formats leftover map comparison graphic leftover-map post ξ in %s", (locale, expected) => {
    setLocale(locale);
    expect(
      tf("Open leftover map comparison graphic leftover-map post {title} at ξ {person}", {
        title: "Public post",
        person: "(+0.50, +0.10)",
      }),
    ).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 비교 그림 원점 글 Public post 열기 (ξ (0.00, 0.00))"],
    ["zh", "打开残差地图比较图形原点帖子 Public post（ξ (0.00, 0.00)）"],
    ["ja", "残差マップの比較図の原点投稿 Public post を開く（ξ (0.00, 0.00)）"],
    ["vi", "Mở bài gốc đồ họa so sánh bản đồ phần dư Public post tại ξ (0.00, 0.00)"],
  ] as const)(
    "formats leftover map comparison graphic leftover-map post leftover-map origin ξ in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("Open leftover map comparison graphic leftover-map post {title} at leftover-map origin ξ {person}", {
          title: "Public post",
          person: "(0.00, 0.00)",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 그림 포함 범위"],
    ["zh", "残差图图形覆盖范围"],
    ["ja", "残差マップ図の対象範囲"],
    ["vi", "Phạm vi đồ họa bản đồ phần dư"],
  ] as const)("formats leftover-map graphic coverage label in %s", (locale, expected) => {
    setLocale(locale);
    expect(t("Leftover-map graphic coverage")).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 비교 포함 범위"],
    ["zh", "残差地图比较覆盖范围"],
    ["ja", "残差マップの比較対象範囲"],
    ["vi", "Phạm vi so sánh bản đồ phần dư"],
  ] as const)("formats leftover map comparison coverage label in %s", (locale, expected) => {
    setLocale(locale);
    expect(t("Leftover map comparison coverage")).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 비교 그림 포함 범위"],
    ["zh", "残差地图比较图形覆盖范围"],
    ["ja", "残差マップの比較図対象範囲"],
    ["vi", "Phạm vi đồ họa so sánh bản đồ phần dư"],
  ] as const)("formats leftover map comparison graphic coverage label in %s", (locale, expected) => {
    setLocale(locale);
    expect(t("Leftover map comparison graphic coverage")).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 비교 그림 기준 포함 범위"],
    ["zh", "残差地图比较图形准则覆盖范围"],
    ["ja", "残差マップの比較図基準対象範囲"],
    ["vi", "Phạm vi tiêu chí đồ họa so sánh bản đồ phần dư"],
  ] as const)("formats leftover map comparison graphic item coverage label in %s", (locale, expected) => {
    setLocale(locale);
    expect(t("Leftover map comparison graphic item coverage")).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 비교 기준 포함 범위"],
    ["zh", "残差地图比较准则覆盖范围"],
    ["ja", "残差マップの比較基準対象範囲"],
    ["vi", "Phạm vi so sánh tiêu chí bản đồ phần dư"],
  ] as const)("formats leftover map comparison item coverage label in %s", (locale, expected) => {
    setLocale(locale);
    expect(t("Leftover map comparison item coverage")).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 비교 불완전 글"],
    ["zh", "残差地图比较不完整帖文"],
    ["ja", "残差マップの比較不完全投稿"],
    ["vi", "Bài không đầy đủ so sánh trên bản đồ phần dư"],
  ] as const)("formats leftover map comparison incomplete posts label in %s", (locale, expected) => {
    setLocale(locale);
    expect(t("Leftover map comparison incomplete posts")).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 비교 그림 불완전 글"],
    ["zh", "残差地图比较图形不完整帖文"],
    ["ja", "残差マップの比較図不完全投稿"],
    ["vi", "Bài không đầy đủ đồ họa so sánh trên bản đồ phần dư"],
  ] as const)("formats leftover map comparison graphic incomplete posts label in %s", (locale, expected) => {
    setLocale(locale);
    expect(t("Leftover map comparison graphic incomplete posts")).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 비교 불완전 기준"],
    ["zh", "残差地图比较不完整准则"],
    ["ja", "残差マップの比較不完全基準"],
    ["vi", "Tiêu chí không đầy đủ so sánh trên bản đồ phần dư"],
  ] as const)("formats leftover map comparison incomplete items label in %s", (locale, expected) => {
    setLocale(locale);
    expect(t("Leftover map comparison incomplete items")).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 비교 그림 불완전 기준"],
    ["zh", "残差地图比较图形不完整准则"],
    ["ja", "残差マップの比較図不完全基準"],
    ["vi", "Tiêu chí không đầy đủ đồ họa so sánh trên bản đồ phần dư"],
  ] as const)("formats leftover map comparison graphic incomplete items label in %s", (locale, expected) => {
    setLocale(locale);
    expect(t("Leftover map comparison graphic incomplete items")).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 비교 재구성"],
    ["zh", "残差地图比较重建"],
    ["ja", "残差マップの比較再構成"],
    ["vi", "Tái dựng so sánh bản đồ phần dư"],
  ] as const)("formats leftover map comparison reconstruction label in %s", (locale, expected) => {
    setLocale(locale);
    expect(t("Leftover map comparison reconstruction")).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 비교 그림 재구성 R̂ +0.35"],
    ["zh", "残差地图比较图形重建 R̂ +0.35"],
    ["ja", "残差マップの比較図再構成 R̂ +0.35"],
    ["vi", "tái dựng đồ họa so sánh bản đồ phần dư R̂ +0.35"],
  ] as const)("formats leftover map comparison graphic reconstruction in %s", (locale, expected) => {
    setLocale(locale);
    expect(tf("leftover map comparison graphic reconstruction {label}", { label: "R̂ +0.35" })).toBe(
      expected,
    );
  });

  it.each([
    ["ko", "잔여 지도 비교 그림 설명 잔여 점유율 R̂²/R² 0.76"],
    ["zh", "残差地图比较图形已解释残差份额 R̂²/R² 0.76"],
    ["ja", "残差マップの比較図説明済み残差割合 R̂²/R² 0.76"],
    ["vi", "phần dư giải thích đồ họa so sánh bản đồ phần dư R̂²/R² 0.76"],
  ] as const)(
    "formats leftover map comparison graphic explained leftover share in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("leftover map comparison graphic explained leftover share {label}", {
          label: "R̂²/R² 0.76",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 그림 미설명 잔여 점유율 U²/R² 0.02"],
    ["zh", "残差地图比较图形未解释残差份额 U²/R² 0.02"],
    ["ja", "残差マップの比較図未説明残差割合 U²/R² 0.02"],
    ["vi", "phần dư chưa giải thích đồ họa so sánh bản đồ phần dư U²/R² 0.02"],
  ] as const)(
    "formats leftover map comparison graphic unexplained leftover share in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("leftover map comparison graphic unexplained leftover share {label}", {
          label: "U²/R² 0.02",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 그림 교차 점유율 2R̂U/R² 0.12"],
    ["zh", "残差地图比较图形交叉份额 2R̂U/R² 0.12"],
    ["ja", "残差マップの比較図交差割合 2R̂U/R² 0.12"],
    ["vi", "phần giao đồ họa so sánh bản đồ phần dư 2R̂U/R² 0.12"],
  ] as const)(
    "formats leftover map comparison graphic cross share in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("leftover map comparison graphic cross share {label}", {
          label: "2R̂U/R² 0.12",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 그림 미설명 잔여 U +0.05"],
    ["zh", "残差地图比较图形未解释残差 U +0.05"],
    ["ja", "残差マップの比較図未説明残差 U +0.05"],
    ["vi", "phần dư chưa giải thích đồ họa so sánh U +0.05"],
  ] as const)(
    "formats leftover map comparison graphic unexplained leftover in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("leftover map comparison graphic unexplained leftover {label}", {
          label: "U +0.05",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 그림 잔여 R +0.40"],
    ["zh", "残差地图比较图形残差 R +0.40"],
    ["ja", "残差マップの比較図残差 R +0.40"],
    ["vi", "phần dư đồ họa so sánh bản đồ phần dư R +0.40"],
  ] as const)(
    "formats leftover map comparison graphic leftover residual in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("leftover map comparison graphic leftover residual {label}", {
          label: "R +0.40",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 그림 관측 Y 2.40"],
    ["zh", "残差地图比较图形观测 Y 2.40"],
    ["ja", "残差マップの比較図観測 Y 2.40"],
    ["vi", "quan sát đồ họa so sánh bản đồ phần dư Y 2.40"],
  ] as const)(
    "formats leftover map comparison graphic leftover observed in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("leftover map comparison graphic leftover observed {label}", {
          label: "Y 2.40",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 그림 기대 E 2.00"],
    ["zh", "残差地图比较图形期望 E 2.00"],
    ["ja", "残差マップの比較図期待 E 2.00"],
    ["vi", "kỳ vọng đồ họa so sánh bản đồ phần dư E 2.00"],
  ] as const)(
    "formats leftover map comparison graphic leftover expected in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("leftover map comparison graphic leftover expected {label}", {
          label: "E 2.00",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 그림 순위 rank 1"],
    ["zh", "残差地图比较图形秩 rank 1"],
    ["ja", "残差マップの比較図階数 rank 1"],
    ["vi", "hạng đồ họa so sánh bản đồ phần dư rank 1"],
  ] as const)(
    "formats leftover map comparison graphic leftover-map rank in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("leftover map comparison graphic leftover-map rank {label}", {
          label: "rank 1",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 그림 거리 d 0.12"],
    ["zh", "残差地图比较图形距离 d 0.12"],
    ["ja", "残差マップの比較図距離 d 0.12"],
    ["vi", "khoảng cách đồ họa so sánh bản đồ phần dư d 0.12"],
  ] as const)(
    "formats leftover map comparison graphic leftover-map distance in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("leftover map comparison graphic leftover-map distance {label}", {
          label: "d 0.12",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 그림 축 1 눈금 +0.50"],
    ["zh", "残差地图比较图形轴 1 刻度 +0.50"],
    ["ja", "残差マップの比較図軸 1 目盛 +0.50"],
    ["vi", "vạch trục đồ họa so sánh bản đồ phần dư 1 +0.50"],
  ] as const)(
    "formats leftover map comparison graphic leftover-map axis ticks in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("leftover map comparison graphic leftover-map axis {axis} tick {value}", {
          axis: 1,
          value: "+0.50",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 그림 축 1 눈금 +0.50 σ 1.84"],
    ["zh", "残差地图比较图形轴 1 刻度 +0.50 σ 1.84"],
    ["ja", "残差マップの比較図軸 1 目盛 +0.50 σ 1.84"],
    ["vi", "vạch trục đồ họa so sánh bản đồ phần dư 1 +0.50 σ 1.84"],
  ] as const)(
    "formats leftover map comparison graphic leftover-map axis tick singular values in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("leftover map comparison graphic leftover-map axis {axis} tick {value} σ {singular}", {
          axis: 1,
          value: "+0.50",
          singular: "1.84",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 그림 축 1 눈금 +0.50 82%"],
    ["zh", "残差地图比较图形轴 1 刻度 +0.50 82%"],
    ["ja", "残差マップの比較図軸 1 目盛 +0.50 82%"],
    ["vi", "vạch trục đồ họa so sánh bản đồ phần dư 1 +0.50 82%"],
  ] as const)(
    "formats leftover map comparison graphic leftover-map axis tick leftover-map axis share in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("leftover map comparison graphic leftover-map axis {axis} tick {value} {share}%", {
          axis: 1,
          value: "+0.50",
          share: "82",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 그림 축 1 눈금 +0.50 σ 1.84 82%"],
    ["zh", "残差地图比较图形轴 1 刻度 +0.50 σ 1.84 82%"],
    ["ja", "残差マップの比較図軸 1 目盛 +0.50 σ 1.84 82%"],
    ["vi", "vạch trục đồ họa so sánh bản đồ phần dư 1 +0.50 σ 1.84 82%"],
  ] as const)(
    "formats leftover map comparison graphic leftover-map axis tick leftover-map singular values and leftover-map axis share in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf(
          "leftover map comparison graphic leftover-map axis {axis} tick {value} σ {singular} {share}%",
          {
            axis: 1,
            value: "+0.50",
            singular: "1.84",
            share: "82",
          },
        ),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 그림 축 1 원점 눈금 0.00"],
    ["zh", "残差地图比较图形轴 1 原点刻度 0.00"],
    ["ja", "残差マップの比較図軸 1 原点目盛 0.00"],
    ["vi", "vạch gốc trục đồ họa so sánh bản đồ phần dư 1 0.00"],
  ] as const)(
    "formats leftover map comparison graphic leftover-map axis origin ticks in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("leftover map comparison graphic leftover-map axis {axis} origin tick {value}", {
          axis: 1,
          value: "0.00",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 그림 축 1 원점 눈금 0.00 σ 0.00 0%"],
    ["zh", "残差地图比较图形轴 1 原点刻度 0.00 σ 0.00 0%"],
    ["ja", "残差マップの比較図軸 1 原点目盛 0.00 σ 0.00 0%"],
    ["vi", "vạch gốc trục đồ họa so sánh bản đồ phần dư 1 0.00 σ 0.00 0%"],
  ] as const)(
    "formats leftover map comparison graphic leftover-map axis origin ticks leftover-map singular values and leftover-map axis share in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf(
          "leftover map comparison graphic leftover-map axis {axis} origin tick {value} σ {singular} {share}%",
          {
            axis: 1,
            value: "0.00",
            singular: "0.00",
            share: "0",
          },
        ),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 그림 축 1 σ 1.84"],
    ["zh", "残差地图比较图形轴 1 σ 1.84"],
    ["ja", "残差マップの比較図軸 1 σ 1.84"],
    ["vi", "trục đồ họa so sánh bản đồ phần dư 1 σ 1.84"],
  ] as const)(
    "formats leftover map comparison graphic leftover-map axis singular values in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("leftover map comparison graphic leftover-map axis {axis} σ {value}", {
          axis: 1,
          value: "1.84",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 그림 축 1 σ 1.84 (82%)"],
    ["zh", "残差地图比较图形轴 1 σ 1.84 (82%)"],
    ["ja", "残差マップの比較図軸 1 σ 1.84 (82%)"],
    ["vi", "trục đồ họa so sánh bản đồ phần dư 1 σ 1.84 (82%)"],
  ] as const)(
    "formats leftover map comparison graphic leftover-map axis singular share in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("leftover map comparison graphic leftover-map axis {axis} σ {value} ({share}%)", {
          axis: 1,
          value: "1.84",
          share: "82",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔차 축 1 σ 1.84 82%"],
    ["zh", "残差轴 1 σ 1.84 82%"],
    ["ja", "残差軸 1 σ 1.84 82%"],
    ["vi", "trục phần dư 1 σ 1.84 82%"],
  ] as const)("formats leftover-axis badge singular value with share in %s", (locale, expected) => {
    setLocale(locale);
    expect(
      tf("leftover axis {axis} σ {value} {share}%", { axis: 1, value: "1.84", share: "82" }),
    ).toBe(expected);
  });

  it.each([
    ["ko", "잔차 축 1 σ 1.84"],
    ["zh", "残差轴 1 σ 1.84"],
    ["ja", "残差軸 1 σ 1.84"],
    ["vi", "trục phần dư 1 σ 1.84"],
  ] as const)("formats leftover-axis badge singular values without share in %s", (locale, expected) => {
    setLocale(locale);
    expect(tf("leftover axis {axis} σ {value}", { axis: 1, value: "1.84" })).toBe(expected);
  });

  it.each([
    ["ko", "잔차 축 1 눈금 +0.50"],
    ["zh", "残差轴 1 刻度 +0.50"],
    ["ja", "残差軸 1 目盛 +0.50"],
    ["vi", "vạch trục phần dư 1 +0.50"],
  ] as const)("formats leftover-axis ticks in %s", (locale, expected) => {
    setLocale(locale);
    expect(tf("leftover axis {axis} tick {value}", { axis: 1, value: "+0.50" })).toBe(expected);
  });

  it.each([
    ["ko", "잔차 축 1 눈금 +0.50 σ 1.84"],
    ["zh", "残差轴 1 刻度 +0.50 σ 1.84"],
    ["ja", "残差軸 1 目盛 +0.50 σ 1.84"],
    ["vi", "vạch trục phần dư 1 +0.50 σ 1.84"],
  ] as const)("formats leftover-axis tick singular values in %s", (locale, expected) => {
    setLocale(locale);
    expect(
      tf("leftover axis {axis} tick {value} σ {singular}", {
        axis: 1,
        value: "+0.50",
        singular: "1.84",
      }),
    ).toBe(expected);
  });

  it.each([
    ["ko", "잔차 축 1 눈금 +0.50 82%"],
    ["zh", "残差轴 1 刻度 +0.50 82%"],
    ["ja", "残差軸 1 目盛 +0.50 82%"],
    ["vi", "vạch trục phần dư 1 +0.50 82%"],
  ] as const)("formats leftover-axis tick leftover-map axis share in %s", (locale, expected) => {
    setLocale(locale);
    expect(
      tf("leftover axis {axis} tick {value} {share}%", {
        axis: 1,
        value: "+0.50",
        share: "82",
      }),
    ).toBe(expected);
  });

  it.each([
    ["ko", "잔차 축 1 원점 눈금 0.00"],
    ["zh", "残差轴 1 原点刻度 0.00"],
    ["ja", "残差軸 1 原点目盛 0.00"],
    ["vi", "vạch gốc trục phần dư 1 0.00"],
  ] as const)("formats leftover-axis origin ticks in %s", (locale, expected) => {
    setLocale(locale);
    expect(tf("leftover axis {axis} origin tick {value}", { axis: 1, value: "0.00" })).toBe(expected);
  });

  it.each([
    ["ko", "잔차 축 1 원점 눈금 0.00 σ 0.00 0%"],
    ["zh", "残差轴 1 原点刻度 0.00 σ 0.00 0%"],
    ["ja", "残差軸 1 原点目盛 0.00 σ 0.00 0%"],
    ["vi", "vạch gốc trục phần dư 1 0.00 σ 0.00 0%"],
  ] as const)(
    "formats leftover-axis origin ticks leftover-map singular values and leftover-map axis share in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("leftover axis {axis} origin tick {value} σ {singular} {share}%", {
          axis: 1,
          value: "0.00",
          singular: "0.00",
          share: "0",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔차 축 1 눈금 +0.50 σ 1.84 82%"],
    ["zh", "残差轴 1 刻度 +0.50 σ 1.84 82%"],
    ["ja", "残差軸 1 目盛 +0.50 σ 1.84 82%"],
    ["vi", "vạch trục phần dư 1 +0.50 σ 1.84 82%"],
  ] as const)(
    "formats leftover-axis tick leftover-map singular values and leftover-map axis share in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("leftover axis {axis} tick {value} σ {singular} {share}%", {
          axis: 1,
          value: "+0.50",
          singular: "1.84",
          share: "82",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 잔차 축 1 σ 1.84"],
    ["zh", "残差地图比较残差轴 1 σ 1.84"],
    ["ja", "残差マップの比較残差軸 1 σ 1.84"],
    ["vi", "trục phần dư so sánh bản đồ phần dư 1 σ 1.84"],
  ] as const)(
    "formats leftover map comparison leftover-axis singular values in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("leftover map comparison leftover axis {axis} σ {value}", {
          axis: 1,
          value: "1.84",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 잔차 축 1 눈금 +0.50"],
    ["zh", "残差地图比较残差轴 1 刻度 +0.50"],
    ["ja", "残差マップの比較残差軸 1 目盛 +0.50"],
    ["vi", "vạch trục phần dư so sánh bản đồ phần dư 1 +0.50"],
  ] as const)(
    "formats leftover map comparison leftover-axis ticks in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("leftover map comparison leftover axis {axis} tick {value}", {
          axis: 1,
          value: "+0.50",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 잔차 축 1 눈금 +0.50 σ 1.84"],
    ["zh", "残差地图比较残差轴 1 刻度 +0.50 σ 1.84"],
    ["ja", "残差マップの比較残差軸 1 目盛 +0.50 σ 1.84"],
    ["vi", "vạch trục phần dư so sánh bản đồ phần dư 1 +0.50 σ 1.84"],
  ] as const)(
    "formats leftover map comparison leftover-axis tick singular values in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("leftover map comparison leftover axis {axis} tick {value} σ {singular}", {
          axis: 1,
          value: "+0.50",
          singular: "1.84",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 잔차 축 1 눈금 +0.50 82%"],
    ["zh", "残差地图比较残差轴 1 刻度 +0.50 82%"],
    ["ja", "残差マップの比較残差軸 1 目盛 +0.50 82%"],
    ["vi", "vạch trục phần dư so sánh bản đồ phần dư 1 +0.50 82%"],
  ] as const)(
    "formats leftover map comparison leftover-axis tick leftover-map axis share in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("leftover map comparison leftover axis {axis} tick {value} {share}%", {
          axis: 1,
          value: "+0.50",
          share: "82",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 잔차 축 1 눈금 +0.50 σ 1.84 82%"],
    ["zh", "残差地图比较残差轴 1 刻度 +0.50 σ 1.84 82%"],
    ["ja", "残差マップの比較残差軸 1 目盛 +0.50 σ 1.84 82%"],
    ["vi", "vạch trục phần dư so sánh bản đồ phần dư 1 +0.50 σ 1.84 82%"],
  ] as const)(
    "formats leftover map comparison leftover-axis tick leftover-map singular values and leftover-map axis share in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("leftover map comparison leftover axis {axis} tick {value} σ {singular} {share}%", {
          axis: 1,
          value: "+0.50",
          singular: "1.84",
          share: "82",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 잔차 축 1 원점 눈금 0.00"],
    ["zh", "残差地图比较残差轴 1 原点刻度 0.00"],
    ["ja", "残差マップの比較残差軸 1 原点目盛 0.00"],
    ["vi", "vạch gốc trục phần dư so sánh bản đồ phần dư 1 0.00"],
  ] as const)(
    "formats leftover map comparison leftover-axis origin ticks in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("leftover map comparison leftover axis {axis} origin tick {value}", {
          axis: 1,
          value: "0.00",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 잔차 축 1 원점 눈금 0.00 σ 0.00 0%"],
    ["zh", "残差地图比较残差轴 1 原点刻度 0.00 σ 0.00 0%"],
    ["ja", "残差マップの比較残差軸 1 原点目盛 0.00 σ 0.00 0%"],
    ["vi", "vạch gốc trục phần dư so sánh bản đồ phần dư 1 0.00 σ 0.00 0%"],
  ] as const)(
    "formats leftover map comparison leftover-axis origin ticks leftover-map singular values and leftover-map axis share in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf(
          "leftover map comparison leftover axis {axis} origin tick {value} σ {singular} {share}%",
          {
            axis: 1,
            value: "0.00",
            singular: "0.00",
            share: "0",
          },
        ),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 잔차 축 1 σ 1.84 82%"],
    ["zh", "残差地图比较残差轴 1 σ 1.84 82%"],
    ["ja", "残差マップの比較残差軸 1 σ 1.84 82%"],
    ["vi", "trục phần dư so sánh bản đồ phần dư 1 σ 1.84 82%"],
  ] as const)(
    "formats leftover map comparison leftover-axis singular share in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("leftover map comparison leftover axis {axis} σ {value} {share}%", {
          axis: 1,
          value: "1.84",
          share: "82",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 설명 잔여 점유율"],
    ["zh", "残差地图比较已解释残差份额"],
    ["ja", "残差マップの比較説明済み残差割合"],
    ["vi", "Phần dư giải thích so sánh bản đồ phần dư"],
  ] as const)(
    "formats leftover map comparison explained leftover share label in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(t("Leftover map comparison explained leftover share")).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 미설명 잔여 점유율"],
    ["zh", "残差地图比较未解释残差份额"],
    ["ja", "残差マップの比較未説明残差割合"],
    ["vi", "Phần dư chưa giải thích so sánh bản đồ phần dư"],
  ] as const)(
    "formats leftover map comparison unexplained leftover share label in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(t("Leftover map comparison unexplained leftover share")).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 교차 점유율"],
    ["zh", "残差地图比较交叉份额"],
    ["ja", "残差マップの比較交差割合"],
    ["vi", "Phần giao so sánh bản đồ phần dư"],
  ] as const)(
    "formats leftover map comparison cross share label in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(t("Leftover map comparison cross share")).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 미설명 잔여"],
    ["zh", "残差地图比较未解释残差"],
    ["ja", "残差マップの比較未説明残差"],
    ["vi", "Phần dư chưa giải thích so sánh"],
  ] as const)(
    "formats leftover map comparison unexplained leftover label in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(t("Leftover map comparison unexplained leftover")).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 잔여"],
    ["zh", "残差地图比较残差"],
    ["ja", "残差マップの比較残差"],
    ["vi", "Phần dư so sánh bản đồ phần dư"],
  ] as const)(
    "formats leftover map comparison residual label in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(t("Leftover map comparison residual")).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 관측"],
    ["zh", "残差地图比较观测"],
    ["ja", "残差マップの比較観測"],
    ["vi", "Quan sát so sánh bản đồ phần dư"],
  ] as const)(
    "formats leftover map comparison observed label in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(t("Leftover map comparison observed")).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 기대"],
    ["zh", "残差地图比较期望"],
    ["ja", "残差マップの比較期待"],
    ["vi", "Kỳ vọng so sánh bản đồ phần dư"],
  ] as const)(
    "formats leftover map comparison expected label in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(t("Leftover map comparison expected")).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 순위"],
    ["zh", "残差地图比较秩"],
    ["ja", "残差マップの比較階数"],
    ["vi", "Hạng so sánh bản đồ phần dư"],
  ] as const)(
    "formats leftover map comparison rank label in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(t("Leftover map comparison rank")).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 좌표"],
    ["zh", "残差地图比较坐标"],
    ["ja", "残差マップの比較座標"],
    ["vi", "Tọa độ so sánh bản đồ phần dư"],
  ] as const)(
    "formats leftover map comparison coordinates label in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(t("Leftover map comparison coordinates")).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 그림"],
    ["zh", "残差地图比较图形"],
    ["ja", "残差マップの比較図"],
    ["vi", "Đồ họa so sánh bản đồ phần dư"],
  ] as const)(
    "formats leftover map comparison graphic label in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(t("Leftover map comparison graphic")).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 비교 축 1 (82%)"],
    ["zh", "残差地图比较轴 1 (82%)"],
    ["ja", "残差マップの比較軸 1 (82%)"],
    ["vi", "trục so sánh bản đồ phần dư 1 (82%)"],
  ] as const)(
    "formats leftover map comparison axis share label in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(tf("leftover map comparison axis {axis} ({share}%)", { axis: 1, share: "82" })).toBe(
        expected,
      );
    },
  );

  it.each([
    ["ko", "잔여 지도 그림 기준 포함 범위"],
    ["zh", "残差图图形准则覆盖范围"],
    ["ja", "残差マップ図の基準対象範囲"],
    ["vi", "Phạm vi đồ họa tiêu chí bản đồ phần dư"],
  ] as const)("formats leftover-map graphic item coverage label in %s", (locale, expected) => {
    setLocale(locale);
    expect(t("Leftover-map graphic item coverage")).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 기준 포함 범위"],
    ["zh", "残差地图准则覆盖范围"],
    ["ja", "残差マップの基準対象範囲"],
    ["vi", "Phạm vi tiêu chí bản đồ phần dư"],
  ] as const)("formats leftover map item coverage label in %s", (locale, expected) => {
    setLocale(locale);
    expect(t("Leftover map item coverage")).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 불완전 글"],
    ["zh", "残差地图不完整帖文"],
    ["ja", "残差マップの不完全投稿"],
    ["vi", "Bài không đầy đủ trên bản đồ phần dư"],
  ] as const)("formats leftover map incomplete posts label in %s", (locale, expected) => {
    setLocale(locale);
    expect(t("Leftover map incomplete posts")).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 불완전 기준"],
    ["zh", "残差地图不完整准则"],
    ["ja", "残差マップの不完全基準"],
    ["vi", "Tiêu chí không đầy đủ trên bản đồ phần dư"],
  ] as const)("formats leftover map incomplete items label in %s", (locale, expected) => {
    setLocale(locale);
    expect(t("Leftover map incomplete items")).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 그림 불완전 글"],
    ["zh", "残差图图形不完整帖文"],
    ["ja", "残差マップ図の不完全投稿"],
    ["vi", "Bài không đầy đủ trên đồ họa bản đồ phần dư"],
  ] as const)("formats leftover-map graphic incomplete posts label in %s", (locale, expected) => {
    setLocale(locale);
    expect(t("Leftover-map graphic incomplete posts")).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 그림 불완전 기준"],
    ["zh", "残差图图形不完整准则"],
    ["ja", "残差マップ図の不完全基準"],
    ["vi", "Tiêu chí không đầy đủ trên đồ họa bản đồ phần dư"],
  ] as const)("formats leftover-map graphic incomplete items label in %s", (locale, expected) => {
    setLocale(locale);
    expect(t("Leftover-map graphic incomplete items")).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 축 1 눈금 +0.50"],
    ["zh", "残差图轴 1 刻度 +0.50"],
    ["ja", "残差マップ軸 1 目盛 +0.50"],
    ["vi", "vạch trục bản đồ phần dư 1 +0.50"],
  ] as const)("formats leftover-map coordinate ticks in %s", (locale, expected) => {
    setLocale(locale);
    expect(tf("leftover-map axis {axis} tick {value}", { axis: 1, value: "+0.50" })).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 축 1 눈금 +0.50 σ 1.84"],
    ["zh", "残差图轴 1 刻度 +0.50 σ 1.84"],
    ["ja", "残差マップ軸 1 目盛 +0.50 σ 1.84"],
    ["vi", "vạch trục bản đồ phần dư 1 +0.50 σ 1.84"],
  ] as const)("formats leftover-map graphic leftover-map axis tick singular values in %s", (locale, expected) => {
    setLocale(locale);
    expect(
      tf("leftover-map axis {axis} tick {value} σ {singular}", {
        axis: 1,
        value: "+0.50",
        singular: "1.84",
      }),
    ).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 축 1 눈금 +0.50 82%"],
    ["zh", "残差图轴 1 刻度 +0.50 82%"],
    ["ja", "残差マップ軸 1 目盛 +0.50 82%"],
    ["vi", "vạch trục bản đồ phần dư 1 +0.50 82%"],
  ] as const)("formats leftover-map graphic leftover-map axis tick leftover-map axis share in %s", (locale, expected) => {
    setLocale(locale);
    expect(
      tf("leftover-map axis {axis} tick {value} {share}%", {
        axis: 1,
        value: "+0.50",
        share: "82",
      }),
    ).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 축 1 눈금 +0.50 σ 1.84 82%"],
    ["zh", "残差图轴 1 刻度 +0.50 σ 1.84 82%"],
    ["ja", "残差マップ軸 1 目盛 +0.50 σ 1.84 82%"],
    ["vi", "vạch trục bản đồ phần dư 1 +0.50 σ 1.84 82%"],
  ] as const)(
    "formats leftover-map graphic leftover-map axis tick leftover-map singular values and leftover-map axis share in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("leftover-map axis {axis} tick {value} σ {singular} {share}%", {
          axis: 1,
          value: "+0.50",
          singular: "1.84",
          share: "82",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 축 1 원점 눈금 0.00"],
    ["zh", "残差图轴 1 原点刻度 0.00"],
    ["ja", "残差マップ軸 1 原点目盛 0.00"],
    ["vi", "vạch gốc trục bản đồ phần dư 1 0.00"],
  ] as const)("formats leftover-map graphic leftover-map axis origin ticks in %s", (locale, expected) => {
    setLocale(locale);
    expect(tf("leftover-map axis {axis} origin tick {value}", { axis: 1, value: "0.00" })).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 원점 (0.00, 0.00)"],
    ["zh", "残差图原点 (0.00, 0.00)"],
    ["ja", "残差マップ原点 (0.00, 0.00)"],
    ["vi", "gốc bản đồ phần dư (0.00, 0.00)"],
  ] as const)("formats leftover-map graphic leftover-map origin in %s", (locale, expected) => {
    setLocale(locale);
    expect(tf("leftover-map origin {origin}", { origin: "(0.00, 0.00)" })).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 축 1 원점 눈금 0.00 σ 0.00 0%"],
    ["zh", "残差图轴 1 原点刻度 0.00 σ 0.00 0%"],
    ["ja", "残差マップ軸 1 原点目盛 0.00 σ 0.00 0%"],
    ["vi", "vạch gốc trục bản đồ phần dư 1 0.00 σ 0.00 0%"],
  ] as const)(
    "formats leftover-map graphic leftover-map axis origin ticks leftover-map singular values and leftover-map axis share in %s",
    (locale, expected) => {
      setLocale(locale);
      expect(
        tf("leftover-map axis {axis} origin tick {value} σ {singular} {share}%", {
          axis: 1,
          value: "0.00",
          singular: "0.00",
          share: "0",
        }),
      ).toBe(expected);
    },
  );

  it.each([
    ["ko", "잔여 지도 거리 d 0.12"],
    ["zh", "残差图距离 d 0.12"],
    ["ja", "残差マップ距離 d 0.12"],
    ["vi", "khoảng cách bản đồ phần dư d 0.12"],
  ] as const)("formats leftover-map segment distance in %s", (locale, expected) => {
    setLocale(locale);
    expect(tf("leftover-map distance {label}", { label: "d 0.12" })).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 재구성 R̂ +0.35"],
    ["zh", "残差图重建 R̂ +0.35"],
    ["ja", "残差マップ再構成 R̂ +0.35"],
    ["vi", "tái dựng bản đồ phần dư R̂ +0.35"],
  ] as const)("formats leftover-map segment reconstruction in %s", (locale, expected) => {
    setLocale(locale);
    expect(tf("leftover-map reconstruction {label}", { label: "R̂ +0.35" })).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 설명 잔여 점유율 R̂²/R² 0.76"],
    ["zh", "残差图已解释残差份额 R̂²/R² 0.76"],
    ["ja", "残差マップ説明済み残差割合 R̂²/R² 0.76"],
    ["vi", "phần dư giải thích bản đồ phần dư R̂²/R² 0.76"],
  ] as const)("formats leftover-map segment explained leftover share in %s", (locale, expected) => {
    setLocale(locale);
    expect(tf("leftover-map explained leftover share {label}", { label: "R̂²/R² 0.76" })).toBe(
      expected,
    );
  });

  it.each([
    ["ko", "잔여 지도 미설명 잔여 점유율 U²/R² 0.02"],
    ["zh", "残差图未解释残差份额 U²/R² 0.02"],
    ["ja", "残差マップ未説明残差割合 U²/R² 0.02"],
    ["vi", "phần dư chưa giải thích bản đồ phần dư U²/R² 0.02"],
  ] as const)("formats leftover-map segment unexplained leftover share in %s", (locale, expected) => {
    setLocale(locale);
    expect(tf("leftover-map unexplained leftover share {label}", { label: "U²/R² 0.02" })).toBe(
      expected,
    );
  });

  it.each([
    ["ko", "잔여 지도 교차 점유율 2R̂U/R² 0.12"],
    ["zh", "残差图交叉份额 2R̂U/R² 0.12"],
    ["ja", "残差マップ交差割合 2R̂U/R² 0.12"],
    ["vi", "phần giao bản đồ phần dư 2R̂U/R² 0.12"],
  ] as const)("formats leftover-map segment cross share in %s", (locale, expected) => {
    setLocale(locale);
    expect(tf("leftover-map cross share {label}", { label: "2R̂U/R² 0.12" })).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 미설명 잔여 U +0.05"],
    ["zh", "残差图未解释残差 U +0.05"],
    ["ja", "残差マップ未説明残差 U +0.05"],
    ["vi", "phần dư chưa giải thích U +0.05"],
  ] as const)("formats leftover-map segment unexplained leftover in %s", (locale, expected) => {
    setLocale(locale);
    expect(tf("leftover-map unexplained leftover {label}", { label: "U +0.05" })).toBe(expected);
  });

  it.each([
    ["ko", "잔여 R +0.40"],
    ["zh", "残差 R +0.40"],
    ["ja", "残差 R +0.40"],
    ["vi", "phần dư R +0.40"],
  ] as const)("formats leftover-map segment leftover residual in %s", (locale, expected) => {
    setLocale(locale);
    expect(tf("leftover residual {label}", { label: "R +0.40" })).toBe(expected);
  });

  it.each([
    ["ko", "관측 Y 2.40"],
    ["zh", "观测 Y 2.40"],
    ["ja", "観測 Y 2.40"],
    ["vi", "quan sát Y 2.40"],
  ] as const)("formats leftover-map segment leftover observed in %s", (locale, expected) => {
    setLocale(locale);
    expect(tf("leftover observed {label}", { label: "Y 2.40" })).toBe(expected);
  });

  it.each([
    ["ko", "기대 E 2.00"],
    ["zh", "期望 E 2.00"],
    ["ja", "期待 E 2.00"],
    ["vi", "kỳ vọng E 2.00"],
  ] as const)("formats leftover-map segment leftover expected in %s", (locale, expected) => {
    setLocale(locale);
    expect(tf("leftover expected {label}", { label: "E 2.00" })).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 순위 rank 1"],
    ["zh", "残差图秩 rank 1"],
    ["ja", "残差マップ階数 rank 1"],
    ["vi", "hạng bản đồ phần dư rank 1"],
  ] as const)("formats leftover-map segment leftover-map rank in %s", (locale, expected) => {
    setLocale(locale);
    expect(tf("leftover-map rank {label}", { label: "rank 1" })).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 축 1 (82%)"],
    ["zh", "残差图轴 1 (82%)"],
    ["ja", "残差マップ軸 1 (82%)"],
    ["vi", "trục bản đồ phần dư 1 (82%)"],
  ] as const)("formats leftover-map plot axis share in %s", (locale, expected) => {
    setLocale(locale);
    expect(tf("leftover-map axis {axis} ({share}%)", { axis: 1, share: "82" })).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 축 1 σ 1.84"],
    ["zh", "残差图轴 1 σ 1.84"],
    ["ja", "残差マップ軸 1 σ 1.84"],
    ["vi", "trục bản đồ phần dư 1 σ 1.84"],
  ] as const)("formats leftover-map plot axis singular values in %s", (locale, expected) => {
    setLocale(locale);
    expect(tf("leftover-map axis {axis} σ {value}", { axis: 1, value: "1.84" })).toBe(expected);
  });

  it.each([
    ["ko", "잔여 지도 축 1 σ 1.84 (82%)"],
    ["zh", "残差图轴 1 σ 1.84 (82%)"],
    ["ja", "残差マップ軸 1 σ 1.84 (82%)"],
    ["vi", "trục bản đồ phần dư 1 σ 1.84 (82%)"],
  ] as const)("formats leftover-map plot axis singular share in %s", (locale, expected) => {
    setLocale(locale);
    expect(
      tf("leftover-map axis {axis} σ {value} ({share}%)", { axis: 1, value: "1.84", share: "82" }),
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
  const allVoiceLabels = [
    "Voice of Customer",
    "Voice of Customer's Customer",
    "Voice of Competitor",
    "Voice of Market",
    "Voice of Partner",
    "Voice of Supplier",
    "Voice of Employee",
    "Voice of Business",
    "Voice of Regulator",
    "Voice of Investor",
    "Voice of Society",
    "Voice of Process",
  ] as const;

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

  it.each(["ko", "zh", "ja", "vi"] as const)(
    "translates every governed atomic Voice label in %s",
    (locale) => {
      setLocale(locale);
      for (const label of allVoiceLabels) expect(t(label)).not.toBe(label);
    },
  );
});
