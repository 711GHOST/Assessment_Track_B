import React, { useState } from "react";
import "./App.css";

const BACKEND_URL =
  process.env.REACT_APP_API_URL ||
  "https://shwetanshu25-mini-rag-backend.hf.space";

function App() {
  const [text, setText] = useState("");
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleUpload = async () => {
    try {
      setError(null);
      const response = await fetch(`${BACKEND_URL}/upload`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: Date.now().toString(),
          text,
          metadata: {},
        }),
      });

      if (!response.ok) throw new Error("Upload failed");

      alert("Document uploaded successfully!");
      setText("");
    } catch (err) {
      console.error(err);
      setError("Upload failed. Check backend.");
    }
  };

  const handleQuery = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${BACKEND_URL}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, top_k: 5 }),
      });

      if (!response.ok) throw new Error("Query failed");

      const data = await response.json();
      setAnswer(data);
    } catch (err) {
      console.error(err);
      setError("Query failed. Check backend.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <h1>Mini RAG Application</h1>

      <textarea
        placeholder="Paste your text here"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <button onClick={handleUpload}>Upload</button>

      <input
        type="text"
        placeholder="Enter your query"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <button onClick={handleQuery} disabled={loading}>
        {loading ? "Loading..." : "Search"}
      </button>

      {error && <p className="error">{error}</p>}

      {answer && (
        <div className="answer-box">
          <h2>Answer</h2>
          <p>{answer.answer}</p>

          <h3>Citations</h3>
          <ul>
            {answer.citations.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>

          <div className="stats">
            <p>Latency: {answer.latency}s</p>
            <p>Token Estimate: {answer.token_estimate}</p>
            <p>Cost Estimate: ${answer.cost_estimate}</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
