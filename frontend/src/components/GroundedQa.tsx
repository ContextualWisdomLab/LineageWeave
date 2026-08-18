import { useState, type FormEvent } from "react";

export type GroundedQaAnswer = {
  question: string;
  slot_code: string | null;
  values: string[];
  grounded: boolean;
  empty_next_action: string | null;
};

export type GroundedQaProps = {
  onAsk: (question: string) => Promise<GroundedQaAnswer>;
};

export function GroundedQa({ onAsk }: GroundedQaProps) {
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
    <section className="popup-section" aria-label="이 사건 lineage에 묻기">
      <h3>이 사건 lineage에 묻기</h3>
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
          {pending ? "Querying..." : "Ask"}
        </button>
      </form>
      {error ? <p className="error">{error}</p> : null}
      {answer && answer.grounded ? (
        <p role="status" aria-label="Grounded lineage answer">
          {answer.values.join(" · ")}
        </p>
      ) : null}
      {answer && !answer.grounded ? (
        <p className="popup-placeholder" role="status" aria-label="Ungrounded lineage answer">
          {answer.empty_next_action}
        </p>
      ) : null}
    </section>
  );
}
