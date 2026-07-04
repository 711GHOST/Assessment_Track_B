import { useEffect, useState } from "react";

// Animated SVG ring visualizing 0-100 grounding confidence. Colour shifts
// green → amber → red as confidence drops.
export default function ConfidenceRing({ value, size = 54 }) {
  const [shown, setShown] = useState(0);

  useEffect(() => {
    const timer = requestAnimationFrame(() => setShown(value));
    return () => cancelAnimationFrame(timer);
  }, [value]);

  const stroke = 5;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (shown / 100) * circumference;

  const color =
    value >= 66 ? "var(--success)" : value >= 33 ? "var(--warning)" : "var(--danger)";

  const label = value >= 66 ? "High" : value >= 33 ? "Medium" : "Low";

  return (
    <div className="confidence-ring" title={`Grounding confidence: ${value}%`}>
      <svg width={size} height={size}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--border)"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          style={{ transition: "stroke-dashoffset 1s cubic-bezier(.2,.8,.2,1)" }}
        />
        <text
          x="50%"
          y="50%"
          dominantBaseline="central"
          textAnchor="middle"
          className="ring-value"
          fill={color}
        >
          {value}
        </text>
      </svg>
      <span className="ring-label" style={{ color }}>
        {label}
      </span>
    </div>
  );
}
