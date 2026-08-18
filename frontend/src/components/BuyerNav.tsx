export type BuyerDestination = "board" | "customers" | "calendar" | "ask";

export type BuyerNavProps = {
  destination: BuyerDestination;
  onChange: (destination: BuyerDestination) => void;
};

const LABELS: Record<BuyerDestination, string> = {
  board: "게시판",
  customers: "고객 마스터",
  calendar: "달력",
  ask: "Ask Agent",
};

const ITEMS: BuyerDestination[] = ["board", "customers", "calendar", "ask"];

export function BuyerNav({ destination, onChange }: BuyerNavProps) {
  return (
    <nav className="buyer-gnb" aria-label="Buyer">
      {ITEMS.map((id) => (
        <button
          key={id}
          type="button"
          className="buyer-gnb-item"
          aria-current={destination === id ? "page" : undefined}
          onClick={() => onChange(id)}
        >
          {LABELS[id]}
        </button>
      ))}
    </nav>
  );
}
