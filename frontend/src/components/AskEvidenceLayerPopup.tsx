import { useEffect, useId, useRef } from "react";
import { chatEvidenceKindLabel } from "../evidenceKindLabels";
import { isFocusableVisible } from "../focusVisibility";
import { t, tf } from "../i18n";
import { PopupCloseButton } from "./PopupCloseButton";

const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "summary",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  '[tabindex]:not([tabindex="-1"])',
].join(",");

export type AskEvidenceLayerFact = {
  kind: string;
  text: string;
};

export type AskEvidenceLayerImage = {
  unit_index: number;
  caption: string | null;
  extracted_text: string | null;
  tags: string[];
};

export type AskEvidenceLayerPopupProps = {
  postId: string;
  postTitle: string;
  facts: AskEvidenceLayerFact[];
  images: AskEvidenceLayerImage[];
  onClose: () => void;
  onOpenPost: (postId: string) => void;
};

/**
 * A focused evidence layer for one Ask Agent citation -- opened from the
 * answer without leaving it, unlike the full post detail popup.
 *
 * Next action: open the source post for the complete record, or close to
 * return to the answer.
 */
export function AskEvidenceLayerPopup({
  postId,
  postTitle,
  facts,
  images,
  onClose,
  onOpenPost,
}: AskEvidenceLayerPopupProps) {
  const headingId = useId();
  const factsHeadingId = useId();
  const imagesHeadingId = useId();
  const panelRef = useRef<HTMLDivElement>(null);
  const restoreFocusOnUnmountRef = useRef(true);

  useEffect(() => {
    const previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    panelRef.current?.focus();
    return () => {
      if (restoreFocusOnUnmountRef.current && previouslyFocused?.isConnected) {
        previouslyFocused.focus();
      }
    };
  }, []);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab") return;

      const panel = panelRef.current;
      if (!panel) return;
      const focusable = Array.from(
        panel.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
      ).filter(isFocusableVisible);
      if (focusable.length === 0) {
        event.preventDefault();
        panel.focus();
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;
      if (active === panel || !panel.contains(active)) {
        event.preventDefault();
        (event.shiftKey ? last : first).focus();
        return;
      }
      if (event.shiftKey && active === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  function handleOpenPost() {
    // Opening the full post is a workflow transition rather than returning to
    // the invoking citation, so do not restore focus to the old trigger while
    // the destination surface is being mounted.
    restoreFocusOnUnmountRef.current = false;
    onClose();
    onOpenPost(postId);
  }

  return (
    <div className="popup-backdrop" onClick={onClose}>
      <div
        ref={panelRef}
        className="popup-panel ask-evidence-layer"
        role="dialog"
        aria-modal="true"
        aria-labelledby={headingId}
        tabIndex={-1}
        onClick={(event) => event.stopPropagation()}
      >
        <PopupCloseButton onClose={onClose} label={t("Close evidence panel")} />
        <h2 id={headingId}>{postTitle}</h2>
        {facts.length === 0 && images.length === 0 ? (
          <p className="popup-placeholder">{t("No persisted evidence is available for this citation.")}</p>
        ) : null}
        {facts.length > 0 ? (
          <section className="popup-section">
            <h3 id={factsHeadingId}>{t("Evidence facts")}</h3>
            <ul className="post-evidence-list" aria-labelledby={`${headingId} ${factsHeadingId}`}>
              {facts.map((fact, index) => (
                <li key={`${fact.kind}:${fact.text}:${index}`}>
                  <span>{chatEvidenceKindLabel(fact.kind)}: </span>
                  <span>{fact.text}</span>
                </li>
              ))}
            </ul>
          </section>
        ) : null}
        {images.length > 0 ? (
          <section className="popup-section">
            <h3 id={imagesHeadingId}>{t("Image evidence")}</h3>
            <ul className="post-evidence-list" aria-labelledby={`${headingId} ${imagesHeadingId}`}>
              {images.map((image) => (
                <li key={image.unit_index}>
                  <span>{image.caption?.trim() ? image.caption : t("Untitled image")}</span>
                  {image.extracted_text ? <span> · {image.extracted_text}</span> : null}
                  {image.tags.length ? <span> · {t("Image tags")}: {image.tags.join(", ")}</span> : null}
                </li>
              ))}
            </ul>
          </section>
        ) : null}
        <button type="button" className="keyman-select" onClick={handleOpenPost}>
          {tf("Open post: {label}", { label: postTitle })}
        </button>
      </div>
    </div>
  );
}
