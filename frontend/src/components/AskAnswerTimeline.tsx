import { useRef, useState } from "react";
import type { AskAgentResponse, CitedPostEvent } from "../api";
import { chatEvidenceKindLabel } from "../evidenceKindLabels";
import { getLocale, t, tf } from "../i18n";

type Props = {
  question: string;
  answer: AskAgentResponse;
  onOpenEvidence: (postId: string) => void;
  onOpenPost: (postId: string) => void;
};

type Citation = {
  citationNumber: number;
  postId: string;
  postTitle: string;
  event: CitedPostEvent | undefined;
};

function observedTimeLabel(event: CitedPostEvent | undefined): string {
  if (!event?.observed_at) return t("Observed time unavailable");
  const date = new Date(event.observed_at);
  if (Number.isNaN(date.valueOf())) return t("Observed time unavailable");
  const formatted = new Intl.DateTimeFormat(getLocale(), {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
  const axis = event.time_axis_code === "event_occurred_at"
    ? t("Event occurred")
    : event.time_axis_code === "created_at"
      ? t("Record created")
      : t("Observed time");
  return `${formatted} · ${axis}`;
}

function observedEpoch(event: CitedPostEvent | undefined): number | null {
  if (!event?.observed_at) return null;
  const epoch = Date.parse(event.observed_at);
  return Number.isNaN(epoch) ? null : epoch;
}

function isPublicDocumentUrl(url: string): boolean {
  return /^https?:\/\//i.test(url);
}

/** Links one grounded Ask answer to its authorized source-event cards. */
export function AskAnswerTimeline({ question, answer, onOpenEvidence, onOpenPost }: Props) {
  const [selectedPostId, setSelectedPostId] = useState<string | null>(null);
  const citationRefs = useRef(new Map<string, HTMLButtonElement>());
  const cardRefs = useRef(new Map<string, HTMLButtonElement>());
  const eventsByPost = new Map(answer.cited_events?.map((event) => [event.post_id, event]));
  const postDetails = new Map((answer.cited_posts ?? []).map((post) => [post.post_id, post]));
  const citationIds = [...new Set([
    ...(answer.cited_post_ids ?? []),
    ...(answer.cited_posts ?? []).map((post) => post.post_id),
  ])];
  const citations: Citation[] = citationIds.map((postId, index) => ({
    citationNumber: index + 1,
    postId,
    postTitle: postDetails.get(postId)?.post_title ?? t("Record details"),
    event: eventsByPost.get(postId),
  }));
  const chronological = [...citations].sort((left, right) => {
    const leftEpoch = observedEpoch(left.event);
    const rightEpoch = observedEpoch(right.event);
    if (leftEpoch === null) return rightEpoch === null ? left.citationNumber - right.citationNumber : 1;
    if (rightEpoch === null) return -1;
    return leftEpoch - rightEpoch || left.citationNumber - right.citationNumber;
  });

  function selectCitation(citation: Citation, target: "card" | "citation") {
    setSelectedPostId(citation.postId);
    const destination = target === "card"
      ? cardRefs.current.get(citation.postId)
      : citationRefs.current.get(citation.postId);
    destination?.scrollIntoView?.({ block: "nearest", inline: "nearest" });
    destination?.focus({ preventScroll: true });
  }

  return (
    <div className="ask-answer-layout">
      <section className="ask-conversation" aria-label={t("Conversation")}>
        <div className="ask-message ask-message-question">
          <span className="ask-message-speaker">{t("You")}</span>
          <p>{question}</p>
        </div>
        <div className="ask-message ask-message-answer">
          <span className="ask-message-speaker">{t("Ask Agent")}</span>
          {answer.answer_text ? <p>{answer.answer_text}</p> : null}
          {citations.length ? (
            <nav className="ask-inline-citations" aria-label={t("Answer citations")}>
              {citations.map((citation) => (
                <button
                  key={citation.postId}
                  ref={(node) => {
                    if (node) citationRefs.current.set(citation.postId, node);
                    else citationRefs.current.delete(citation.postId);
                  }}
                  type="button"
                  className="ask-inline-citation"
                  aria-label={tf("Show event {number}: {title}", {
                    number: citation.citationNumber,
                    title: citation.postTitle,
                  })}
                  aria-pressed={selectedPostId === citation.postId}
                  onClick={() => selectCitation(citation, "card")}
                >
                  [{citation.citationNumber}]
                </button>
              ))}
            </nav>
          ) : null}
        </div>
        {answer.next_action ? <p className="ask-next-action">{t(answer.next_action)}</p> : null}
      </section>

      {chronological.length ? (
        <section className="ask-evidence-timeline" aria-labelledby="ask-evidence-timeline-heading">
          <h4 id="ask-evidence-timeline-heading">{t("Answer evidence timeline")}</h4>
          <p>{t("Select a citation to review the event and open its source.")}</p>
          <ol>
            {chronological.map((citation) => {
              const post = postDetails.get(citation.postId);
              const facts = answer.cited_post_evidence?.find(
                (item) => item.post_id === citation.postId,
              )?.facts ?? [];
              const images = answer.cited_post_images?.filter(
                (image) => image.post_id === citation.postId,
              ) ?? [];
              const sourceReferences = answer.cited_source_references?.filter(
                (reference) => reference.post_id === citation.postId,
              ) ?? [];
              const selected = selectedPostId === citation.postId;
              return (
                <li key={citation.postId} className={selected ? "ask-event-selected" : undefined}>
                  <article aria-label={tf("Evidence {number}: {title}", {
                    number: citation.citationNumber,
                    title: citation.postTitle,
                  })}>
                    <button
                      ref={(node) => {
                        if (node) cardRefs.current.set(citation.postId, node);
                        else cardRefs.current.delete(citation.postId);
                      }}
                      type="button"
                      className="ask-event-select"
                      aria-label={tf("Return to answer citation {number}: {title}", {
                        number: citation.citationNumber,
                        title: citation.postTitle,
                      })}
                      aria-pressed={selected}
                      onClick={() => selectCitation(citation, "citation")}
                    >
                      <span className="ask-event-marker">[{citation.citationNumber}]</span>
                      <span>
                        <strong>{citation.postTitle}</strong>
                        <small>{observedTimeLabel(citation.event)}</small>
                      </span>
                    </button>
                    {post?.source_post_revision_id ? (
                      <p className="post-meta">
                        {t("Retained revision")}
                        {post.evidence_available_at ? ` · ${post.evidence_available_at}` : ""}
                        {post.live_changed_after_cutoff ? ` · ${t("Live source changed later")}` : ""}
                      </p>
                    ) : null}
                    {facts.length ? (
                      <ul className="post-evidence-list" aria-label={t("Evidence facts")}>
                        {facts.map((fact, index) => (
                          <li key={`${fact.kind}:${fact.text}:${index}`}>
                            <span>{chatEvidenceKindLabel(fact.kind)}</span>
                            <span>: {fact.text}</span>
                          </li>
                        ))}
                      </ul>
                    ) : null}
                    {images.map((image) => (
                      <p key={`${image.post_id}:${image.unit_index}`} className="post-meta">
                        {t("Image evidence")}: {image.caption?.trim() ? image.caption : t("Untitled image")}
                        {image.extracted_text ? ` — ${image.extracted_text}` : ""}
                        {image.tags.length ? ` — ${t("Image tags")}: ${image.tags.join(", ")}` : ""}
                      </p>
                    ))}
                    {sourceReferences.length ? (
                      <section aria-label={t("Related public sources")}>
                        <h5>{t("Related public sources")}</h5>
                        <ul className="post-evidence-list">
                          {sourceReferences.map((reference) => (
                            <li key={`${reference.evidence_url}:${reference.lead_kind_code}`}>
                              {isPublicDocumentUrl(reference.evidence_url) ? (
                                <a
                                  href={reference.evidence_url}
                                  target="_blank"
                                  rel="noreferrer"
                                >
                                  {reference.evidence_title_text || reference.evidence_url}
                                </a>
                              ) : null}
                              {reference.evidence_excerpt_text ? (
                                <span>{` — ${reference.evidence_excerpt_text}`}</span>
                              ) : null}
                            </li>
                          ))}
                        </ul>
                      </section>
                    ) : null}
                    <div className="ask-event-actions">
                      <button type="button" className="citation-chip" onClick={() => onOpenEvidence(citation.postId)}>
                        {t("View evidence")}
                      </button>
                      <button type="button" className="btn-link" onClick={() => onOpenPost(citation.postId)}>
                        {tf("Open post: {label}", { label: citation.postTitle })}
                      </button>
                    </div>
                  </article>
                </li>
              );
            })}
          </ol>
          {selectedPostId ? (
            <p className="visually-hidden" role="status">
              {tf("Selected evidence: {title}", {
                title: citations.find((citation) => citation.postId === selectedPostId)?.postTitle ?? "",
              })}
            </p>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
