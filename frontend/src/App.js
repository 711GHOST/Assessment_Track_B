import React, { useState } from 'react';
import './App.css';

const BACKEND_URL = "https://shwetanshu25-mini-rag-backend.hf.space";

function App() {
  const [text, setText] = useState("");
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleUpload = async () => {
    const response = await fetch(`${BACKEND_URL}/upload`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        id: Date.now().toString(),
        text,
        metadata: {},
      }),
    });
    if (response.ok) {
      alert("Document uploaded successfully!");
      setText("");
    }
  };

  const handleQuery = async () => {
    setLoading(true);
    const response = await fetch(`${BACKEND_URL}/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ query, top_k: 5 }),
    });
    const data = await response.json();
    setAnswer(data);
    setLoading(false);
  };

  return (
    <div className="App">
      <h1>Mini RAG Application</h1>

      <div>
        <textarea
          placeholder="Paste your text here"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <button onClick={handleUpload}>Upload</button>
      </div>

      <div>
        <input
          type="text"
          placeholder="Enter your query"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button onClick={handleQuery} disabled={loading}>
          {loading ? "Loading..." : "Search"}
        </button>
      </div>

      {answer && (
        <div>
          <h2>Answer</h2>
          <p>{answer.answer}</p>
          <h3>Citations</h3>
          <ul>
            {answer.citations.map((citation, index) => (
              <li key={index}>{citation}</li>
            ))}
          </ul>
          <p>Latency: {answer.latency}s</p>
          <p>Token Estimate: {answer.token_estimate}</p>
          <p>Cost Estimate: ${answer.cost_estimate}</p>
        </div>
      )}
    </div>
  );
}

export default App;