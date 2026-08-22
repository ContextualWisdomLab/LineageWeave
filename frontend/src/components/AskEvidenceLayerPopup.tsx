import { useEffect, useId, useRef } from "react";
import { chatEvidenceKindLabel } from "../evidenceKindLabels";
import { t, tf } from "../i18n";
import { PopupCloseButton } from "./PopupCloseButton";

export type AskEvidenceLayerFact = {
  kind: string;
  text: string;
};

export type AskEvidenceLayerImage = {
  unit_index: number;
  caption: string | null;
  extracted_text: string | null;
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
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    panelRef.current?.focus();
  }, []);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

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
            <h3>{t("Evidence facts")}</h3>
            <ul className="post-evidence-list" aria-label={t("Evidence facts")}>
              {facts.map((fact, index) => (
                <li key={`${fact.kind}:${fact.text}:${index}`}>
                  <span>{chatEvidenceKindLabel(fact.kind)}</span>
                  <span>{fact.text}</span>
                </li>
              ))}
            </ul>
          </section>
        ) : null}
        {images.length > 0 ? (
          <section className="popup-section">
            <h3>{t("Image evidence")}</h3>
            <ul className="post-evidence-list" aria-label={t("Image evidence")}>
              {images.map((image) => (
                <li key={image.unit_index}>
                  <span>{image.caption ?? t("Untitled image")}</span>
                  {image.extracted_text ? <span>{image.extracted_text}</span> : null}
                </li>
              ))}
            </ul>
          </section>
        ) : null}
        <button type="button" className="keyman-select" onClick={() => onOpenPost(postId)}>
          {tf("Open post: {label}", { label: postTitle })}
        </button>
      </div>
    </div>
  );
}
