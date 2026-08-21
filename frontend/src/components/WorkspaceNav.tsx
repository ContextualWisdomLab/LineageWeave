import { t } from "../i18n";

export type WorkspaceDestination = "board" | "customers" | "calendar" | "ask" | "admin";

export type WorkspaceNavProps = {
  destination: WorkspaceDestination;
  onChange: (destination: WorkspaceDestination) => void;
  drawer?: boolean;
  id?: string;
};

const ITEMS: WorkspaceDestination[] = ["board", "customers", "calendar", "ask", "admin"];

const LABELS: Record<WorkspaceDestination, string> = {
  board: "Board",
  customers: "Customer master",
  calendar: "Calendar",
  ask: "Ask Agent",
  admin: "Admin",
};

export function WorkspaceNav({ destination, onChange, drawer = false, id }: WorkspaceNavProps) {
  return (
    <nav
      id={id}
      className={`workspace-gnb${drawer ? " workspace-gnb-drawer" : ""}`}
      aria-label={t("Workspace navigation")}
    >
      {ITEMS.map((id) => (
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
