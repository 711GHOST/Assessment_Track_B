import { useCallback, useEffect, useState } from "react";

import { api } from "../api/client";
import AnimatedBackground from "../components/AnimatedBackground";
import ChatPanel from "../components/ChatPanel";
import DocumentsPanel from "../components/DocumentsPanel";
import Navbar from "../components/Navbar";
import StatsBar from "../components/StatsBar";

export default function DashboardPage() {
  const [documents, setDocuments] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]);
  const [providers, setProviders] = useState(null);
  const [stats, setStats] = useState(null);
  const [suggestions, setSuggestions] = useState([]);

  const refreshStats = useCallback(async () => {
    try {
      setStats(await api("/api/stats"));
    } catch {
      /* keep last known stats */
    }
  }, []);

  const refreshSuggestions = useCallback(async () => {
    try {
      const data = await api("/api/chat/suggestions");
      setSuggestions(data.suggestions);
    } catch {
      setSuggestions([]);
    }
  }, []);

  const refreshDocuments = useCallback(async () => {
    try {
      setDocuments(await api("/api/documents"));
    } catch {
      /* panels surface their own errors */
    }
    refreshStats();
    refreshSuggestions();
  }, [refreshStats, refreshSuggestions]);

  useEffect(() => {
    refreshDocuments();
    api("/api/health", { auth: false })
      .then((health) => setProviders(health.providers))
      .catch(() => setProviders(null));
  }, [refreshDocuments]);

  function toggleSelected(id) {
    setSelectedIds((current) =>
      current.includes(id) ? current.filter((x) => x !== id) : [...current, id]
    );
  }

  return (
    <div className="dashboard">
      <AnimatedBackground />
      <Navbar providers={providers} />
      <div className="dashboard-scroll">
        <StatsBar stats={stats} />
        <div className="dashboard-body">
          <DocumentsPanel
            documents={documents}
            selectedIds={selectedIds}
            onToggleSelected={toggleSelected}
            onChanged={refreshDocuments}
          />
          <ChatPanel
            documents={documents}
            selectedIds={selectedIds}
            suggestions={suggestions}
            onActivity={refreshStats}
          />
        </div>
      </div>
    </div>
  );
}
