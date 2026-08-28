import type { ProductEvidence } from "../api";
import { t } from "../i18n";

function resolutionNextAction(status: ProductEvidence["resolution_status_code"]): string | null {
  if (status === "missing") return t("Ask a catalog manager to register this cited product, then run product analysis again.");
  if (status === "tie") return t("Ask a catalog manager to distinguish the matching products, then run product analysis again.");
  if (status === "unavailable") return t("Retry product analysis after catalog access is restored.");
  return null;
}

export function ProductEvidenceList({ products, onOpenPost }: { products: ProductEvidence[]; onOpenPost: (postId: string) => void }) {
  return (
    <section className="popup-section" aria-label={t("Product evidence")}>
      <h3>{t("Product evidence")}</h3>
      <ul className="evidence-list">
        {products.map((product) => {
          const nextAction = resolutionNextAction(product.resolution_status_code);
          return (
          <li key={`${product.evidence_post_id}-${product.mention_ordinal}`}>
            <strong>{product.canonical_product_name ?? product.extracted_product_name}</strong>
            {product.product_catalog_code ? <p>{product.product_catalog_code}</p> : null}
            <p>{product.evidence_text}</p>
            <button type="button" className="btn-link" onClick={() => onOpenPost(product.evidence_post_id)}>{t("Open product evidence post")}</button>
            {(product.relations ?? []).map((relation) => (
              <div key={`${relation.target_kind_code}-${relation.target_id}-${relation.relation_type_code}`}>
                <p><strong>{relation.target_label}</strong> · {relation.evidence_text}</p>
                {relation.evidence_post_id !== product.evidence_post_id ? <button type="button" className="btn-link" onClick={() => onOpenPost(relation.evidence_post_id)}>{t("Open relationship evidence post")}</button> : null}
              </div>
            ))}
            {nextAction ? (
              <p className="popup-placeholder" role="status">
                {nextAction}
              </p>
            ) : null}
          </li>
          );
        })}
      </ul>
    </section>
  );
}
