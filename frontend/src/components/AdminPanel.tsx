import { useState } from "react";
import { t } from "../i18n";

export type AdminPanelProps = {
  currentBrandName: string;
  onBrandNameChange: (newName: string) => void;
};

export function AdminPanel({ currentBrandName, onBrandNameChange }: AdminPanelProps) {
  const [draftName, setDraftName] = useState(currentBrandName);
  const [saved, setSaved] = useState(false);

  function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (draftName.trim()) {
      onBrandNameChange(draftName.trim());
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    }
  }

  return (
    <div className="popup-section">
      <div className="lineage-home-header">
        <h2>{t("Admin settings")}</h2>
      </div>
      <form onSubmit={handleSave} className="admin-form">
        <label htmlFor="brandNameInput" style={{ display: "block", marginBottom: "0.5rem" }}>
          <strong>* {t("Tenant brand name")}</strong>
        </label>
        <input
          id="brandNameInput"
          type="text"
          value={draftName}
          onChange={(e) => setDraftName(e.target.value)}
          style={{ padding: "0.5rem", width: "100%", maxWidth: "400px", marginBottom: "1rem" }}
          aria-label={t("Tenant brand name")}
        />
        <div>
          <button type="submit" className="btn-primary" disabled={!draftName.trim() || draftName === currentBrandName}>
            {t("Save settings")}
          </button>
          {saved && <span style={{ marginLeft: "1rem", color: "green" }}>{t("Settings saved!")}</span>}
        </div>
      </form>
    </div>
  );
}
