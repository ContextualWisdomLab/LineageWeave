import { useState } from "react";
import { t } from "../i18n";
import { updateTenantConfig } from "../api";

export type AdminPanelProps = {
  currentBrandName: string;
  onBrandNameChange: (newName: string) => void;
  accessToken: string;
};

export function AdminPanel({ currentBrandName, onBrandNameChange, accessToken }: AdminPanelProps) {
  const [draftName, setDraftName] = useState(currentBrandName);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (draftName.trim()) {
      setSaving(true);
      setError(null);
      try {
        const config = await updateTenantConfig(accessToken, draftName.trim());
        onBrandNameChange(config.brandName);
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
      } catch (err: any) {
        setError(err.message || "Failed to update settings");
      } finally {
        setSaving(false);
      }
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
          disabled={saving}
        />
        <div>
          <button type="submit" className="btn-primary" disabled={saving || !draftName.trim() || draftName === currentBrandName}>
            {saving ? t("Saving...") : t("Save settings")}
          </button>
          {saved && (
            <span role="status" style={{ marginLeft: "1rem", color: "green" }}>
              {t("Settings saved!")}
            </span>
          )}
          {error && (
            <span role="alert" style={{ marginLeft: "1rem", color: "red" }}>
              {t(error)}
            </span>
          )}
        </div>
      </form>
    </div>
  );
}
