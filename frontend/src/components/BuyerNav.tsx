export type BuyerDestination = "board" | "customers" | "ask";

export type BuyerNavProps = {
  destination: BuyerDestination;
  onChange: (destination: BuyerDestination) => void;
};

const ITEMS: { id: BuyerDestination; label: string }[] = [
  { id: "board", label: "게시판" },
  { id: "customers", label: "고객 마스터" },
  { id: "ask", label: "Ask Cubee" },
];

export function BuyerNav({ destination, onChange }: BuyerNavProps) {
  return (
    <nav className="buyer-gnb" aria-label="Buyer">
      {ITEMS.map((item) => (
        <button
          key={item.id}
          type="button"
          className="buyer-gnb-item"
          aria-current={destination === item.id ? "page" : undefined}
          onClick={() => onChange(item.id)}
        >
          {item.label}
        </button>
      ))}
    </nav>
  );
}
