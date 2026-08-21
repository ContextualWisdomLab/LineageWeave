import { useState } from "react";
import { t } from "../i18n";
import { updateTenantConfig, type CurrentUser } from "../api";
import type { WorkspaceDestination } from "./WorkspaceNav";
import "./AdminPanel.css";

export type AdminBoardTool = "advanced" | "lineage" | "rankings" | "analysis" | "reports";

type AdminSection =
  | "overview"
  | "post-operations"
  | "lineage"
  | "rankings"
  | "analysis"
  | "reports"
  | "settings"
  | "scope";

type AdminLnbItem = {
  id: AdminSection;
  label: string;
  description: string;
  destination?: WorkspaceDestination;
  boardTool?: AdminBoardTool;
};

type AdminLnbGroup = {
  label: string;
  items: AdminLnbItem[];
};

const ADMIN_LNB_GROUPS: AdminLnbGroup[] = [
  {
    label: "Admin overview",
    items: [
      { id: "overview", label: "Control center", description: "Admin operations and workspace handoffs" },
    ],
  },
  {
    label: "Content operations",
    items: [
      { id: "post-operations", label: "Post evidence operations", description: "Keymen, relations, evaluation, tickets", boardTool: "advanced" },
      { id: "overview", label: "Board & posts", description: "Search authorized posts", destination: "board" },
      { id: "overview", label: "Customer master", description: "Entities, people, and relationship network", destination: "customers" },
      { id: "overview", label: "Calendar & commitments", description: "Upcoming commitments and CalDAV events", destination: "calendar" },
    ],
  },
  {
    label: "Lineage & analysis",
    items: [
      { id: "lineage", label: "Lineage rebuild", description: "Reconstruct authorized lineage", boardTool: "lineage" },
      { id: "rankings", label: "Rankings", description: "Reader-facing ranking evidence", boardTool: "rankings" },
      { id: "analysis", label: "Analysis runs", description: "Cutoff, start, and run evidence", boardTool: "analysis" },
      { id: "reports", label: "Period reports", description: "Compare and rebuild period reports", boardTool: "reports" },
    ],
  },
  {
    label: "Workspace",
    items: [
      { id: "settings", label: "Tenant settings", description: "Branding and tenant configuration" },
      { id: "scope", label: "Account scope", description: "Permission and authorized entity scope" },
    ],
  },
];

type AdminOperation = {
  label: string;
  route: string;
  permission: string;
  note: string;
};

const ADMIN_OPERATIONS: AdminOperation[] = [
  { label: "Verify post relations", route: "POST /api/posts/{post_id}/verify-relations", permission: "post_admin", note: "Validate extracted ontology relationships against source evidence." },
  { label: "Extract Keymen", route: "POST /api/posts/{post_id}/extract-keymen", permission: "post_admin", note: "Run the orchestrated Keyman extraction for a selected post." },
  { label: "Evaluate post", route: "POST /api/posts/{post_id}/evaluate", permission: "post_admin", note: "Create the evaluation evidence for a selected post." },
  { label: "Manage tickets", route: "PATCH /api/tickets/{issue_ticket_id}", permission: "post_admin", note: "Update the status of an issue ticket opened from a post." },
  { label: "Derive commitment", route: "POST /api/posts/{post_id}/derive-commitment", permission: "post_admin", note: "Derive a commitment from source-grounded post evidence." },
  { label: "Rebuild lineage", route: "POST /api/lineage/rebuild", permission: "post_admin", note: "Reconstruct the authorized lineage projection." },
  { label: "Create analysis run", route: "POST /api/analysis-runs", permission: "post_read", note: "Create a pending cutoff lineage for an authorized account." },
  { label: "Start analysis run", route: "POST /api/analysis-runs/{id}/start", permission: "post_read", note: "Start the persisted run from its pending cutoff lineage." },
  { label: "Rebuild period report", route: "POST /api/reports/{grouping_kind}/{period_code}/rebuild", permission: "post_admin", note: "Rebuild a period report from the persisted report inputs." },
  { label: "Update tenant settings", route: "PATCH /api/settings", permission: "post_admin", note: "Persist the tenant brand name used by the workspace shell." },
];

export type AdminPanelProps = {
  currentBrandName: string;
  onBrandNameChange: (newName: string) => void;
  accessToken: string;
  currentUser?: CurrentUser | null;
  onNavigate: (destination: WorkspaceDestination) => void;
  onOpenBoardTool: (tool: AdminBoardTool) => void;
};

