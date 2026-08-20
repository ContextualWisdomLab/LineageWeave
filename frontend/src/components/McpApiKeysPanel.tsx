import { useCallback, useEffect, useState, type FormEvent } from "react";
import {
  createMcpApiKey,
  fetchMcpApiKeys,
  revokeMcpApiKey,
  type McpApiKey,
} from "../api";
import { t } from "../i18n";

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "-";
}

export function McpApiKeysPanel({ accessToken }: { accessToken: string }) {
  const [keys, setKeys] = useState<McpApiKey[]>([]);
  const [displayName, setDisplayName] = useState("");
  const [expiresAt, setExpiresAt] = useState("");
  const [newKey, setNewKey] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadKeys = useCallback(async () => {
    try {
      setKeys((await fetchMcpApiKeys(accessToken)).api_keys);
    } catch {
      setError(t("The key could not be loaded."));
    }
  }, [accessToken]);

  useEffect(() => {
    void loadKeys();
  }, [loadKeys]);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!displayName.trim()) {
      setError(t("Key label is required."));
      return;
    }
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const created = await createMcpApiKey(accessToken, displayName, expiresAt ? `${expiresAt}T23:59:59Z` : null);
      setKeys((current) => [created, ...current]);
      setNewKey(created.api_key);
      setDisplayName("");
      setExpiresAt("");
      setNotice(t("MCP key created."));
    } catch {
      setError(t("The key could not be created."));
    } finally {
      setBusy(false);
    }
  }

  async function handleRevoke(keyId: string) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const revoked = await revokeMcpApiKey(accessToken, keyId);
      setKeys((current) => current.map((key) => (key.mcp_api_key_id === keyId ? revoked : key)));
      setNotice(t("MCP key revoked."));
    } catch {
      setError(t("The key could not be revoked."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="buyer-destination" aria-labelledby="mcp-api-keys-heading">
      <p className="section-eyebrow">{t("API keys")}</p>
      <h2 id="mcp-api-keys-heading">{t("API keys")}</h2>
      <p className="buyer-destination-intro">{t("Manage MCP access keys for this account.")}</p>
      {error ? <p className="error" role="alert">{error}</p> : null}
      {notice ? <p role="status">{notice}</p> : null}
      {newKey ? (
        <section aria-live="polite">
          <p>{t("A new key is shown once. Store it before leaving this page.")}</p>
          <code>{newKey}</code>
          <button type="button" onClick={() => void navigator.clipboard?.writeText(newKey)}>
            {t("Copy key")}
          </button>
        </section>
      ) : null}
      <form onSubmit={handleCreate}>
        <label>
          {t("Key label")}
          <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} maxLength={120} />
        </label>
        <label>
          {t("Expires")}
          <input type="date" value={expiresAt} onChange={(event) => setExpiresAt(event.target.value)} />
        </label>
        <button type="submit" disabled={busy}>{busy ? t("Creating...") : t("Create key")}</button>
      </form>
      {keys.length === 0 ? <p>{t("No MCP keys have been created.")}</p> : null}
      <ul>
        {keys.map((key) => (
          <li key={key.mcp_api_key_id}>
            <strong>{key.display_name}</strong> <code>{key.key_prefix}...</code>
            <span>{t("Created")}: {formatDate(key.created_at)}</span>
            <span>{t("Expires")}: {formatDate(key.expires_at)}</span>
            {key.revoked_at ? <span>{t("Revoked")}: {formatDate(key.revoked_at)}</span> : (
              <button type="button" disabled={busy} onClick={() => void handleRevoke(key.mcp_api_key_id)}>{busy ? t("Revoking...") : t("Revoke")}</button>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
