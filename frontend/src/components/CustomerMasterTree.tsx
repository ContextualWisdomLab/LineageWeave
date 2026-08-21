import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FocusEvent,
  type KeyboardEvent,
  type MouseEvent,
  type ReactNode,
} from "react";
import type { CustomerMasterEntity, RelatedNode } from "../api";
import { getCustomerMasterWorkspaceCopy } from "../customerMasterWorkspace";
import { t, tf, useLocale } from "../i18n";
import {
  buildCustomerEntityForest,
  flattenVisibleCustomerTree,
  type CustomerEntityTreeNode,
  type VisibleCustomerTreeItem,
} from "../customerMasterTree";
import "./CustomerMasterTree.css";

const NODE_POST = "node_post";

/** Inputs for the authorized Customer Master relationship workspace. */
export interface CustomerMasterTreeProps {
  entities: readonly CustomerMasterEntity[];
  loadRelated: (entityId: string) => Promise<RelatedNode[]>;
  onOpenPost: (postId: string) => void;
  initialSelectedEntityId?: string | null;
}

/** A source-backed related-post card shared by customer hierarchy and hint lists. */
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

function branchEntityIds(roots: readonly CustomerEntityTreeNode[]): Set<string> {
  const result = new Set<string>();
  const stack = [...roots];
  while (stack.length > 0) {
    const node = stack.pop()!;
    if (node.children.length > 0) result.add(node.entity.corporate_entity_id);
    stack.push(...node.children);
  }
  return result;
}

function indexCustomerTree(
  roots: readonly CustomerEntityTreeNode[],
): Map<string, CustomerEntityTreeNode> {
  const index = new Map<string, CustomerEntityTreeNode>();
  const stack = [...roots];
  while (stack.length > 0) {
    const node = stack.pop()!;
    index.set(node.entity.corporate_entity_id, node);
    stack.push(...node.children);
  }
  return index;
}

/**
 * Render the authorized Customer Master as a customer-centered three-pane workspace.
 *
 * The left pane preserves the cycle-safe WAI-ARIA hierarchy, the middle pane keeps one customer and
 * its visible parent/child relations in focus, and the right pane owns only source-backed evidence.
 */
