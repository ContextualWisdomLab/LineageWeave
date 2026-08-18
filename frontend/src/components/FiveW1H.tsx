export type FiveW1HSlot = {
  slot_code: string;
  slot_label: string;
  values: string[];
  empty_next_action: string | null;
};

export type FiveW1HProps = {
  slots: FiveW1HSlot[] | null;
  error?: string | null;
};

export function FiveW1H({ slots, error }: FiveW1HProps) {
  return (
    <section className="popup-section" aria-label="5W1H">
      <h3>5W1H</h3>
      {error ? <p className="error">{error}</p> : null}
      {slots === null && !error ? <p>Loading 5W1H...</p> : null}
      {slots ? (
        <dl className="five-w1h">
          {slots.map((slot) => (
            <div key={slot.slot_code} className="five-w1h-slot">
              <dt>{slot.slot_label}</dt>
              <dd>
                {slot.values.length > 0 ? (
                  slot.values.join(" · ")
                ) : (
                  <span className="popup-placeholder">{slot.empty_next_action}</span>
                )}
              </dd>
            </div>
          ))}
        </dl>
      ) : null}
    </section>
  );
}
