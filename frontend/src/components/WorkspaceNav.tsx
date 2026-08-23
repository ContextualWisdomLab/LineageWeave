import { t } from "../i18n";
import type { ReactNode } from "react";

export type WorkspaceDestination = "board" | "customers" | "calendar" | "ask" | "admin";

export type WorkspaceNavProps = {
  destination: WorkspaceDestination;
  onChange: (destination: WorkspaceDestination) => void;
  tools?: ReactNode;
};

const ITEMS: WorkspaceDestination[] = ["board", "customers", "calendar", "ask", "admin"];

const LABELS: Record<WorkspaceDestination, string> = {
  board: "Board",
  customers: "Customer master",
  calendar: "Calendar",
  ask: "Ask Agent",
  admin: "Admin",
};

export function WorkspaceNav({ destination, onChange, tools }: WorkspaceNavProps) {
  return (
    <nav className="workspace-gnb" aria-label={t("Workspace navigation")}>
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
      {tools ? <div className="workspace-gnb-tools">{tools}</div> : null}
    </nav>
  );
}
