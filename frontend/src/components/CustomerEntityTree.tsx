import type { CustomerMasterEntity, RelatedNode } from "../api";
import { t, tf } from "../i18n";
import { customerScopeFacetLabel } from "./customerEntityTreeUtils";

export interface CustomerEntityTreeNode {
  entity: CustomerMasterEntity;
  children: CustomerEntityTreeNode[];
}

export function CustomerRelatedPostCard({
  postId,
  postTitle,
  postBodyExcerpt,
  postBodyTruncated,
  onOpenPost,
}: {
  postId: string;
  postTitle: string;
  postBodyExcerpt?: string | null;
  postBodyTruncated?: boolean;
  onOpenPost: (postId: string) => void;
}) {
  return (
    <button
      type="button"
      className="related-post-card"
      aria-label={tf("Open related post: {label}", { label: postTitle })}
      onClick={() => onOpenPost(postId)}
    >
      <span className="related-post-content">
        <strong>{postTitle}</strong>
        <span className="post-body-excerpt" aria-label={t("Post body preview")}>
          {postBodyExcerpt || t("No post body.")}
          {postBodyTruncated ? " ..." : ""}
        </span>
      </span>
      <span>{t("Open record")}</span>
    </button>
  );
}

export function CustomerEntityTreeRow({
  node,
  depth,
  expandedEntityId,
  relatedByEntity,
  relatedLoading,
  onToggle,
  onOpenPost,
}: {
  node: CustomerEntityTreeNode;
  depth: number;
  expandedEntityId: string | null;
  relatedByEntity: Record<string, RelatedNode[]>;
  relatedLoading: string | null;
  onToggle: (entityId: string) => void;
  onOpenPost: (postId: string) => void;
}) {
  const { entity, children } = node;
  const relatedPosts = (relatedByEntity[entity.corporate_entity_id] ?? []).filter(
    // "node_post" mirrors App.tsx's own NODE_POST constant -- inlined here
    // rather than imported to keep this file free of App.tsx's monolith.
    (related) => related.node_type_code === "node_post",
  );
  return (
    <li style={{ marginInlineStart: depth * 20 }}>
      <button
        type="button"
        className="customer-entity-button"
        aria-expanded={expandedEntityId === entity.corporate_entity_id}
        onClick={() => onToggle(entity.corporate_entity_id)}
      >
        <strong>{entity.entity_name}</strong>
        <span className="customer-entity-meta">
          <span>{entity.corporate_entity_code} · {entity.entity_level_label}</span>
          {(entity.scope_facets ?? []).map((facet) => (
            <span className="customer-scope-chip" key={facet}>{customerScopeFacetLabel(facet)}</span>
          ))}
        </span>
      </button>
      {expandedEntityId === entity.corporate_entity_id ? (
        <div className="customer-related-posts">
          {relatedLoading === entity.corporate_entity_id ? <p>{t("Loading related posts...")}</p> : null}
          {relatedLoading !== entity.corporate_entity_id && relatedPosts.length === 0 ? (
            <p className="popup-placeholder">{t("No linked posts yet.")}</p>
          ) : null}
          {relatedPosts.length > 0 ? (
            <ul aria-label={`${t("Related posts")}: ${entity.entity_name}`}>
              {relatedPosts.map((related) => (
                <li key={related.node_id}>
                  <CustomerRelatedPostCard
                    postId={related.node_id}
                    postTitle={related.label ?? related.node_id}
                    postBodyExcerpt={related.post_body_excerpt}
                    postBodyTruncated={related.post_body_truncated}
                    onOpenPost={onOpenPost}
                  />
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
      {children.length > 0 ? (
        <ul className="customer-master-list customer-master-tree-children" aria-label={tf("Affiliates of {name}", { name: entity.entity_name })}>
          {children.map((child) => (
            <CustomerEntityTreeRow
              key={child.entity.corporate_entity_id}
              node={child}
              depth={depth + 1}
              expandedEntityId={expandedEntityId}
              relatedByEntity={relatedByEntity}
              relatedLoading={relatedLoading}
              onToggle={onToggle}
              onOpenPost={onOpenPost}
            />
          ))}
        </ul>
      ) : null}
    </li>
  );
}
