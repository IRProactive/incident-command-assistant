import { useState } from "react";
import { askGuidance } from "../api.js";

export default function AskPanel() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [sources, setSources] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function handleAsk(e) {
    e.preventDefault();
    if (!question.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const result = await askGuidance(question.trim());
      setAnswer(result.answer);
      setSources(result.sources || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      {error && <div className="error-banner">{error}</div>}
      <form className="ask-row" onSubmit={handleAsk}>
        <input
          type="text"
          placeholder="e.g. What should we do to contain and eradicate an incident?"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <button type="submit" className="btn" disabled={busy || !question.trim()}>
          {busy ? "Asking…" : "Ask"}
        </button>
      </form>

      {answer && <div className="answer-block">{answer}</div>}

      {sources.length > 0 && (
        <ul className="source-list">
          {sources.map((s, i) => (
            <li key={i} className="source-row">
              <span className={`kind-badge ${s.kind}`}>{s.kind === "org_doc" ? "your plan" : "standard"}</span>
              <span title={s.source}>{s.source.length > 90 ? s.source.slice(0, 90) + "…" : s.source}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
