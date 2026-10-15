import { useState } from "react";
import { api } from "./api";
import AskPanel from "./components/AskPanel";
import EvalPanel from "./components/EvalPanel";
import HowPanel from "./components/HowPanel";
import { useAsync } from "./hooks";

type Tab = "ask" | "eval" | "how";

export default function App() {
  const health = useAsync(() => api.health(), []);
  const config = useAsync(() => api.config(), []);
  const [tab, setTab] = useState<Tab>("ask");
  const h = health.data;

  return (
    <>
      {health.error && <div className="banner error" role="alert">Cannot reach the API: {health.error}</div>}
      {h && h.sections === 0 && (
        <div className="banner error" role="alert">No documents loaded. Add .txt, .md or .pdf files to backend/data/raw and restart.</div>
      )}
      <header className="topbar">
        <h1>Legal<span>Lens</span></h1>
        <span className="hint">
          {h ? `${h.documents.join(", ") || "no documents"} · ${h.sections} sections · ${h.generator === "llm" ? "LLM answers" : "extractive answers (offline)"}` : "connecting…"}
        </span>
      </header>
      <main className="main">
        <div className="tabs" role="tablist">
          {([["ask", "Ask"], ["eval", "Evaluation"], ["how", "How it works"]] as [Tab, string][]).map(([k, label]) => (
            <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}>{label}</button>
          ))}
        </div>
        {tab === "ask" && <AskPanel config={config.data} />}
        {tab === "eval" && <EvalPanel />}
        {tab === "how" && <HowPanel />}
      </main>
      <footer className="foot">{h?.disclaimer}</footer>
    </>
  );
}
