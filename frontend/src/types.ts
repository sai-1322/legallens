export interface Health {
  status: string; version: string; documents: string[]; sections: number;
  generator: "extractive" | "llm"; embedder: string; disclaimer: string;
}
export interface Config {
  retrieval: Retrieval; rerank: boolean; top_k: number; chunking: Chunking; window_words: number;
  abstain_threshold: number; generator: string; llm_model: string | null;
}
export type Retrieval = "bm25" | "vector" | "hybrid";
export type Chunking = "section" | "window";

export interface Source {
  rank: number; label: string; sections: string[]; doc: string; text: string;
  retrieval_score: number; coverage: number; final_score: number; highlight: string[];
}
export interface AskResponse {
  question: string; answer: string; abstained: boolean; citations: string[]; support: number; threshold: number;
  generator: string; config: Record<string, unknown>; timing_ms: { retrieval: number; generation: number };
  sources: Source[]; disclaimer: string;
}
export interface AskOptions { retrieval?: Retrieval; rerank?: boolean; top_k?: number; chunking?: Chunking }

export interface Metrics {
  n_answerable: number; n_unanswerable: number; "hit@1": number; "hit@3": number; "hit@5": number; "mrr@5": number;
  correct: number; abstain_ok: number | null; false_abstain: number; faithful: number | null; balanced: number;
  latency_ms_mean: number; latency_ms_p95: number;
  ci: { "hit@5": [number, number]; correct: [number, number]; abstain_ok: [number, number] | null };
}
export interface EvalConfig {
  id: string; chunking: string; window: number; retrieval: string; rerank: boolean; metrics: Metrics;
}
export interface Failure {
  id: number; type: string; category: string; question: string; answer: string; support: number;
  first_hit_rank: number | null;
}
export interface EvalReport {
  meta: { date: string; documents: string[]; n_questions: number; n_answerable: number; n_unanswerable: number;
    threshold: number; generator: string; embedder: string; quick: boolean; note: string };
  best_id: string;
  configs: EvalConfig[];
  best_by_type: Record<string, { n: number; ok: number; rate: number }>;
  failures: Failure[];
  threshold_sweep: { threshold: number; false_abstain: number; correct: number; abstain_ok: number | null }[];
}
