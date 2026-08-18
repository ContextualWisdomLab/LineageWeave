import { useState, type FormEvent } from "react";

export type GroundedQaAnswer = {
  question: string;
  slot_code: string | null;
  values: string[];
  grounded: boolean;
  empty_next_action: string | null;
  who?: string[];
  what_happened?: string[];
  chronology?: { occurred_at: string; label: string }[];
};

export type GroundedQaProps = {
  heading?: string;
  onAsk: (question: string) => Promise<GroundedQaAnswer>;
};

export function GroundedQa({ heading = "Ask Cubee", onAsk }: GroundedQaProps) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<GroundedQaAnswer | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const next = question.trim();
    if (!next) {
      return;
    }
    setPending(true);
    setError(null);
    try {
      setAnswer(await onAsk(next));
    } catch (err) {
      setError(String(err));
      setAnswer(null);
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="popup-section" aria-label={heading}>
      <h3>{heading}</h3>
      <form className="chat-input-row" onSubmit={handleSubmit}>
        <label>
          질문
          <input
            aria-label="Lineage question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="누가 관련되었나요?"
          />
        </label>
        <button type="submit" disabled={pending}>
          {pending ? "Querying..." : "묻기"}
        </button>
      </form>
      {error ? <p className="error">{error}</p> : null}
      {answer && answer.grounded ? (
        <div role="status" aria-label="Grounded lineage answer">
          <p>{answer.values.join(" · ")}</p>
          {answer.who && answer.who.length > 0 ? <p>누가 · {answer.who.join(" · ")}</p> : null}
          {answer.what_happened && answer.what_happened.length > 0 ? (
            <p>무엇을 · {answer.what_happened.join(" · ")}</p>
          ) : null}
          {answer.chronology && answer.chronology.length > 0 ? (
            <ol>
              {answer.chronology.map((row) => (
                <li key={`${row.occurred_at}:${row.label}`}>
                  {row.occurred_at} · {row.label}
                </li>
              ))}
            </ol>
          ) : null}
        </div>
      ) : null}
      {answer && !answer.grounded ? (
        <p className="popup-placeholder" role="status" aria-label="Ungrounded lineage answer">
          {answer.empty_next_action}
        </p>
      ) : null}
    </section>
  );
}
