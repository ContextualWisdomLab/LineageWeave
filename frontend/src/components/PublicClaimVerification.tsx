import type { ExternalClaim } from "../api";
import { t } from "../i18n";
import "./PublicClaimVerification.css";

/** Keep public web evidence separate from authorized internal citations. */
export function PublicClaimVerification({
  claims,
  statusCode,
}: {
  claims: ExternalClaim[];
  statusCode?: string;
}) {
  if (
    claims.length === 0
    && statusCode !== "external_verification_completed"
    && statusCode !== "external_verification_unavailable"
  ) return null;
  return (
    <section className="popup-section public-claim-verification" aria-label={t("Public verification")}>
      <h4>{t("Public verification")}</h4>
      {claims.length === 0 && (
        <p>
          {t(
            statusCode === "external_verification_unavailable"
              ? "Public verification is unavailable. Try again later."
              : "Not enough public information",
          )}
        </p>
      )}
      {claims.map((claim) => (
        <article className="public-claim-card" key={`${claim.claim_kind}:${claim.claim_text}`}>
          <p>
            {t(
              claim.status_code === "claim_supported"
                ? "Supported by public evidence"
                : claim.status_code === "claim_refuted"
                  ? "Conflicts with public evidence"
                  : "Not enough public information",
            )}
          </p>
          <p>{claim.rationale}</p>
          <ul className="public-claim-evidence">
            {claim.evidence.map((evidence) => (
              <li key={evidence.url}>
                <a href={evidence.url} target="_blank" rel="noreferrer">
                  {evidence.title}
                </a>
                <span>{evidence.snippet}</span>
              </li>
            ))}
          </ul>
        </article>
      ))}
    </section>
  );
}
