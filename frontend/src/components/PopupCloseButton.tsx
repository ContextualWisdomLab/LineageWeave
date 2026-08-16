export type PopupCloseButtonProps = {
  onClose: () => void;
  label: string;
};

export function PopupCloseButton({ onClose, label }: PopupCloseButtonProps) {
  return (
    <button
      type="button"
      className="popup-close"
      onClick={onClose}
      aria-label={label}
    >
      &times;
    </button>
  );
}
