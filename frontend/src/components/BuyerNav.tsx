import { t } from "../i18n";
import type { ReactNode } from "react";

export type BuyerDestination = "board" | "customers" | "calendar" | "ask" | "admin";

export type BuyerNavProps = {
  destination: BuyerDestination;
  onChange: (destination: BuyerDestination) => void;
  tools?: ReactNode;
  drawer?: boolean;
  id?: string;
};

const ITEMS: BuyerDestination[] = ["board", "customers", "calendar", "ask", "admin"];

const LABELS: Record<BuyerDestination, string> = {
  board: "Board",
  customers: "Customer master",
  calendar: "Calendar",
  ask: "Ask Agent",
  admin: "Admin",
};

export function BuyerNav({ destination, onChange, tools, drawer = false, id }: BuyerNavProps) {
  return (
    <nav
      id={id}
      className={`buyer-gnb${drawer ? " buyer-gnb-drawer" : ""}`}
      aria-label={t("Buyer navigation")}
    >
      {ITEMS.map((id) => (
        <button
          key={id}
          type="button"
          className="buyer-gnb-item"
          aria-current={destination === id ? "page" : undefined}
          onClick={() => onChange(id)}
        >
          {t(LABELS[id])}
        </button>
      ))}
      {tools ? <div className="buyer-gnb-tools">{tools}</div> : null}
    </nav>
  );
}
