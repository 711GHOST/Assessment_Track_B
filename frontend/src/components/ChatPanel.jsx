import { useEffect, useRef, useState } from "react";

import { api } from "../api/client";
import { useToast } from "../context/ToastContext";
import { useTypewriter } from "../hooks/useTypewriter";
import ConfidenceRing from "./ConfidenceRing";

function Citations({ citations }) {
  const [open, setOpen] = useState(false);
  if (!citations?.length) return null;
  const maxScore = Math.max(...citations.map((c) => c.score), 0.0001);
  return (
    <div className="citations">
      <button className="citations-toggle" onClick={() => setOpen(!open)}>
        📎 {open ? "Hide" : "Show"} {citations.length} source
        {citations.length > 1 ? "s" : ""}
      </button>
      {open && (
        <ol className="citations-list">
          {citations.map((c) => (
            <li key={c.index}>
              <div className="citation-head">
                <span className="citation-source">
                  [{c.index}] {c.document_title} · chunk {c.chunk_index}
                </span>
                <span className="citation-score">{c.score.toFixed(3)}</span>
              </div>
              <div className="relevance-bar">
                <span style={{ width: `${(c.score / maxScore) * 100}%` }} />
              </div>
              <p className="citation-snippet">{c.snippet}…</p>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

function AssistantBubble({ message, onFeedback }) {
  const toast = useToast();
  const { output, done } = useTypewriter(message.answer, !!message.isNew);

  function copy() {
    navigator.clipboard?.writeText(message.answer);
    toast("Answer copied to clipboard", "success");
  }

  return (
    <div className="bubble bubble-assistant">
      <div className="assistant-top">
        {message.confidence > 0 && (
          <ConfidenceRing value={message.confidence} />
        )}
        <p className="answer-text">
          {output}
          {!done && <span className="caret" />}
        </p>
      </div>

      {done && (
        <>
          <div className="answer-meta">
            <span className="badge badge-mode">{message.mode}</span>
            <span className="meta-item">⚡ {message.latency_ms} ms</span>
            {message.token_estimate > 0 && (
              <span className="meta-item">≈ {message.token_estimate} tokens</span>
            )}
            <div className="answer-actions">
              <button className="icon-action" onClick={copy} title="Copy answer">
                ⧉
              </button>
              <button
                className={`icon-action${message.feedback === "up" ? " active-up" : ""}`}
                onClick={() => onFeedback(message, "up")}
                title="Helpful"
              >
                👍
              </button>
              <button
                className={`icon-action${message.feedback === "down" ? " active-down" : ""}`}
                onClick={() => onFeedback(message, "down")}
                title="Not helpful"
              >
                👎
              </button>
            </div>
          </div>
          <Citations citations={message.citations} />
        </>
      )}
    </div>
  );
}

export default function ChatPanel({ documents, selectedIds, suggestions, onActivity }) {
  const toast = useToast();
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    api("/api/chat/history")
      .then(setMessages)
      .catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  async function ask(text) {
    const trimmed = text.trim();
    if (!trimmed || busy) return;
    setBusy(true);
    setQuestion("");
    try {
      const entry = await api("/api/chat/query", {
        method: "POST",
        body: {
          question: trimmed,
          top_k: 5,
          document_ids: selectedIds.length > 0 ? selectedIds : null,
        },
      });
      setMessages((current) => [...current, { ...entry, isNew: true }]);
      onActivity?.();
    } catch (err) {
      toast(err.message, "error");
      setQuestion(trimmed);
    } finally {
      setBusy(false);
    }
  }

  async function handleFeedback(message, rating) {
    try {
      await api(`/api/chat/${message.id}/feedback`, {
        method: "POST",
        body: { rating },
      });
      setMessages((current) =>
        current.map((m) => (m.id === message.id ? { ...m, feedback: rating } : m))
      );
      toast("Thanks for the feedback!", "success");
      onActivity?.();
    } catch (err) {
      toast(err.message, "error");
    }
  }

  async function handleClear() {
    try {
      await api("/api/chat/history", { method: "DELETE" });
      setMessages([]);
      toast("Chat history cleared", "info");
    } catch (err) {
      toast(err.message, "error");
    }
  }

  const showSuggestions =
    messages.length === 0 && suggestions?.length > 0 && documents.length > 0;

  return (
    <main className="chat-panel glass">
      <div className="chat-header">
        <h2>Ask your documents</h2>
        {messages.length > 0 && (
          <button className="btn btn-ghost" onClick={handleClear}>
            Clear history
          </button>
        )}
      </div>

      <div className="chat-messages">
        {messages.length === 0 && !busy && (
          <div className="chat-empty">
            <div className="empty-orb" />
            <p>
              {documents.length === 0
                ? "Upload a document on the left, then ask a question about it."
                : "Ask a question — every answer comes with citations and a confidence score."}
            </p>
            {showSuggestions && (
              <div className="suggestions">
                <span className="suggestions-label">✨ Suggested questions</span>
                <div className="suggestion-chips">
                  {suggestions.map((s) => (
                    <button
                      key={s}
                      className="chip"
                      onClick={() => ask(s)}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {messages.map((message) => (
          <div key={message.id} className="chat-exchange">
            <div className="bubble bubble-user">{message.question}</div>
            <AssistantBubble message={message} onFeedback={handleFeedback} />
          </div>
        ))}

        {busy && (
          <div className="chat-exchange">
            <div className="bubble bubble-assistant thinking">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(question);
        }}
        className="chat-input"
      >
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. What does the report say about Q3 revenue?"
          maxLength={2000}
        />
        <button
          type="submit"
          className="btn btn-primary btn-glow"
          disabled={busy || !question.trim()}
        >
          Ask →
        </button>
      </form>
    </main>
  );
}
