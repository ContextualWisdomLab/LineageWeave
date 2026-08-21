import { CloseIcon } from "./icons";

export type PopupCloseButtonProps = {
  onClose: () => void;
  label: string;
};

/**
 * Closes the evidence panel or post popup.
 *
 * Next action: click to return to the list or the reconstruction view.
 */
export function PopupCloseButton({ onClose, label }: PopupCloseButtonProps) {
  return (
    <button
      type="button"
      className="popup-close"
      onClick={onClose}
      aria-label={label}
    >
      <CloseIcon />
    </button>
  );
}
