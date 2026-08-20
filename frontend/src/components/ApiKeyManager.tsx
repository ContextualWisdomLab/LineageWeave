import { useCallback, useEffect, useState, type FormEvent } from "react";
import { createApiKey, fetchApiKeys, revokeApiKey, type ApiKeyRecord } from "../api";
import { t } from "../i18n";

export function ApiKeyManager({ accessToken }: { accessToken: string }) {
  const [apiKeys, setApiKeys] = useState<ApiKeyRecord[]>([]);
  const [keyName, setKeyName] = useState("");
  const [newKey, setNewKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(
    () =>
      fetchApiKeys(accessToken)
        .then((result) => setApiKeys(result.api_keys))
        .catch(() => setError(t("API key could not be loaded.")))
        .finally(() => setLoading(false)),
    [accessToken],
  );

  useEffect(() => {
    void reload();
  }, [reload]);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      const created = await createApiKey(accessToken, keyName);
      setNewKey(created.api_key);
      setKeyName("");
      reload();
    } catch {
      setError(t("API key could not be created."));
    }
  }

  async function handleRevoke(apiKeyId: string) {
    setError(null);
    try {
      await revokeApiKey(accessToken, apiKeyId);
      reload();
    } catch {
      setError(t("API key could not be revoked."));
    }
  }

  return (
    <section className="popup-section" aria-labelledby="api-key-heading">
      <h2 id="api-key-heading">{t("API keys")}</h2>
      <p>{t("MCP read")}</p>
      <form onSubmit={handleCreate}>
        <label>
          {t("Key name")}
          <input value={keyName} onChange={(event) => setKeyName(event.target.value)} required maxLength={100} />
        </label>
        <button type="submit">{t("Create API key")}</button>
      </form>
      {newKey ? (
        <p role="status">
          {t("Copy this key now; it will not be shown again.")} <code>{newKey}</code>
          <button type="button" onClick={() => void navigator.clipboard?.writeText(newKey)}>
            {t("Copy")}
          </button>
        </p>
      ) : null}
      {error ? <p className="error">{error}</p> : null}
      {loading ? <p>{t("Loading API keys...")}</p> : null}
      {!loading && apiKeys.length === 0 ? <p>{t("No API keys.")}</p> : null}
      <ul>
        {apiKeys.map((apiKey) => (
          <li key={apiKey.api_key_id}>
            <strong>{apiKey.key_name}</strong> <code>{apiKey.key_prefix}...</code> {t("MCP read")}
            {apiKey.revoked_at ? ` (${t("Revoked")})` : ` (${t("Active")})`}
            {!apiKey.revoked_at ? (
              <button type="button" onClick={() => void handleRevoke(apiKey.api_key_id)}>
                {t("Revoke")}
              </button>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
