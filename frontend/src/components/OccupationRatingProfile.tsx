import { useEffect, useState } from "react";
import {
  fetchOccupationRatingOccupations,
  fetchOccupationRatingSources,
  fetchOccupationRatings,
  type OccupationRatingOccupation,
  type OccupationRatingProfile as OccupationRatingProfilePayload,
  type OccupationRatingSource,
} from "../api";

type Props = { accessToken: string };

function sourceKey(source: Pick<OccupationRatingSource, "data_release_code" | "source_table_code">): string {
  return `${source.data_release_code}|${source.source_table_code}`;
}

function safeHttpUrl(value: string | null | undefined): string | null {
  if (!value) return null;
  try {
    const parsed = new URL(value);
    return parsed.protocol === "http:" || parsed.protocol === "https:" ? parsed.toString() : null;
  } catch {
    return null;
  }
}

/** Lets an authenticated user inspect one exact imported occupation profile. */
export function OccupationRatingProfile({ accessToken }: Props) {
  const [sources, setSources] = useState<OccupationRatingSource[] | null>(null);
  const [selectedSource, setSelectedSource] = useState("");
  const [sourceCatalogError, setSourceCatalogError] = useState(false);
  const [occupations, setOccupations] = useState<OccupationRatingOccupation[] | null>(null);
  const [selectedOccupation, setSelectedOccupation] = useState("");
  const [occupationCatalogError, setOccupationCatalogError] = useState(false);
  const [profile, setProfile] = useState<OccupationRatingProfilePayload | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");

  useEffect(() => {
    let active = true;
    fetchOccupationRatingSources(accessToken)
      .then(({ sources: loaded }) => {
        if (!active) return;
        setSources(loaded);
        setSelectedSource(loaded[0] ? sourceKey(loaded[0]) : "");
      })
      .catch(() => active && setSourceCatalogError(true));
    return () => { active = false; };
  }, [accessToken]);

  useEffect(() => {
    const source = sources?.find((item) => sourceKey(item) === selectedSource);
    if (!source) {
      setOccupations(null);
      setSelectedOccupation("");
      setOccupationCatalogError(false);
      return;
    }
    let active = true;
    setOccupations(null);
    setSelectedOccupation("");
    setOccupationCatalogError(false);
    fetchOccupationRatingOccupations(accessToken, {
      dataReleaseCode: source.data_release_code,
      sourceTableCode: source.source_table_code,
    })
      .then((payload) => {
        if (!active) return;
        const loaded = payload.source_available ? payload.occupations : [];
        setOccupations(loaded);
        setSelectedOccupation(loaded[0]?.onetsoc_code ?? "");
      })
      .catch(() => active && setOccupationCatalogError(true));
    return () => { active = false; };
  }, [accessToken, sources, selectedSource]);

  function load(offset: number | null = null) {
    const source = sources?.find((item) => sourceKey(item) === selectedSource);
    const request = offset == null && source && selectedOccupation
      ? {
          onetsocCode: selectedOccupation,
          dataReleaseCode: source.data_release_code,
          sourceTableCode: source.source_table_code,
        }
      : profile
        ? {
            onetsocCode: profile.onetsoc_code,
            dataReleaseCode: profile.data_release_code,
            sourceTableCode: profile.source_table_code,
          }
        : null;
    if (!request) return;
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

  const occupationCatalogReady = occupations !== null && !occupationCatalogError;
  const canSubmit = Boolean(selectedSource) && Boolean(selectedOccupation) && occupationCatalogReady && occupations.length > 0;

  return (
    <section className="occupation-rating-profile" aria-labelledby="occupation-rating-heading">
      <header>
        <p className="dashboard-eyebrow">공개 직업 근거</p>
        <h2 id="occupation-rating-heading">직업별 업무 특성 확인</h2>
        <p>직업과 근거 표를 선택해 관측값, 오차, 사용 주의사항을 함께 확인하세요.</p>
      </header>
      <form
        className="occupation-rating-form"
        onSubmit={(event) => {
          event.preventDefault();
          load();
        }}
      >
        <label className="occupation-rating-source-select">
          근거 릴리스·표
          <select
            required
            value={selectedSource}
            onChange={(event) => {
              setSelectedSource(event.target.value);
              setProfile(null);
            }}
          >
            {(sources ?? []).map((source) => (
              <option key={sourceKey(source)} value={sourceKey(source)}>
                {source.release_version} · {source.source_table_name}
              </option>
            ))}
          </select>
        </label>
        <label className="occupation-rating-occupation-select">
          직업
          <select
            required
            value={selectedOccupation}
            disabled={!occupationCatalogReady || occupations.length === 0}
            onChange={(event) => setSelectedOccupation(event.target.value)}
          >
            {(occupations ?? []).map((occupation) => (
              <option key={occupation.onetsoc_code} value={occupation.onetsoc_code}>
                {occupation.occupation_title} ({occupation.onetsoc_code})
              </option>
            ))}
          </select>
        </label>
        <button className="btn-secondary" type="submit" disabled={status === "loading" || !canSubmit}>
          {status === "loading" ? "근거를 불러오는 중" : "직업 근거 열기"}
        </button>
      </form>
      {sources === null && !sourceCatalogError ? <p role="status">사용 가능한 근거 표를 확인하는 중입니다.</p> : null}
      {sources?.length === 0 ? <p role="status">가져온 직업 근거 표가 없습니다. 데이터 담당자에게 근거 가져오기를 요청하세요.</p> : null}
      {sourceCatalogError ? <p role="alert">사용 가능한 근거 표를 확인하지 못했습니다. 잠시 후 다시 열어 보세요.</p> : null}
      {selectedSource && occupations === null && !occupationCatalogError ? (
        <p role="status">사용 가능한 직업을 확인하는 중입니다.</p>
      ) : null}
      {occupations?.length === 0 && !occupationCatalogError ? (
        <p role="status">이 근거 표에서 확인할 수 있는 직업이 없습니다. 다른 근거 표를 선택하거나 데이터 담당자에게 가져오기를 요청하세요.</p>
      ) : null}
      {occupationCatalogError ? <p role="alert">사용 가능한 직업을 확인하지 못했습니다. 잠시 후 다시 열어 보세요.</p> : null}
      {status === "error" ? (
        <p role="alert">직업 근거를 불러오지 못했습니다. 선택한 직업과 접근 권한을 확인한 뒤 다시 시도하세요.</p>
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
        이 근거 표에는 선택한 직업의 관측값이 없습니다. 직업이나 근거 표를 바꿔 확인하세요.
      </p>
    );
  }
  const sourceArtifactUrl = safeHttpUrl(profile.source?.source_artifact_url);
  const scaleArtifactUrl = safeHttpUrl(profile.source?.scale_artifact_url);
  return (
    <>
      <div className="occupation-rating-source">
        <strong>{profile.occupation_title ?? profile.onetsoc_code}</strong>
        <span>{profile.data_release_code} · {profile.onetsoc_code}</span>
        <span>{profile.source?.source_table_name}</span>
        {sourceArtifactUrl ? (
          <a href={sourceArtifactUrl} target="_blank" rel="noreferrer">평정 원문 열기</a>
        ) : (
          <span>원문 링크를 사용할 수 없습니다. 데이터 담당자에게 출처 확인을 요청하세요.</span>
        )}
        {scaleArtifactUrl ? (
          <a href={scaleArtifactUrl} target="_blank" rel="noreferrer">척도 정의 열기</a>
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
