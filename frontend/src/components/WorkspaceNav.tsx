import type { ReactNode } from "react";
import { ANALYST_GNB_ITEMS, type AnalystGnbId } from "../gnbChrome";
import { t } from "../i18n";

export type WorkspaceDestination = AnalystGnbId | "admin";

export type WorkspaceNavProps = {
  destination: WorkspaceDestination;
  onChange: (destination: WorkspaceDestination) => void;
  tools?: ReactNode;
};

export function WorkspaceNav({ destination, onChange, tools }: WorkspaceNavProps) {
  return (
    <nav className="workspace-gnb" aria-label={t("Workspace navigation")}>
      {ANALYST_GNB_ITEMS.map((item) => (
        <button
          key={item.id}
          type="button"
          className="workspace-gnb-item"
          aria-current={destination === item.id ? "page" : undefined}
          onClick={() => onChange(item.id)}
        >
          {t(item.labelKey)}
        </button>
      ))}
      {tools ? <div className="workspace-gnb-tools">{tools}</div> : null}
    </nav>
  );
}
