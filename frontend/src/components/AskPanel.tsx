import { useState } from "react";
import { api } from "../api";
import type { AskResponse, Chunking, Config, Retrieval, Source } from "../types";

const EXAMPLES = [
  "How much notice is needed to increase the rent?",
  "Within how many days must the deposit be returned?",
  "How quickly must a landlord start an urgent repair?",
  "Can the landlord come into my flat without telling me?",
  "What is the tax rate on cryptocurrency gains?",
];

function Highlighted({ text, words }: { text: string; words: string[] }) {
  if (!words.length) return <>{text}</>;
  const re = new RegExp(`\\b(${words.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})\\b`, "gi");
  const parts = text.split(re);
  return <>{parts.map((p, i) => (i % 2 === 1 ? <mark key={i}>{p}</mark> : <span key={i}>{p}</span>))}</>;
}

function SourceCard({ s, cited }: { s: Source; cited: boolean }) {
  return (
    <li className={`source${cited ? " cited" : ""}`}>
      <div className="source-head">
        <strong>#{s.rank} {s.sections.join(", ")}</strong>
        {cited && <span className="tag">cited in answer</span>}
        <span className="scores">retrieval {s.retrieval_score.toFixed(3)} · coverage {Math.round(s.coverage * 100)}%</span>
      </div>
      <p><Highlighted text={s.text} words={s.highlight} /></p>
    </li>
  );
}

export default function AskPanel({ config }: { config: Config | null }) {
  const [q, setQ] = useState("");
  const [retrieval, setRetrieval] = useState<Retrieval | "">("");
  const [chunking, setChunking] = useState<Chunking | "">("");
  const [rerank, setRerank] = useState<"" | "on" | "off">("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [res, setRes] = useState<AskResponse | null>(null);

  const submit = async (question: string) => {
    const text = question.trim();
    if (text.length < 3) { setErr("Please type a question of at least 3 characters."); return; }
    setBusy(true); setErr(null);
    try {
      setRes(await api.ask(text, {
        ...(retrieval ? { retrieval } : {}), ...(chunking ? { chunking } : {}),
        ...(rerank ? { rerank: rerank === "on" } : {}),
      }));
    } catch (e) { setRes(null); setErr(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  };

  return (
    <>
      <form className="card" onSubmit={(e) => { e.preventDefault(); void submit(q); }}>
        <label htmlFor="q" className="label">Ask a question about the loaded documents</label>
        <textarea id="q" rows={2} maxLength={500} value={q} onChange={(e) => setQ(e.target.value)}
          placeholder="e.g. How much notice is needed to increase the rent?"
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void submit(q); } }} />
        <div className="row">
          <button className="btn" type="submit" disabled={busy}>{busy ? "Searching…" : "Ask"}</button>
          <span className="hint">Enter to send · answers come only from the documents</span>
        </div>
        <div className="chips" aria-label="Example questions">
          {EXAMPLES.map((x) => (
            <button type="button" key={x} className="chip" onClick={() => { setQ(x); void submit(x); }}>{x}</button>
          ))}
        </div>
        <details className="adv">
          <summary>Retrieval settings (defaults: {config ? `${config.retrieval}, rerank ${config.rerank ? "on" : "off"}, ${config.chunking} chunks` : "…"})</summary>
          <div className="grid3">
            <label>Retrieval
              <select value={retrieval} onChange={(e) => setRetrieval(e.target.value as Retrieval | "")}>
                <option value="">default</option><option value="bm25">BM25 (keywords)</option>
                <option value="vector">Vector (TF-IDF)</option><option value="hybrid">Hybrid</option>
              </select></label>
            <label>Chunking
              <select value={chunking} onChange={(e) => setChunking(e.target.value as Chunking | "")}>
                <option value="">default</option><option value="section">By legal section</option>
                <option value="window">Fixed word windows</option>
              </select></label>
            <label>Rerank
              <select value={rerank} onChange={(e) => setRerank(e.target.value as "" | "on" | "off")}>
                <option value="">default</option><option value="on">On</option><option value="off">Off</option>
              </select></label>
          </div>
        </details>
      </form>

      {err && <div className="err" role="alert">{err}</div>}

      {res && (
        <div className="card" aria-live="polite">
          {res.abstained ? (
            <div className="answer abstain">
              <h2>No answer found in the documents</h2>
              <p>{res.answer}</p>
              <p className="hint">The best-matching passage covered only {Math.round(res.support * 100)}% of your
                question's key terms, below the {Math.round(res.threshold * 100)}% needed to answer. If you expected an
                answer, try different words: keyword search can miss paraphrases.</p>
            </div>
          ) : (
            <div className="answer">
              <h2>Answer</h2>
              <p className="answer-text">{res.answer}</p>
              <div className="cites">
                {res.citations.length ? res.citations.map((c) => <span className="tag strong" key={c}>{c}</span>)
                  : <span className="hint">no citation returned</span>}
                <span className="hint">via {res.generator === "llm" ? "language model" : "extractive (quotes the text)"}</span>
              </div>
              <div className="meter" role="img" aria-label={`Support ${Math.round(res.support * 100)} percent`}>
                <div className="bar" style={{ width: `${Math.min(100, res.support * 100)}%` }} />
                <div className="mark-line" style={{ left: `${res.threshold * 100}%` }} title="answer threshold" />
              </div>
              <div className="hint">Support {Math.round(res.support * 100)}% (answer threshold {Math.round(res.threshold * 100)}%).
                Support is how much of your question the best passage covers; it is not the chance the answer is correct.</div>
            </div>
          )}
          <h3>Passages retrieved <span className="hint">({res.timing_ms.retrieval} ms retrieval, {res.timing_ms.generation} ms answer)</span></h3>
          <ul className="sources">
            {res.sources.map((s) => <SourceCard key={s.rank} s={s} cited={s.sections.some((x) => res.citations.includes(x))} />)}
          </ul>
          <p className="hint">{res.disclaimer}</p>
        </div>
      )}
    </>
  );
}
