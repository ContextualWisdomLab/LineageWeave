import type { RelatedNode, RelatedNodeType } from "../api";

export const KG_EMPTY = "이 글의 지식그래프를 아직 받을 수 없습니다";

export type KnowledgeGraphDepthProps = {
  related: RelatedNode[] | null;
  error?: string | null;
  onSelectPost?: (postId: string) => void;
};

type KnownRelatedType = RelatedNodeType;

function isKnownRelatedType(code: string): code is KnownRelatedType {
  return (
    code === "node_person" ||
    code === "node_post" ||
    code === "node_corporate_entity" ||
    code === "node_team"
  );
}

function nodeTypeLabel(code: string): string {
  if (!isKnownRelatedType(code)) {
    return code;
  }
  switch (code) {
    case "node_person":
      return "Person";
    case "node_post":
      return "Post";
    case "node_corporate_entity":
      return "Organization";
    case "node_team":
      return "Team";
    default: {
      const _exhaustive: never = code;
      return _exhaustive;
    }
  }
}

export function KnowledgeGraphDepth({ related, error, onSelectPost }: KnowledgeGraphDepthProps) {
  return (
    <section className="popup-section" aria-label="지식그래프">
      <h3>지식그래프</h3>
      {error ? <p className="error">{error}</p> : null}
      {related === null && !error ? <p>Loading related nodes...</p> : null}
      {related && related.length === 0 ? <p className="popup-placeholder">{KG_EMPTY}</p> : null}
      {related && related.length > 0 ? (
        <ul>
          {related.map((node) => {
            const label = node.label ?? node.node_id;
            const typeLabel = node.ontology_label ?? nodeTypeLabel(node.node_type_code);
            const side = node.person_side_label ? ` · ${node.person_side_label}` : "";
            if (node.node_type_code === "node_post" && onSelectPost) {
              return (
                <li key={`${node.node_type_code}:${node.node_id}`}>
                  <button type="button" onClick={() => onSelectPost(node.node_id)}>
                    {typeLabel} · {label}
                    {side}
                  </button>
                </li>
              );
            }
            return (
              <li key={`${node.node_type_code}:${node.node_id}`}>
                {typeLabel} · {label}
                {side}
              </li>
            );
          })}
        </ul>
      ) : null}
    </section>
  );
}
