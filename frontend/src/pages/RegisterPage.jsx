import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import AuthLayout from "../components/AuthLayout";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";

export default function RegisterPage() {
  const { user, register } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
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
      await register(fullName, email, password);
      toast("Account created — welcome to RAG Studio!", "success");
      navigate("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout
      title="Create your account"
      subtitle="A private workspace for your documents"
      footer={
        <>
          Already registered? <Link to="/login">Sign in</Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="auth-form">
        <label>
          Full name
          <input
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            placeholder="Ada Lovelace"
            autoComplete="name"
            maxLength={80}
            required
          />
        </label>
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
            placeholder="At least 8 characters, letters + digits"
            autoComplete="new-password"
            minLength={8}
            maxLength={72}
            required
          />
        </label>
        {error && <p className="form-error">{error}</p>}
        <button type="submit" className="btn btn-primary" disabled={busy}>
          {busy ? "Creating account…" : "Create account"}
        </button>
      </form>
    </AuthLayout>
  );
}
