"use client";

import { useState } from "react";

type Article = {
  source: string;
  title: string;
  year?: number | null;
  authors: string[];
  journal?: string | null;
  doi?: string | null;
  url?: string | null;
  language?: string | null;
  abstract?: string | null;
};

type SearchResponse = {
  topic: string;
  keywords: string[];
  articles: Article[];
  summary: string;
  critical_appraisal: string;
  research_gaps: string;
  evidence_quality: string;
  citations_csv: string;
};

export default function Home() {
  const [topic, setTopic] = useState("");
  const [maxResults, setMaxResults] = useState(25);
  const [sources, setSources] = useState<string[]>(["scopus"]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<SearchResponse | null>(null);

  const apiBase = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

  const toggleSource = (src: string) => {
    setSources((prev) =>
      prev.includes(src) ? prev.filter((s) => s !== src) : [...prev, src]
    );
  };

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (sources.length === 0) {
      setError("Please select at least one source database.");
      return;
    }
    setLoading(true);
    setError(null);
    setData(null);

    try {
      const res = await fetch(`${apiBase}/api/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, max_results: maxResults, include_full_text: false, sources }),
      });

      if (!res.ok) {
        const payload = await res.json().catch(() => ({}));
        throw new Error(payload.detail || "Search failed");
      }

      const payload: SearchResponse = await res.json();
      setData(payload);
    } catch (err: any) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  const downloadCsv = () => {
    if (!data?.citations_csv) return;
    const blob = new Blob([data.citations_csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "citations.csv";
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="panel">
      <form onSubmit={onSubmit} className="form">
        <label htmlFor="topic">Health sciences topic</label>
        <input
          id="topic"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="e.g., effect of meditation on cardiac arrhythmias"
          required
        />

        <fieldset style={{ border: "none", padding: 0 }}>
          <legend style={{ fontWeight: 600, marginBottom: "0.25rem" }}>Sources</legend>
          <label style={{ marginRight: "1rem" }}>
            <input
              type="checkbox"
              checked={sources.includes("pubmed")}
              onChange={() => toggleSource("pubmed")}
              style={{ marginRight: "0.3rem" }}
            />
            PubMed
          </label>
          <label>
            <input
              type="checkbox"
              checked={sources.includes("scopus")}
              onChange={() => toggleSource("scopus")}
              style={{ marginRight: "0.3rem" }}
            />
            Scopus
          </label>
        </fieldset>

        <label htmlFor="maxResults">Max results (1–100)</label>
        <input
          id="maxResults"
          type="number"
          min={1}
          max={100}
          value={maxResults}
          onChange={(e) => setMaxResults(Number(e.target.value))}
        />

        <button type="submit" disabled={loading}>
          {loading ? "Searching..." : "Search literature"}
        </button>
      </form>

      {error && <div className="error">{error}</div>}

      {data && (
        <div className="results">
          <section>
            <h2>Keywords</h2>
            <div className="chips">
              {data.keywords.map((k) => (
                <span key={k} className="chip">
                  {k}
                </span>
              ))}
            </div>
          </section>

          <section className="grid">
            <div>
              <h2>Summary</h2>
              <p>{data.summary || "No summary available."}</p>
            </div>
            <div>
              <h2>Critical appraisal</h2>
              <p>{data.critical_appraisal || "No appraisal available."}</p>
            </div>
            <div>
              <h2>Research gaps</h2>
              <p>{data.research_gaps || "No gaps identified."}</p>
            </div>
            <div>
              <h2>Evidence quality</h2>
              <p>{data.evidence_quality || "No assessment available."}</p>
            </div>
          </section>

          <section>
            <div className="results-header">
              <h2>Articles</h2>
              <button type="button" onClick={downloadCsv}>
                Download CSV
              </button>
            </div>
            <div className="articles">
              {data.articles.map((article, idx) => (
                <article key={`${article.title}-${idx}`}>
                  <h3>{article.title}</h3>
                  <p className="meta">
                    {article.source} {article.year ? `• ${article.year}` : ""}
                  </p>
                  {article.journal && <p>{article.journal}</p>}
                  {article.abstract && <p>{article.abstract}</p>}
                  {article.url && (
                    <a href={article.url} target="_blank" rel="noreferrer">
                      View source
                    </a>
                  )}
                </article>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}