import AnimatedBackground from "./AnimatedBackground";
import Logo from "./Logo";
import ThemeToggle from "./ThemeToggle";
import TiltCard from "./TiltCard";

export default function AuthLayout({ title, subtitle, children, footer }) {
  return (
    <div className="auth-page">
      <AnimatedBackground />
      <div className="auth-topbar">
        <ThemeToggle />
      </div>

      <div className="auth-hero">
        <Logo size={64} withText={false} />
        <h1 className="hero-title">
          Turn documents into <span className="grad-text">answers</span>
        </h1>
        <p className="hero-sub">
          Upload your knowledge, ask anything, and get grounded responses with
          citations and a confidence score you can trust.
        </p>
        <ul className="hero-points">
          <li>🔒 Private, per-user knowledge base</li>
          <li>📎 Inline citations on every answer</li>
          <li>🎯 Confidence scoring &amp; suggested questions</li>
        </ul>
      </div>

      <TiltCard className="auth-card" max={7}>
        <div className="auth-card-head">
          <Logo size={30} />
        </div>
        <h2>{title}</h2>
        <p className="auth-subtitle">{subtitle}</p>
        {children}
        <div className="auth-footer">{footer}</div>
      </TiltCard>
    </div>
  );
}
