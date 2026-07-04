import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import AuthLayout from "../components/AuthLayout";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";

export default function LoginPage() {
  const { user, login } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email, password);
      toast("Welcome back!", "success");
      navigate("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Sign in to your workspace"
      footer={
        <>
          New here? <Link to="/register">Create an account</Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="auth-form">
        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            autoComplete="email"
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            autoComplete="current-password"
            required
          />
        </label>
        {error && <p className="form-error">{error}</p>}
        <button type="submit" className="btn btn-primary" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </AuthLayout>
  );
}
