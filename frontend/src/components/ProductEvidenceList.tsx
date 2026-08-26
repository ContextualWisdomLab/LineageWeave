import type { ProductEvidence } from "../api";
import { t } from "../i18n";

export function ProductEvidenceList({ products }: { products: ProductEvidence[] }) {
  return (
    <section className="popup-section" aria-label={t("Product evidence")}>
      <h3>{t("Product evidence")}</h3>
      <ul className="evidence-list">
        {products.map((product) => (
          <li key={`${product.evidence_post_id}-${product.mention_ordinal}`}>
            <strong>{product.canonical_product_name ?? product.extracted_product_name}</strong>
            <p>{product.evidence_text}</p>
            {(product.relations ?? []).map((relation) => (
              <p key={`${relation.target_kind_code}-${relation.target_id}-${relation.relation_type_code}`}>
                <strong>{relation.target_label}</strong> · {relation.evidence_text}
              </p>
            ))}
            {product.resolution_status_code !== "unique" ? (
              <p className="popup-placeholder" role="status">
                {t("Review the product catalog before using this relationship.")}
              </p>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
