import { t } from "../i18n";

export type WorkspaceDestination = "dashboard" | "board" | "customers" | "calendar" | "ask" | "admin";

export type WorkspaceNavProps = {
  destination: WorkspaceDestination;
  onChange: (destination: WorkspaceDestination) => void;
  showAdmin?: boolean;
  drawer?: boolean;
  id?: string;
};

const ITEMS: WorkspaceDestination[] = ["dashboard", "board", "customers", "calendar", "ask", "admin"];

const LABELS: Record<WorkspaceDestination, string> = {
  dashboard: "Dashboard",
  board: "Board",
  customers: "Customer master",
  calendar: "Calendar",
  ask: "Ask Agent",
  admin: "Admin",
};

export function WorkspaceNav({ destination, onChange, showAdmin = true, drawer = false, id }: WorkspaceNavProps) {
  const items = showAdmin ? ITEMS : ITEMS.filter((item) => item !== "admin");
  return (
    <nav
      id={id}
      className={`workspace-gnb${drawer ? " workspace-gnb-drawer" : ""}`}
      aria-label={t("Workspace navigation")}
    >
      {items.map((id) => (
        <button
          key={id}
          type="button"
          className="workspace-gnb-item"
          aria-current={destination === id ? "page" : undefined}
          onClick={() => onChange(id)}
        >
          {t(LABELS[id])}
        </button>
      ))}
    </nav>
  );
}
