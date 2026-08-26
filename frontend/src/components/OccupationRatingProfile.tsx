import { useState } from "react";
import {
  fetchOccupationRatings,
  type OccupationRatingProfile as OccupationRatingProfilePayload,
} from "../api";

type Props = { accessToken: string };

/** Lets an authenticated user inspect one exact imported occupation profile. */
export function OccupationRatingProfile({ accessToken }: Props) {
  const [onetsocCode, setOnetsocCode] = useState("");
  const [releaseCode, setReleaseCode] = useState("onet-31.0");
  const [sourceCode, setSourceCode] = useState("abilities");
  const [profile, setProfile] = useState<OccupationRatingProfilePayload | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");

  function load(offset: number | null = null) {
    const request = offset == null
      ? { onetsocCode, dataReleaseCode: releaseCode, sourceTableCode: sourceCode }
      : {
          onetsocCode: profile?.onetsoc_code ?? onetsocCode,
          dataReleaseCode: profile?.data_release_code ?? releaseCode,
          sourceTableCode: profile?.source_table_code ?? sourceCode,
        };
    if (offset == null) setProfile(null);
    setStatus("loading");
    fetchOccupationRatings(accessToken, {
      ...request,
      offset: offset ?? 0,
    })
      .then((payload) => {
        setProfile((current) =>
          offset != null && current
            ? { ...payload, items: [...current.items, ...payload.items] }
            : payload,
        );
        setStatus("idle");
      })
      .catch(() => setStatus("error"));
  }

  return (
    <section className="occupation-rating-profile" aria-labelledby="occupation-rating-heading">
      <header>
        <p className="dashboard-eyebrow">공개 직업 근거</p>
        <h2 id="occupation-rating-heading">직업별 업무 특성 확인</h2>
        <p>직업 코드와 근거 표를 선택해 관측값, 오차, 사용 주의사항을 함께 확인하세요.</p>
      </header>
      <form
        className="occupation-rating-form"
        onSubmit={(event) => {
          event.preventDefault();
          load();
        }}
      >
        <label>
          O*NET-SOC 직업 코드
          <input
            required
            pattern="[0-9]{2}-[0-9]{4}\.[0-9]{2}"
            placeholder="15-1252.00"
            value={onetsocCode}
            onChange={(event) => setOnetsocCode(event.target.value)}
          />
        </label>
        <label>
          데이터 릴리스
          <input required value={releaseCode} onChange={(event) => setReleaseCode(event.target.value)} />
        </label>
        <label>
          근거 표
          <input required value={sourceCode} onChange={(event) => setSourceCode(event.target.value)} />
        </label>
        <button className="btn-secondary" type="submit" disabled={status === "loading"}>
          {status === "loading" ? "근거를 불러오는 중" : "직업 근거 열기"}
        </button>
      </form>
      {status === "error" ? (
        <p role="alert">직업 근거를 불러오지 못했습니다. 코드와 접근 권한을 확인한 뒤 다시 시도하세요.</p>
      ) : null}
      {profile ? <OccupationRatingProfileView profile={profile} /> : null}
      {profile?.next_offset != null ? (
        <button
          className="btn-secondary"
          type="button"
          disabled={status === "loading"}
          onClick={() => load(profile.next_offset)}
        >
          다음 관측값 불러오기
        </button>
      ) : null}
    </section>
  );
}

/** Renders an exact occupation profile for runtime and Storybook scenes. */
export function OccupationRatingProfileView({
  profile,
}: {
  profile: OccupationRatingProfilePayload;
}) {
  if (!profile.source_available) {
    return (
      <p role="status">
        선택한 릴리스와 근거 표가 아직 준비되지 않았습니다. 다른 근거 표를 선택하거나 데이터 담당자에게 가져오기를 요청하세요.
      </p>
    );
  }
  if (profile.items.length === 0) {
    return (
      <p role="status">
        이 근거 표에는 선택한 직업의 관측값이 없습니다. 직업 코드나 근거 표를 바꿔 확인하세요.
      </p>
    );
  }
  return (
    <>
      <div className="occupation-rating-source">
        <strong>{profile.source?.source_table_name}</strong>
        <span>{profile.data_release_code} · {profile.onetsoc_code}</span>
        <a href={profile.source?.source_artifact_url} target="_blank" rel="noreferrer">평정 원문 열기</a>
        {profile.source?.scale_artifact_url ? (
          <a href={profile.source.scale_artifact_url} target="_blank" rel="noreferrer">척도 정의 열기</a>
        ) : null}
      </div>
      <p className="occupation-rating-scroll-hint">표를 가로로 밀어 오차와 사용 주의를 확인하세요.</p>
      <div className="occupation-rating-table" role="region" tabIndex={0} aria-label="직업 업무 특성 관측값">
        <table>
          <caption>값과 오차 및 사용 주의사항</caption>
          <thead>
            <tr>
              <th>업무 특성</th><th>척도</th><th>값</th><th>표본·오차</th><th>출처 시점</th><th>사용 주의</th>
            </tr>
          </thead>
          <tbody>
            {profile.items.map((item) => (
              <tr key={`${item.element_id}-${item.scale_id}-${item.category_value ?? "none"}`}>
                <td>{item.element_name}<small>{item.element_id}</small></td>
                <td>{item.scale_name} ({item.minimum_value}–{item.maximum_value})</td>
                <td>{item.data_value}{item.category_value == null ? null : ` · 범주 ${item.category_value}`}</td>
                <td>
                  {item.sample_size == null ? "표본 수 없음" : `N ${item.sample_size}`}
                  {item.standard_error == null ? null : ` · SE ${item.standard_error}`}
                  {item.lower_ci_bound == null || item.upper_ci_bound == null ? null : ` · CI ${item.lower_ci_bound}–${item.upper_ci_bound}`}
                </td>
                <td>{item.source_updated_month ?? "시점 없음"}{item.domain_source_code ? ` · ${item.domain_source_code}` : ""}</td>
                <td>
                  {[
                    item.recommend_suppress ? "정밀도가 낮아 해석 전 원문을 확인하세요." : null,
                    item.not_relevant ? "해당 없음 응답이 포함됩니다." : null,
                  ].filter(Boolean).join(" ") || "공개 근거와 함께 해석하세요."}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
