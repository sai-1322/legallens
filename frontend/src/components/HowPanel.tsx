const STEPS = [
  ["1. Ingest", "Reads .txt, .md and .pdf files and splits them at headings such as “Section 9.” so every passage knows which section it came from."],
  ["2. Chunk", "Keeps each legal section whole (or slides a fixed word window). Chunk size changes what retrieval can find, so it is one of the things the evaluation compares."],
  ["3. Index", "Builds a BM25 keyword index and a TF-IDF vector index. Optionally swap in real neural embeddings (EMBEDDER=st)."],
  ["4. Retrieve", "Takes the top 20 from BM25, vector search or both fused with reciprocal-rank fusion, then optionally reranks by how many of the question’s rare terms each passage contains."],
  ["5. Decide", "If even the best passage covers too little of the question, the system refuses rather than guess. This threshold is the safety valve."],
  ["6. Answer", "Extractive mode quotes the best sentences (no model needed). LLM mode sends only the retrieved passages to a language model with a cite-or-say-NOT_FOUND instruction."],
];
export default function HowPanel() {
  return (
    <div className="card prose">
      <h2>How LegalLens works</h2>
      <ol className="steps">{STEPS.map(([t, d]) => <li key={t}><strong>{t}</strong> {d}</li>)}</ol>
      <h3>What it cannot do</h3>
      <ul>
        <li>Keyword and TF-IDF search miss paraphrases (“flat” vs “dwelling”, “cost” vs “fee”). Neural embeddings help, and the evaluation tab shows what is still missed.</li>
        <li>It answers from the documents you loaded. It does not know about amendments, court rulings or other laws.</li>
        <li>The extractive answer quotes text; it can pick a sentence that is relevant but incomplete.</li>
        <li>The refusal threshold is a trade-off, not a guarantee. Always check the cited section.</li>
        <li>This is an educational project and not legal advice.</li>
      </ul>
    </div>
  );
}
