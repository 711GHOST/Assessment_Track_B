import { useRef } from "react";

// Wraps content in a card that tilts in 3D toward the cursor and lifts a
// glare highlight. Falls back to a plain card on touch / reduced motion.
export default function TiltCard({ children, className = "", max = 10 }) {
  const ref = useRef(null);

  function handleMove(e) {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width;
    const py = (e.clientY - rect.top) / rect.height;
    const rotX = (0.5 - py) * max * 2;
    const rotY = (px - 0.5) * max * 2;
    el.style.setProperty("--rx", `${rotX}deg`);
    el.style.setProperty("--ry", `${rotY}deg`);
    el.style.setProperty("--gx", `${px * 100}%`);
    el.style.setProperty("--gy", `${py * 100}%`);
  }

  function reset() {
    const el = ref.current;
    if (!el) return;
    el.style.setProperty("--rx", "0deg");
    el.style.setProperty("--ry", "0deg");
  }

  return (
    <div
      ref={ref}
      className={`tilt-card ${className}`}
      onMouseMove={handleMove}
      onMouseLeave={reset}
    >
      <div className="tilt-inner">{children}</div>
      <div className="tilt-glare" />
    </div>
  );
}
