import { useEffect, useRef, type FormEvent } from "react";
import { CloseIcon } from "./icons";

export type GlobalSearchProps = {
  open: boolean;
  value: string;
  searchLabel: string;
  inputLabel: string;
  closeLabel: string;
  helpText: string;
  onOpen: () => void;
  onClose: () => void;
  onChange: (value: string) => void;
  onSubmit: (value: string) => void;
};

export function GlobalSearch({
  open,
  value,
  searchLabel,
  inputLabel,
  closeLabel,
  helpText,
  onOpen,
  onClose,
  onChange,
  onSubmit,
}: GlobalSearchProps) {
  const triggerRef = useRef<HTMLButtonElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    inputRef.current?.focus();
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      onClose();
      triggerRef.current?.focus();
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [onClose, open]);

  function closeAndReturnFocus() {
    onClose();
    triggerRef.current?.focus();
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit(value);
  }

  return (
    <div className="app-header-search-wrap">
      <button
        ref={triggerRef}
        type="button"
        className="btn-secondary app-header-search"
        aria-expanded={open}
        aria-controls="global-search-panel"
        onClick={open ? closeAndReturnFocus : onOpen}
      >
        {searchLabel}
      </button>
      {open ? (
        <form
          id="global-search-panel"
          className="global-search-panel"
          role="search"
          aria-label={inputLabel}
          onSubmit={handleSubmit}
        >
          <div className="global-search-input-row">
            <label>
              <span className="visually-hidden">{inputLabel}</span>
              <input
                ref={inputRef}
                type="search"
                value={value}
                onChange={(event) => onChange(event.target.value)}
                placeholder={inputLabel}
              />
            </label>
            <button type="submit" className="btn-primary global-search-submit">
              {searchLabel}
            </button>
            <button
              type="button"
              className="global-search-close"
              aria-label={closeLabel}
              onClick={closeAndReturnFocus}
            >
              <CloseIcon />
            </button>
          </div>
          <p className="global-search-help">{helpText}</p>
        </form>
      ) : null}
    </div>
  );
}
