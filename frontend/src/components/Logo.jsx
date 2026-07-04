// A continuously rotating 3D cube built purely from CSS transforms - the
// brand mark. `size` scales it for navbar vs. auth-hero contexts.
export default function Logo({ size = 34, withText = true }) {
  return (
    <div className="brand">
      <div className="logo-cube" style={{ "--cube": `${size}px` }}>
        <span className="cube-face face-front" />
        <span className="cube-face face-back" />
        <span className="cube-face face-right" />
        <span className="cube-face face-left" />
        <span className="cube-face face-top" />
        <span className="cube-face face-bottom" />
      </div>
      {withText && <span className="brand-name">RAG Studio</span>}
    </div>
  );
}
