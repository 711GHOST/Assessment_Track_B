import { useAuth } from "../context/AuthContext";
import Logo from "./Logo";
import ThemeToggle from "./ThemeToggle";

export default function Navbar({ providers }) {
  const { user, logout } = useAuth();

  return (
    <header className="navbar">
      <Logo size={30} />

      {providers && (
        <div className="provider-badges" title="Active pipeline providers">
          <span className="badge">🧠 {providers.llm}</span>
          <span className="badge">🗂 {providers.vector_store}</span>
          <span className="badge">💾 {providers.database}</span>
        </div>
      )}

      <div className="navbar-user">
        <ThemeToggle />
        <div className="user-chip">
          <span className="user-avatar">
            {(user?.full_name || "?").charAt(0).toUpperCase()}
          </span>
          <span className="user-name">{user?.full_name}</span>
        </div>
        <button className="btn btn-ghost" onClick={logout}>
          Sign out
        </button>
      </div>
    </header>
  );
}
