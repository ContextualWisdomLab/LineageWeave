import { useEffect, useId, useState } from "react";

import { fetchProjectHistory, type ProjectHistoryLink } from "../api";
import type { Locale } from "../i18n";
import { useLocale } from "../i18n";
import { projectHistoryText, type ProjectHistoryProjection } from "../projectHistory";
import { ProjectHistoryTimeline } from "./ProjectHistoryTimeline";
import "./AskProjectHistoryLinks.css";

interface Copy {
  heading: string;
  boundary: string;
  open: (name: string) => string;
  close: (name: string) => string;
  loading: string;
  truncated: string;
  observed: string;
  inferred: string;
}

const COPY: Record<Locale, Copy> = {
  en: {
    heading: "Project histories cited by this answer",
    boundary: "Each timeline is rebuilt from currently authorized evidence at the answer cutoff.",
    open: (name) => `Open project history: ${name}`,
    close: (name) => `Close project history: ${name}`,
    loading: "Loading cited project history...",
    truncated: "Additional cited projects are not shown. Open the cited source records to inspect their project evidence.",
    observed: "Observed project identity",
    inferred: "Inferred project identity",
  },
  ko: {
    heading: "이 답변이 인용한 프로젝트 이력",
    boundary: "각 타임라인은 답변 기준 시각과 현재 권한을 통과한 근거로 다시 구성됩니다.",
    open: (name) => `프로젝트 이력 열기: ${name}`,
    close: (name) => `프로젝트 이력 닫기: ${name}`,
    loading: "인용된 프로젝트 이력을 불러오는 중...",
    truncated: "일부 추가 프로젝트는 표시하지 않습니다. 인용된 원천 기록에서 프로젝트 근거를 확인하세요.",
    observed: "관찰된 프로젝트 식별자",
    inferred: "추론된 프로젝트 식별자",
  },
  zh: {
    heading: "此回答引用的项目历史",
    boundary: "每条时间线都根据回答截止时间和当前授权证据重新构建。",
    open: (name) => `打开项目历史：${name}`,
    close: (name) => `关闭项目历史：${name}`,
    loading: "正在加载引用的项目历史...",
    truncated: "还有引用项目未显示。请打开引用的源记录检查其项目依据。",
    observed: "已观察的项目身份",
    inferred: "已推断的项目身份",
  },
  ja: {
    heading: "この回答が引用したプロジェクト履歴",
    boundary: "各タイムラインは回答時点と現在の権限を通過した根拠から再構成されます。",
    open: (name) => `プロジェクト履歴を開く: ${name}`,
    close: (name) => `プロジェクト履歴を閉じる: ${name}`,
    loading: "引用されたプロジェクト履歴を読み込み中...",
    truncated: "追加の引用プロジェクトは表示されていません。引用元レコードでプロジェクト根拠を確認してください。",
    observed: "観察されたプロジェクト識別子",
    inferred: "推論されたプロジェクト識別子",
  },
  vi: {
    heading: "Lịch sử dự án được câu trả lời này trích dẫn",
    boundary: "Mỗi dòng thời gian được dựng lại từ bằng chứng hiện được cấp quyền tại thời điểm cắt của câu trả lời.",
    open: (name) => `Mở lịch sử dự án: ${name}`,
    close: (name) => `Đóng lịch sử dự án: ${name}`,
    loading: "Đang tải lịch sử dự án được trích dẫn...",
    truncated: "Một số dự án được trích dẫn chưa được hiển thị. Hãy mở bản ghi nguồn để kiểm tra bằng chứng dự án.",
    observed: "Danh tính dự án được quan sát",
    inferred: "Danh tính dự án được suy luận",
  },
};

function ProjectHistoryDisclosure({
  accessToken,
  link,
  onOpenPost,
}: {
  accessToken: string;
  link: ProjectHistoryLink;
  onOpenPost: (postId: string) => void;
}) {
  const locale = useLocale();
  const copy = COPY[locale];
  const regionId = useId();
  const [opened, setOpened] = useState(false);
  const [loading, setLoading] = useState(false);
  const [projection, setProjection] = useState<ProjectHistoryProjection | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    setOpened(false);
    setLoading(false);
    setProjection(null);
    setError(false);
  }, [link.project_key, link.focus_post_id, link.knowledge_cutoff]);

  function toggle() {
    if (opened) {
      setOpened(false);
      return;
    }
    setOpened(true);
    if (projection || loading) return;
    setLoading(true);
    setError(false);
    fetchProjectHistory(
      accessToken,
      link.project_key,
      link.knowledge_cutoff,
      link.focus_post_id,
    )
      .then((result) => {
        setProjection(result);
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });
  }

  return (
    <article className="ask-project-history-link">
      <div>
        <strong>{link.project_name}</strong>
        <span className="post-badge">
          {link.truth_status_code === "observed" ? copy.observed : copy.inferred}
        </span>
      </div>
      <button type="button" aria-expanded={opened} aria-controls={regionId} onClick={toggle}>
        {opened ? copy.close(link.project_name) : copy.open(link.project_name)}
      </button>
      <div id={regionId} hidden={!opened}>
        {loading ? <p role="status">{copy.loading}</p> : null}
        {error ? (
          <p role="alert">{projectHistoryText(locale, "historyUnavailable")}</p>
        ) : null}
        {!error && projection ? (
          <ProjectHistoryTimeline projection={projection} onOpenPost={onOpenPost} />
        ) : null}
      </div>
    </article>
  );
}

export function AskProjectHistoryLinks({
  accessToken,
  links,
  truncated,
  onOpenPost,
}: {
  accessToken: string;
  links: ProjectHistoryLink[];
  truncated: boolean;
  onOpenPost: (postId: string) => void;
}) {
  const locale = useLocale();
  const copy = COPY[locale];
  const headingId = useId();
  if (links.length === 0 && !truncated) return null;
  return (
    <section className="ask-project-history-links" aria-labelledby={headingId}>
      <h4 id={headingId}>{copy.heading}</h4>
      <p className="project-history-boundary">{copy.boundary}</p>
      {links.map((link) => (
        <ProjectHistoryDisclosure
          key={`${link.project_key}:${link.focus_post_id}:${link.knowledge_cutoff}`}
          accessToken={accessToken}
          link={link}
          onOpenPost={onOpenPost}
        />
      ))}
      {truncated ? <p role="status">{copy.truncated}</p> : null}
    </section>
  );
}
