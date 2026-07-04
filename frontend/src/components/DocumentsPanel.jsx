import { useRef, useState } from "react";

import { api } from "../api/client";
import { useToast } from "../context/ToastContext";

export default function DocumentsPanel({
  documents,
  selectedIds,
  onToggleSelected,
  onChanged,
}) {
  const toast = useToast();
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef(null);

  function readFile(file) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      setText(String(reader.result ?? ""));
      if (!title) setTitle(file.name.replace(/\.(txt|md)$/i, ""));
    };
    reader.readAsText(file);
  }

  async function handleUpload(event) {
    event.preventDefault();
    setBusy(true);
    try {
      const doc = await api("/api/documents", {
        method: "POST",
        body: { title: title.trim() || "Untitled", text },
      });
      toast(`Indexed "${doc.title}" into ${doc.chunk_count} chunks`, "success");
      setTitle("");
      setText("");
      if (fileInputRef.current) fileInputRef.current.value = "";
      await onChanged();
    } catch (err) {
      toast(err.message, "error");
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(doc) {
    try {
      await api(`/api/documents/${doc.id}`, { method: "DELETE" });
      toast(`Deleted "${doc.title}"`, "info");
      await onChanged();
    } catch (err) {
      toast(err.message, "error");
    }
  }

  return (
    <aside className="documents-panel glass">
      <div className="panel-head">
        <h2>Knowledge base</h2>
        <span className="pill">{documents.length}</span>
      </div>

      <form onSubmit={handleUpload} className="upload-form">
        <input
          type="text"
          placeholder="Document title"
          value={title}
          maxLength={120}
          onChange={(e) => setTitle(e.target.value)}
        />
        <label
          className={`dropzone${dragging ? " dragging" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            readFile(e.dataTransfer.files?.[0]);
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".txt,.md,text/plain,text/markdown"
            hidden
            onChange={(e) => readFile(e.target.files?.[0])}
          />
          <span className="dropzone-icon">⬆</span>
          <span>Drop a .txt / .md file or click to browse</span>
        </label>
        <textarea
          placeholder="…or paste text directly here"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={4}
        />
        <button
          type="submit"
          className="btn btn-primary btn-glow"
          disabled={busy || !text.trim()}
        >
          {busy ? "Indexing…" : "Upload & index"}
        </button>
      </form>

      <div className="documents-list">
        {documents.length === 0 && (
          <p className="empty-hint">
            No documents yet. Add one to start asking questions.
          </p>
        )}
        {documents.map((doc) => (
          <div
            key={doc.id}
            className={`document-item${
              selectedIds.includes(doc.id) ? " selected" : ""
            }`}
          >
            <label className="document-info">
              <input
                type="checkbox"
                checked={selectedIds.includes(doc.id)}
                onChange={() => onToggleSelected(doc.id)}
                title="Restrict questions to selected documents"
              />
              <span className="document-text">
                <span className="document-title">{doc.title}</span>
                <span className="document-meta">
                  {doc.chunk_count} chunks · {doc.char_count.toLocaleString()} chars
                </span>
              </span>
            </label>
            <button
              className="btn btn-icon"
              onClick={() => handleDelete(doc)}
              title="Delete document"
            >
              ✕
            </button>
          </div>
        ))}
      </div>

      {selectedIds.length > 0 && (
        <p className="scope-hint">
          🔎 Scoped to {selectedIds.length} selected document
          {selectedIds.length > 1 ? "s" : ""}
        </p>
      )}
    </aside>
  );
}
