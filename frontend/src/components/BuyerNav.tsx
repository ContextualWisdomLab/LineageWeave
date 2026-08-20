import { t } from "../i18n";
import type { ReactNode } from "react";

export type BuyerDestination = "board" | "customers" | "calendar" | "ask";

export type BuyerNavProps = {
  destination: BuyerDestination;
  onChange: (destination: BuyerDestination) => void;
  tools?: ReactNode;
};

const ITEMS: BuyerDestination[] = ["board", "customers", "calendar", "ask"];

const LABELS: Record<BuyerDestination, string> = {
  board: "Board",
  customers: "Customer master",
  calendar: "Calendar",
  ask: "Ask Agent",
};

export function BuyerNav({ destination, onChange, tools }: BuyerNavProps) {
  return (
    <nav className="buyer-gnb" aria-label={t("Buyer navigation")}>
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
