import { useState } from "react";
import { api } from "./api.js";

export default function Login({ onLogin }) {
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    const result = await api("/api/login", { method: "POST", body: { login, password } });
    setBusy(false);
    if (result.ok) onLogin(result.data.login);
    else setError(result.error.message);
  }

  return (
    <form onSubmit={submit} style={{ display: "grid", gap: 12, maxWidth: 320 }}>
      <h2>Вход</h2>
      <label>
        Логин
        <input value={login} onChange={(e) => setLogin(e.target.value)} autoComplete="username" style={{ display: "block", width: "100%" }} />
      </label>
      <label>
        Пароль
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" style={{ display: "block", width: "100%" }} />
      </label>
      <button type="submit" disabled={busy}>{busy ? "Вхожу…" : "Войти"}</button>
      {error && <p style={{ color: "#b00020", margin: 0 }}>{error}</p>}
    </form>
  );
}
