import type { PublicClaimVerdict } from "../api";
import { t, tf } from "../i18n";

export type PublicClaimListProps = {
  claims: PublicClaimVerdict[];
  onSelectPost: (postId: string) => void;
};

const KIND_LABELS: Record<string, string> = {
  claim_organization_presence: "Organization presence",
  claim_public_event: "Public event",
  claim_public_relationship: "Public relationship",
};

const STATUS_LABELS: Record<string, string> = {
  claim_supported: "Supported",
  claim_refuted: "Refuted",
  claim_not_enough_information: "Not enough information",
  claim_unavailable: "Unavailable",
};

function nextActionLabel(claim: PublicClaimVerdict): string {
  if (claim.next_action === `Public claim is on ${claim.source_post_title}. Open that post.`) {
    return tf("Public claim is on {title}. Open that post.", {
      title: claim.source_post_title,
    });
  }
  return t(claim.next_action);
}

/**
 * Authorized public-claim verdicts for an opted-in Global Ask.
 *
 * Each row opens the exact source post. External URLs stay links and
 * never become cited post ids (ADR 0229).
 */
export function PublicClaimList({ claims, onSelectPost }: PublicClaimListProps) {
  if (claims.length === 0) {
    return null;
  }
  return (
    <ul className="ticket-list" aria-label={t("Public claims")}>
      {claims.map((claim) => {
        const kindLabel = t(KIND_LABELS[claim.claim_kind_code] ?? "Recorded claim");
        const statusLabel = t(STATUS_LABELS[claim.status_code] ?? "Status unavailable");
        return (
          <li key={claim.public_claim_envelope_id} className="ticket-list-item public-claim-list-item">
            <button
              type="button"
              className="post-list-item public-claim-list-row"
              aria-label={tf("Open public claim: {title}", {
                title: claim.source_post_title,
              })}
              title={t("Open this post so the public claim is current.")}
              onClick={() => onSelectPost(claim.source_post_id)}
            >
              <span className="ticket-title">
                {kindLabel}: {claim.source_post_title} · {claim.subject_label}
              </span>
              <span className="post-badge">{statusLabel}</span>
              <span className="post-badge">{nextActionLabel(claim)}</span>
            </button>
            {claim.external_evidence_urls.length > 0 ? (
              <ul aria-label={t("Public web evidence")}>
                {claim.external_evidence_urls.map((url) => (
                  <li key={url}>
                    <a href={url} target="_blank" rel="noopener noreferrer">
                      {url}
                    </a>
                  </li>
                ))}
              </ul>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}
