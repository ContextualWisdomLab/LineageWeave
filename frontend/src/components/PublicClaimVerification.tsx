import type { ExternalClaim } from "../api";
import { t } from "../i18n";
import { safeHttpUrl } from "../safeHttpUrl";
import "./PublicClaimVerification.css";

/** Keep public web evidence separate from authorized internal citations. */
export function PublicClaimVerification({ claims }: { claims: ExternalClaim[] }) {
  if (claims.length === 0) return null;
  return (
    <section className="popup-section public-claim-verification" aria-label={t("Public verification")}>
      <h4>{t("Public verification")}</h4>
      {claims.map((claim, claimIndex) => (
        <article className="public-claim-card" key={`${claim.claim_kind}:${claim.claim_text}:${claimIndex}`}>
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
            {claim.evidence.map((evidence, evidenceIndex) => (
              <li key={`${evidence.url}:${evidence.title}:${evidenceIndex}`}>
                {safeHttpUrl(evidence.url) ? (
                  <a href={safeHttpUrl(evidence.url)!} target="_blank" rel="noreferrer">
                    {evidence.title}
                  </a>
                ) : (
                  <span>{evidence.title}</span>
                )}
                <span>{evidence.snippet}</span>
              </li>
            ))}
          </ul>
        </article>
      ))}
    </section>
  );
}