function AdminLnb({ activeSection, onSelect }: { activeSection: AdminSection; onSelect: (item: AdminLnbItem) => void }) {
  return (
    <nav className="admin-lnb" aria-label={t("Admin navigation")}>
      {ADMIN_LNB_GROUPS.map((group) => (
        <div className="admin-lnb-group" key={group.label}>
          <p className="admin-lnb-group-label">{t(group.label)}</p>
          <div className="admin-lnb-items">
            {group.items.map((item) => {
              const isLocal = !item.destination && !item.boardTool;
              const active = isLocal && activeSection === item.id;
              return (
                <button
                  key={`${group.label}-${item.label}`}
                  type="button"
                  className="admin-lnb-item"
                  aria-current={active ? "page" : undefined}
                  onClick={() => onSelect(item)}
                >
                  <span className="admin-lnb-item-label">{t(item.label)}</span>
                  <span className="admin-lnb-item-description">{t(item.description)}</span>
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </nav>
  );
}

function OperationIndex({ onOpenBoardTool }: { onOpenBoardTool: (tool: AdminBoardTool) => void }) {
  return (
    <section className="admin-operation-index" aria-labelledby="admin-operation-index-title">
      <div className="admin-section-heading">
        <div>
          <p className="admin-eyebrow">{t("Endpoint catalog")}</p>
          <h3 id="admin-operation-index-title">{t("Admin endpoint catalog")}</h3>
        </div>
        <span className="admin-count-label">{ADMIN_OPERATIONS.length} {t("routes")}</span>
      </div>
      <p className="admin-section-intro">{t("Routes are shown with the permission gate enforced by the backend.")}</p>
      <div className="admin-operation-list">
        {ADMIN_OPERATIONS.map((operation) => (
          <div className="admin-operation-row" key={operation.route}>
            <div>
              <strong>{t(operation.label)}</strong>
              <p>{t(operation.note)}</p>
            </div>
            <div className="admin-operation-meta">
              <code>{operation.route}</code>
              <span className="admin-permission-chip">{operation.permission}</span>
            </div>
          </div>
        ))}
      </div>
      <button type="button" className="btn-secondary" onClick={() => onOpenBoardTool("advanced")}>
        {t("Open post operations")}
      </button>
    </section>
  );
}

function AdminWorkspaceScope({ currentUser }: { currentUser?: CurrentUser | null }) {
  const affiliations = currentUser?.account_affiliations ?? [];
  return (
    <section className="admin-content-section" aria-labelledby="admin-scope-title">
      <p className="admin-eyebrow">{t("Workspace")}</p>
      <h2 id="admin-scope-title">{t("Account scope")}</h2>
      <p className="admin-section-intro">{t("These values come from the authenticated account and are not editable here.")}</p>
      <dl className="admin-scope-list">
        <div><dt>{t("Account")}</dt><dd>{currentUser?.display_name ?? t("Loading...")}</dd></div>
        <div><dt>{t("Permissions")}</dt><dd><code>{currentUser?.permission_codes.join(", ") || t("Not available")}</code></dd></div>
        <div><dt>{t("Authorized entities")}</dt><dd>{affiliations.length ? affiliations.map((item) => `${item.corporate_entity_code}${item.process_unit_code ? ` / ${item.process_unit_code}` : ""}`).join(", ") : t("Not available")}</dd></div>
      </dl>
    </section>
  );
}

function AdminBoardHandoff({ title, description, tool, onOpenBoardTool }: { title: string; description: string; tool: AdminBoardTool; onOpenBoardTool: (tool: AdminBoardTool) => void }) {
  return (
    <section className="admin-content-section" aria-labelledby="admin-handoff-title">
      <p className="admin-eyebrow">{t("Existing workspace surface")}</p>
      <h2 id="admin-handoff-title">{t(title)}</h2>
      <p className="admin-section-intro">{t(description)}</p>
      <div className="admin-handoff">
        <div>
          <strong>{t("Board advanced review")}</strong>
          <p>{t("The existing Board owns the selected post and its provenance, so this action opens there instead of duplicating the workflow.")}</p>
        </div>
        <button type="button" className="btn-primary" onClick={() => onOpenBoardTool(tool)}>
          {t("Open in Board")}
        </button>
      </div>
    </section>
  );
}

export function AdminPanel({ currentBrandName, onBrandNameChange, accessToken, currentUser, onNavigate, onOpenBoardTool }: AdminPanelProps) {
  const [activeSection, setActiveSection] = useState<AdminSection>("overview");
  const [draftName, setDraftName] = useState(currentBrandName);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (draftName.trim()) {
      setSaving(true);
      setError(null);
      try {
        const config = await updateTenantConfig(accessToken, draftName.trim());
        onBrandNameChange(config.brandName);
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
      } catch (err: any) {
        setError(err.message || "Failed to update settings");
      } finally {
        setSaving(false);
      }
    }
  }

  function handleSelect(item: AdminLnbItem) {
    if (item.destination) {
      onNavigate(item.destination);
      return;
    }
    if (item.boardTool) {
      onOpenBoardTool(item.boardTool);
      return;
    }
    setActiveSection(item.id);
  }

  const renderContent = () => {
    switch (activeSection) {
      case "post-operations":
        return <AdminBoardHandoff title="Post evidence operations" description="These operations require a selected post so every write remains attached to source evidence and provenance." tool="advanced" onOpenBoardTool={onOpenBoardTool} />;
      case "lineage":
        return <AdminBoardHandoff title="Lineage rebuild" description="Rebuild is available from the Board advanced review surface and uses the authorized account scope." tool="lineage" onOpenBoardTool={onOpenBoardTool} />;
      case "rankings":
        return <AdminBoardHandoff title="Rankings" description="Rankings remain reader-facing evidence, while the admin LNB makes the existing review surface discoverable." tool="rankings" onOpenBoardTool={onOpenBoardTool} />;
      case "analysis":
        return <AdminBoardHandoff title="Analysis runs" description="Create, start, and inspect cutoff-aware analysis runs from the existing Board review surface." tool="analysis" onOpenBoardTool={onOpenBoardTool} />;
      case "reports":
        return <AdminBoardHandoff title="Period reports" description="Compare period reports and use the rebuild control when the authenticated account has post_admin." tool="reports" onOpenBoardTool={onOpenBoardTool} />;
      case "settings":
        return (
          <section className="admin-content-section" aria-labelledby="admin-settings-title">
            <p className="admin-eyebrow">{t("Workspace")}</p>
            <h2 id="admin-settings-title">{t("Tenant settings")}</h2>
            <form onSubmit={handleSave} className="admin-form">
              <label htmlFor="brandNameInput">
                <strong>* {t("Tenant brand name")}</strong>
                <span className="admin-field-help">{t("This name is used in the authenticated workspace shell.")}</span>
              </label>
              <input
                id="brandNameInput"
                type="text"
                value={draftName}
                onChange={(e) => setDraftName(e.target.value)}
                aria-label={t("Tenant brand name")}
                disabled={saving}
              />
              <div className="admin-form-actions">
                <button type="submit" className="btn-primary" disabled={saving || !draftName.trim() || draftName === currentBrandName}>
                  {saving ? t("Saving...") : t("Save settings")}
                </button>
                {saved && <span className="admin-success" role="status">{t("Settings saved!")}</span>}
                {error && <span className="admin-error" role="alert">{t(error)}</span>}
              </div>
            </form>
          </section>
        );
      case "scope":
        return <AdminWorkspaceScope currentUser={currentUser} />;
      case "overview":
      default:
        return (
          <section className="admin-overview" aria-labelledby="admin-overview-title">
            <div className="admin-panel-header">
              <div>
                <p className="admin-eyebrow">{t("Administrator mode")}</p>
                <h2 id="admin-overview-title">{t("Admin control center")}</h2>
                <p>{t("Find the right operational surface without losing the source and permission context.")}</p>
              </div>
              <div className="admin-context-status">
                <span className="admin-status-dot" aria-hidden="true" />
                <span>{t("post_admin enabled")}</span>
              </div>
            </div>
            <div className="admin-quick-links" aria-label={t("Workspace shortcuts")}>
              <button type="button" className="admin-quick-link" onClick={() => onNavigate("board")}><strong>{t("Board & posts")}</strong><span>{t("Search authorized posts")}</span></button>
              <button type="button" className="admin-quick-link" onClick={() => onNavigate("customers")}><strong>{t("Customer master")}</strong><span>{t("Entities and relationship network")}</span></button>
              <button type="button" className="admin-quick-link" onClick={() => onNavigate("calendar")}><strong>{t("Calendar & commitments")}</strong><span>{t("Upcoming commitments")}</span></button>
            </div>
            <OperationIndex onOpenBoardTool={onOpenBoardTool} />
          </section>
        );
    }
  };

  return (
    <div className="admin-workspace">
      <AdminLnb activeSection={activeSection} onSelect={handleSelect} />
      <div className="admin-content">{renderContent()}</div>
    </div>
  );
}
