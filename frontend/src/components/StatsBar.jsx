import { useCountUp } from "../hooks/useCountUp";

function StatCard({ label, value, suffix = "", icon }) {
  const shown = useCountUp(value);
  return (
    <div className="stat-card">
      <span className="stat-icon">{icon}</span>
      <div className="stat-body">
        <span className="stat-value">
          {shown.toLocaleString()}
          {suffix}
        </span>
        <span className="stat-label">{label}</span>
      </div>
    </div>
  );
}

export default function StatsBar({ stats }) {
  if (!stats) return null;
  return (
    <div className="stats-bar">
      <StatCard label="Documents" value={stats.document_count} icon="📚" />
      <StatCard label="Chunks indexed" value={stats.total_chunks} icon="🧩" />
      <StatCard label="Questions asked" value={stats.query_count} icon="💬" />
      <StatCard
        label="Avg confidence"
        value={stats.avg_confidence}
        suffix="%"
        icon="🎯"
      />
      <StatCard
        label="Avg latency"
        value={stats.avg_latency_ms}
        suffix="ms"
        icon="⚡"
      />
      <StatCard label="Marked helpful" value={stats.helpful_count} icon="👍" />
    </div>
  );
}
