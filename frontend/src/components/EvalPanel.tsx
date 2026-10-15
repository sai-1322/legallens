import { useMemo, useState } from "react";
import { api } from "../api";
import { useAsync } from "../hooks";
import type { EvalConfig } from "../types";

const pc = (v: number | null | undefined) => (v === null || v === undefined ? "n/a" : `${Math.round(v * 100)}%`);
const ci = (r: [number, number] | null) => (r ? `${Math.round(r[0] * 100)}–${Math.round(r[1] * 100)}%` : "");

type Key = "balanced" | "correct" | "abstain_ok" | "hit@1" | "hit@5" | "mrr@5";

function Bar({ v }: { v: number | null }) {
  return <span className="minibar" aria-hidden="true"><i style={{ width: `${(v ?? 0) * 100}%` }} /></span>;
}

export default function EvalPanel() {
  const rep = useAsync(() => api.evalResults(), []);
  const [key, setKey] = useState<Key>("balanced");
  const rows = useMemo(() => {
    const c: EvalConfig[] = rep.data?.configs ?? [];
    return [...c].sort((a, b) => ((b.metrics[key] as number) ?? -1) - ((a.metrics[key] as number) ?? -1));
  }, [rep.data, key]);

  if (rep.loading) return <div className="loading">Loading evaluation results…</div>;
  if (rep.error || !rep.data) {
    return <div className="card"><h2>No evaluation results yet</h2><p>{rep.error}</p>
      <pre>python -m legallens.evaluate</pre></div>;
  }
  const d = rep.data;
  const best = d.configs.find((c) => c.id === d.best_id)!;
  const m = best.metrics;
  const th = (k: Key, label: string) => (
    <th><button className="sort" aria-pressed={key === k} onClick={() => setKey(k)}>{label}</button></th>
  );

  return (
    <>
      <div className="card">
        <h2>Evaluation of the loaded documents</h2>
        <p>{d.meta.n_questions} questions ({d.meta.n_answerable} answerable, {d.meta.n_unanswerable} that the
          documents cannot answer), run {d.meta.date}, answers by <strong>{d.meta.generator}</strong> generation.
          Documents: {d.meta.documents.join(", ")}.</p>
        <div className="note">{d.meta.note}</div>
        <div className="note">
          If these are the demo documents, the questions were written alongside the fictional Act, so scores are
          optimistic. For real documents, write your own questions (see data/eval/README.md).
        </div>
        <div className="metrics">
          <div className="metric"><div className="k">Correct answers</div><div className="v">{pc(m.correct)}</div>
            <div className="d">95% CI {ci(m.ci.correct)}</div></div>
          <div className="metric"><div className="k">Refuses unanswerable</div><div className="v">{pc(m.abstain_ok)}</div>
            <div className="d">95% CI {ci(m.ci.abstain_ok)}</div></div>
          <div className="metric"><div className="k">Wrongly refuses</div><div className="v">{pc(m.false_abstain)}</div>
            <div className="d">answerable but refused</div></div>
          <div className="metric"><div className="k">Right passage in top 5</div><div className="v">{pc(m["hit@5"])}</div>
            <div className="d">easy on small corpora</div></div>
          <div className="metric"><div className="k">Right passage ranked #1</div><div className="v">{pc(m["hit@1"])}</div>
            <div className="d">MRR@5 {m["mrr@5"].toFixed(2)}</div></div>
          <div className="metric"><div className="k">Faithful sentences</div><div className="v">{pc(m.faithful)}</div>
            <div className="d">100% is expected for extractive</div></div>
        </div>
        <p className="hint">Best configuration: <strong>{best.id}</strong>. It was picked on these same questions,
          so its score is slightly flattering.</p>
      </div>

      <div className="card">
        <h2>All configurations</h2>
        <div className="sub">Click a column to sort. Many rows are within noise of each other: with
          {" "}{d.meta.n_questions} questions, one question is worth about {Math.round(100 / Math.max(1, d.meta.n_answerable))} points.</div>
        <div className="tablewrap">
          <table>
            <thead><tr><th>Configuration</th>{th("balanced", "Balanced")}{th("correct", "Correct")}
              {th("abstain_ok", "Refuses ok")}{th("hit@1", "Hit@1")}{th("hit@5", "Hit@5")}{th("mrr@5", "MRR@5")}<th>ms</th></tr></thead>
            <tbody>
              {rows.map((c) => (
                <tr key={c.id} className={c.id === d.best_id ? "sel" : ""}>
                  <td>{c.id}</td>
                  <td>{pc(c.metrics.balanced)} <Bar v={c.metrics.balanced} /></td>
                  <td>{pc(c.metrics.correct)}</td><td>{pc(c.metrics.abstain_ok)}</td>
                  <td>{pc(c.metrics["hit@1"])}</td><td>{pc(c.metrics["hit@5"])}</td>
                  <td>{c.metrics["mrr@5"].toFixed(2)}</td><td>{c.metrics.latency_ms_mean.toFixed(0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <h2>Where the best configuration fails</h2>
        <div className="sub">By question type: {Object.entries(d.best_by_type).map(([t, v]) => `${t} ${v.ok}/${v.n}`).join(" · ")}</div>
        <div className="tablewrap">
          <table>
            <thead><tr><th>#</th><th>Type</th><th>Why it failed</th><th>Question</th></tr></thead>
            <tbody>
              {d.failures.map((f) => (
                <tr key={f.id}><td>{f.id}</td><td>{f.type}</td><td><span className="tag">{f.category.replace(/_/g, " ")}</span></td>
                  <td>{f.question}</td></tr>
              ))}
              {!d.failures.length && <tr><td colSpan={4}>No failures on this question set.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <h2>The refusal trade-off</h2>
        <div className="sub">Raising the answer threshold refuses more unanswerable questions, but also refuses
          answerable ones. The default ({Math.round(d.meta.threshold * 100)}%) was picked by hand after looking at a handful of example questions, not fitted to this whole set.</div>
        <div className="tablewrap">
          <table>
            <thead><tr><th>Threshold</th><th>Correct answers</th><th>Wrongly refused</th><th>Unanswerable refused</th></tr></thead>
            <tbody>
              {d.threshold_sweep.filter((_, i) => i % 2 === 0).map((r) => (
                <tr key={r.threshold} className={Math.abs(r.threshold - d.meta.threshold) < 0.026 ? "sel" : ""}>
                  <td>{Math.round(r.threshold * 100)}%</td><td>{pc(r.correct)}</td><td>{pc(r.false_abstain)}</td>
                  <td>{pc(r.abstain_ok)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