export function CustomerMasterTree({
  entities,
  loadRelated,
  onOpenPost,
  initialSelectedEntityId = null,
}: CustomerMasterTreeProps) {
  const locale = useLocale();
  const copy = getCustomerMasterWorkspaceCopy(locale);
  const forest = useMemo(() => buildCustomerEntityForest(entities), [entities]);
  const allBranchIds = useMemo(() => branchEntityIds(forest), [forest]);
  const treeNodeById = useMemo(() => indexCustomerTree(forest), [forest]);
  const entityById = useMemo(
    () => new Map(entities.map((entity) => [entity.corporate_entity_id, entity])),
    [entities],
  );
  const resolvedInitialSelection =
    initialSelectedEntityId && entityById.has(initialSelectedEntityId)
      ? initialSelectedEntityId
      : null;
  const [expandedEntityIds, setExpandedEntityIds] = useState<Set<string>>(
    () => new Set(allBranchIds),
  );
  const [focusedEntityId, setFocusedEntityId] = useState<string | null>(
    () => forest[0]?.entity.corporate_entity_id ?? null,
  );
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(
    resolvedInitialSelection,
  );
  const [evidenceEntityId, setEvidenceEntityId] = useState<string | null>(null);
  const [relatedByEntity, setRelatedByEntity] = useState<Record<string, RelatedNode[]>>({});
  const [relatedLoadingId, setRelatedLoadingId] = useState<string | null>(null);
  const treeItemRefs = useRef(new Map<string, HTMLLIElement>());
  const relatedRequestSerial = useRef(0);

  useEffect(() => {
    setExpandedEntityIds(new Set(allBranchIds));
    setFocusedEntityId(forest[0]?.entity.corporate_entity_id ?? null);
    setSelectedEntityId(resolvedInitialSelection);
    setEvidenceEntityId(null);
    setRelatedByEntity({});
    setRelatedLoadingId(null);
    relatedRequestSerial.current += 1;
  }, [allBranchIds, forest, resolvedInitialSelection]);

  useEffect(
    () => () => {
      relatedRequestSerial.current += 1;
    },
    [],
  );

  const visibleItems = useMemo(
    () => flattenVisibleCustomerTree(forest, expandedEntityIds),
    [expandedEntityIds, forest],
  );
  const visibleById = useMemo(
    () => new Map(visibleItems.map((item) => [item.entityId, item])),
    [visibleItems],
  );

  useEffect(() => {
    if (focusedEntityId && visibleById.has(focusedEntityId)) return;
    setFocusedEntityId(visibleItems[0]?.entityId ?? null);
  }, [focusedEntityId, visibleById, visibleItems]);

  const focusTreeItem = useCallback((entityId: string) => {
    setFocusedEntityId(entityId);
    treeItemRefs.current.get(entityId)?.focus();
  }, []);

  const setBranchExpanded = useCallback((entityId: string, expanded: boolean) => {
    setExpandedEntityIds((current) => {
      const next = new Set(current);
      if (expanded) next.add(entityId);
      else next.delete(entityId);
      return next;
    });
  }, []);

  const activateEntity = useCallback(
    async (entityId: string) => {
      setSelectedEntityId(entityId);
      setFocusedEntityId(entityId);
      if (evidenceEntityId === entityId) {
        relatedRequestSerial.current += 1;
        setEvidenceEntityId(null);
        setRelatedLoadingId(null);
        return;
      }

      const requestSerial = ++relatedRequestSerial.current;
      setEvidenceEntityId(entityId);
      if (relatedByEntity[entityId]) {
        setRelatedLoadingId(null);
        return;
      }

      setRelatedLoadingId(entityId);
      try {
        const related = await loadRelated(entityId);
        if (requestSerial !== relatedRequestSerial.current) return;
        setRelatedByEntity((current) => ({ ...current, [entityId]: related }));
      } catch {
        if (requestSerial !== relatedRequestSerial.current) return;
        setRelatedByEntity((current) => ({ ...current, [entityId]: [] }));
      } finally {
        if (requestSerial === relatedRequestSerial.current) setRelatedLoadingId(null);
      }
    },
    [evidenceEntityId, loadRelated, relatedByEntity],
  );

  function handleTreeKeyDown(
    event: KeyboardEvent<HTMLLIElement>,
    item: VisibleCustomerTreeItem,
  ) {
    event.stopPropagation();
    const visibleIndex = visibleItems.findIndex((candidate) => candidate.entityId === item.entityId);
    switch (event.key) {
      case "ArrowDown": {
        event.preventDefault();
        const next = visibleItems[Math.min(visibleIndex + 1, visibleItems.length - 1)];
        if (next) focusTreeItem(next.entityId);
        return;
      }
      case "ArrowUp": {
        event.preventDefault();
        const previous = visibleItems[Math.max(visibleIndex - 1, 0)];
        if (previous) focusTreeItem(previous.entityId);
        return;
      }
      case "Home": {
        event.preventDefault();
        if (visibleItems[0]) focusTreeItem(visibleItems[0].entityId);
        return;
      }
      case "End": {
        event.preventDefault();
        const last = visibleItems[visibleItems.length - 1];
        if (last) focusTreeItem(last.entityId);
        return;
      }
      case "ArrowRight": {
        if (item.node.children.length === 0) return;
        event.preventDefault();
        if (!expandedEntityIds.has(item.entityId)) {
          setBranchExpanded(item.entityId, true);
        } else {
          focusTreeItem(item.node.children[0].entity.corporate_entity_id);
        }
        return;
      }
      case "ArrowLeft": {
        event.preventDefault();
        if (item.node.children.length > 0 && expandedEntityIds.has(item.entityId)) {
          setBranchExpanded(item.entityId, false);
        } else if (item.parentEntityId) {
          focusTreeItem(item.parentEntityId);
        }
        return;
      }
      case "Enter":
      case " ": {
        event.preventDefault();
        void activateEntity(item.entityId);
        return;
      }
      default:
        return;
    }
  }

  function renderNodes(nodes: readonly CustomerEntityTreeNode[]): ReactNode {
    return nodes.map((node) => {
      const entity = node.entity;
      const entityId = entity.corporate_entity_id;
      const item = visibleById.get(entityId);
      if (!item) return null;
      const isBranch = node.children.length > 0;
      const isExpanded = expandedEntityIds.has(entityId);
      const isSelected = selectedEntityId === entityId;
      const isEvidenceOpen = evidenceEntityId === entityId;
      const accessibleLabel = [
        entity.entity_name,
        `${entity.corporate_entity_code} · ${entity.entity_level_label}`,
        node.hierarchyIssue ? t("unresolved") : null,
      ]
        .filter(Boolean)
        .join(", ");
      return (
        <li
          key={entityId}
          ref={(element: HTMLLIElement | null) => {
            if (element) treeItemRefs.current.set(entityId, element);
            else treeItemRefs.current.delete(entityId);
          }}
          role="treeitem"
          className="customer-tree-node"
          tabIndex={focusedEntityId === entityId ? 0 : -1}
          aria-label={accessibleLabel}
          aria-level={item.level}
          aria-posinset={item.positionInSet}
          aria-setsize={item.setSize}
          aria-expanded={isBranch ? isExpanded : undefined}
          aria-selected={isSelected}
          aria-controls={isEvidenceOpen ? `customer-evidence-${entityId}` : undefined}
          data-hierarchy-issue={node.hierarchyIssue ?? undefined}
          onFocus={(event: FocusEvent<HTMLLIElement>) => {
            if (event.currentTarget === event.target) setFocusedEntityId(entityId);
          }}
          onKeyDown={(event: KeyboardEvent<HTMLLIElement>) => handleTreeKeyDown(event, item)}
          onClick={(event: MouseEvent<HTMLLIElement>) => {
            event.stopPropagation();
            const target = event.target as HTMLElement;
            if (target !== event.currentTarget) {
              const row = target.closest("[data-customer-tree-row]");
              if (!row || row.parentElement !== event.currentTarget) return;
            }
            if (isBranch && target.closest("[data-customer-branch-toggle]")) {
              setBranchExpanded(entityId, !isExpanded);
              return;
            }
            void activateEntity(entityId);
          }}
        >
          <div className="customer-entity-button" data-customer-tree-row>
            <span
              className={
                isBranch ? "customer-tree-branch-indicator" : "customer-tree-branch-spacer"
              }
              data-customer-branch-toggle={isBranch ? "true" : undefined}
              aria-hidden="true"
            >
              {isBranch ? (isExpanded ? "▾" : "▸") : ""}
            </span>
            <span className="customer-tree-label">
              <strong>{entity.entity_name}</strong>
              <span>
                {entity.corporate_entity_code} · {entity.entity_level_label}
              </span>
              {node.hierarchyIssue ? (
                <span className="customer-tree-unresolved">{t("unresolved")}</span>
              ) : null}
            </span>
          </div>
          {isBranch && isExpanded ? (
            <ul role="group" className="customer-master-tree-group">
              {renderNodes(node.children)}
            </ul>
          ) : null}
        </li>
      );
    });
  }

  const selectedEntity = selectedEntityId ? entityById.get(selectedEntityId) : undefined;
  const selectedNode = selectedEntityId ? treeNodeById.get(selectedEntityId) : undefined;
  const selectedParent = selectedEntity?.parent_entity_id
    ? entityById.get(selectedEntity.parent_entity_id)
    : undefined;
  const selectedChildren = selectedNode?.children ?? [];
  const evidenceEntity = evidenceEntityId ? entityById.get(evidenceEntityId) : undefined;
  const relatedPosts = evidenceEntityId
    ? (relatedByEntity[evidenceEntityId] ?? []).filter(
        (related) => related.node_type_code === NODE_POST,
      )
    : [];

  function renderRelationshipButton(
    entity: CustomerMasterEntity,
    relationshipLabel: string,
  ): ReactNode {
    return (
      <button
        type="button"
        className="customer-master-relationship-card"
        aria-label={`${copy.relationshipAction}: ${entity.entity_name}`}
        onClick={() => void activateEntity(entity.corporate_entity_id)}
      >
        <span className="customer-master-relationship-kind">{relationshipLabel}</span>
        <strong>{entity.entity_name}</strong>
        <span>
          {entity.corporate_entity_code} · {entity.entity_level_label}
        </span>
      </button>
    );
  }

  return (
    <div className="customer-master-relationship-workspace">
      <section
        className="customer-master-workspace-pane customer-master-hierarchy-pane"
        aria-labelledby="customer-master-hierarchy-heading"
      >
        <header className="customer-master-pane-header">
          <p>{copy.hierarchyKicker}</p>
          <h3 id="customer-master-hierarchy-heading">{copy.hierarchyTitle}</h3>
          <span>{copy.hierarchyHelp}</span>
        </header>
        <ul
          role="tree"
          className="customer-master-list customer-master-tree customer-master-tree-widget"
          aria-label={t("Customer entities available to this account.")}
        >
          {renderNodes(forest)}
        </ul>
      </section>

      <section
        className="customer-master-workspace-pane customer-master-focus-pane"
        aria-labelledby="customer-master-focus-heading"
      >
        <header className="customer-master-pane-header">
          <p>{copy.focusKicker}</p>
          <h3 id="customer-master-focus-heading">{copy.focusTitle}</h3>
          <span>{copy.focusHelp}</span>
        </header>
        {selectedEntity && selectedNode ? (
          <div className="customer-master-focus-content">
            <div className="customer-master-selected-summary">
              <span className="customer-master-selected-label">{copy.selectedCustomer}</span>
              <h4>{selectedEntity.entity_name}</h4>
              <p>
                {selectedEntity.corporate_entity_code} · {selectedEntity.entity_level_label}
              </p>
              <span
                className={
                  selectedNode.hierarchyIssue
                    ? "customer-master-status-badge customer-master-status-unresolved"
                    : "customer-master-status-badge customer-master-status-verified"
                }
              >
                {selectedNode.hierarchyIssue ? t("unresolved") : copy.verifiedMaster}
              </span>
            </div>

            {selectedNode.hierarchyIssue ? (
              <p className="customer-master-unresolved-callout">{copy.unresolvedRelation}</p>
            ) : null}

            <div className="customer-master-relationship-section">
              <h4>{copy.parentRelationship}</h4>
              {selectedParent
                ? renderRelationshipButton(selectedParent, copy.parentRelationship)
                : <p className="customer-master-empty-relation">{copy.noParent}</p>}
            </div>

            <div className="customer-master-relationship-section">
              <h4>{copy.childRelationships}</h4>
              {selectedChildren.length > 0 ? (
                <div className="customer-master-relationship-list">
                  {selectedChildren.map((child) => (
                    <div key={child.entity.corporate_entity_id}>
                      {renderRelationshipButton(child.entity, copy.childRelationships)}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="customer-master-empty-relation">{copy.noChildren}</p>
              )}
            </div>

            <button
              type="button"
              className="customer-master-evidence-action"
              aria-expanded={evidenceEntityId === selectedEntity.corporate_entity_id}
              aria-controls={
                evidenceEntityId === selectedEntity.corporate_entity_id
                  ? `customer-evidence-${selectedEntity.corporate_entity_id}`
                  : undefined
              }
              onClick={() => void activateEntity(selectedEntity.corporate_entity_id)}
            >
              {evidenceEntityId === selectedEntity.corporate_entity_id
                ? copy.closeEvidence
                : copy.openEvidence}
            </button>
          </div>
        ) : (
          <p className="customer-master-workspace-placeholder">{copy.selectCustomerPrompt}</p>
        )}
      </section>

      <aside
        className="customer-master-workspace-pane customer-master-evidence-pane"
        aria-labelledby="customer-master-evidence-heading"
      >
        <header className="customer-master-pane-header">
          <p>{copy.evidenceKicker}</p>
          <h3 id="customer-master-evidence-heading">{copy.evidenceTitle}</h3>
          <span>{copy.evidenceHelp}</span>
        </header>
        {!selectedEntity ? (
          <p className="customer-master-workspace-placeholder">{copy.selectEvidencePrompt}</p>
        ) : null}
        {selectedEntity && evidenceEntityId !== selectedEntity.corporate_entity_id ? (
          <button
            type="button"
            className="customer-master-evidence-action customer-master-evidence-action-secondary"
            onClick={() => void activateEntity(selectedEntity.corporate_entity_id)}
          >
            {copy.openEvidence}
          </button>
        ) : null}
        {evidenceEntityId && evidenceEntity ? (
          <section
            id={`customer-evidence-${evidenceEntityId}`}
            className="customer-related-posts customer-tree-evidence"
            aria-label={`${t("Related posts")}: ${evidenceEntity.entity_name}`}
          >
            <div className="customer-master-evidence-context">
              <div>
                <strong>{evidenceEntity.entity_name}</strong>
                <span>{copy.evidenceNextAction}</span>
              </div>
              <button
                type="button"
                className="customer-master-evidence-close"
                aria-label={t("Close evidence panel")}
                onClick={() => void activateEntity(evidenceEntityId)}
              >
                ×
              </button>
            </div>
            {relatedLoadingId === evidenceEntityId ? (
              <p>{t("Loading related posts...")}</p>
            ) : null}
            {relatedLoadingId !== evidenceEntityId && relatedPosts.length === 0 ? (
              <p className="popup-placeholder">{t("No linked posts yet.")}</p>
            ) : null}
            {relatedPosts.length > 0 ? (
              <ul>
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
          </section>
        ) : null}
      </aside>
    </div>
  );
}
