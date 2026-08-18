import type { AffiliateNode } from "../api";

export const AFFILIATE_TREE_EMPTY = "이 글의 고객 그룹을 아직 받을 수 없습니다";

export type AffiliateTreePanelProps = {
  trees: AffiliateNode[] | null;
  error?: string | null;
};

function TreeNodes({ nodes }: { nodes: AffiliateNode[] }) {
  return (
    <ul>
      {nodes.map((node) => (
        <li key={`${node.entity_id ?? "unbound"}:${node.entity_name}`}>
          {node.entity_name}
          {node.entity_level_label ? ` · ${node.entity_level_label}` : ""}
          {node.people.length > 0
            ? ` · ${node.people.map((person) => person.person_name).join(" · ")}`
            : ""}
          {node.children.length > 0 ? <TreeNodes nodes={node.children} /> : null}
        </li>
      ))}
    </ul>
  );
}

export function AffiliateTreePanel({ trees, error }: AffiliateTreePanelProps) {
  return (
    <section className="popup-section" aria-label="고객 그룹">
      <h3>고객 그룹</h3>
      {error ? <p className="error">{error}</p> : null}
      {trees === null && !error ? <p>Loading customer group...</p> : null}
      {trees && trees.length === 0 ? <p className="popup-placeholder">{AFFILIATE_TREE_EMPTY}</p> : null}
      {trees && trees.length > 0 ? <TreeNodes nodes={trees} /> : null}
    </section>
  );
}
