import { useEffect, useRef } from "react";

// A lightweight, GPU-friendly canvas of drifting depth particles that gently
// parallax toward the cursor — paired with CSS aurora blobs behind it. No
// external 3D library, so the bundle stays small and the build stays reliable.
export default function AnimatedBackground() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);
    let raf;

    const reduceMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    const COUNT = Math.min(90, Math.floor((width * height) / 22000));
    const particles = Array.from({ length: COUNT }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      z: Math.random() * 0.8 + 0.2, // depth: drives size, speed, parallax
      vx: (Math.random() - 0.5) * 0.25,
      vy: (Math.random() - 0.5) * 0.25,
    }));

    const mouse = { x: width / 2, y: height / 2 };
    const onMove = (e) => {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
    };
    const onResize = () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("resize", onResize);

    const accent = () =>
      getComputedStyle(document.documentElement)
        .getPropertyValue("--accent-rgb")
        .trim() || "108, 124, 255";

    const draw = () => {
      ctx.clearRect(0, 0, width, height);
      const rgb = accent();
      const px = (mouse.x - width / 2) / width;
      const py = (mouse.y - height / 2) / height;

      for (const p of particles) {
        if (!reduceMotion) {
          p.x += p.vx * p.z;
          p.y += p.vy * p.z;
        }
        if (p.x < 0) p.x = width;
        if (p.x > width) p.x = 0;
        if (p.y < 0) p.y = height;
        if (p.y > height) p.y = 0;

        const ox = px * 40 * p.z;
        const oy = py * 40 * p.z;
        const size = p.z * 2.4;

        ctx.beginPath();
        ctx.arc(p.x + ox, p.y + oy, size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${rgb}, ${0.12 + p.z * 0.35})`;
        ctx.fill();
      }

      // Thread nearby particles with faint lines for a constellation feel.
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const a = particles[i];
          const b = particles[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const dist = dx * dx + dy * dy;
          if (dist < 13000) {
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.strokeStyle = `rgba(${rgb}, ${0.05 * (1 - dist / 13000)})`;
            ctx.lineWidth = 1;
            ctx.stroke();
          }
        }
      }
      raf = requestAnimationFrame(draw);
    };
    draw();

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("resize", onResize);
    };
  }, []);

  return (
    <div className="bg-scene" aria-hidden="true">
      <div className="aurora aurora-1" />
      <div className="aurora aurora-2" />
      <div className="aurora aurora-3" />
      <canvas ref={canvasRef} className="bg-canvas" />
    </div>
  );
}
