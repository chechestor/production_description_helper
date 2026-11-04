import { useEffect, useState } from "react";
import { api } from "./api.js";
import Login from "./Login.jsx";

// Экран входа (F003) и страница-заглушка; основной экран добавит F009.
export default function App() {
  const [user, setUser] = useState(undefined); // undefined — проверяю, null — не вошёл
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api("/api/me").then((r) => setUser(r.ok ? r.data.login : null));
    api("/api/health").then((r) => (r.ok ? setHealth(r.data) : setError(r.error.message)));
  }, []);

  async function logout() {
    await api("/api/logout", { method: "POST" });
    setUser(null);
  }

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", maxWidth: 720, margin: "40px auto", padding: "0 16px" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16 }}>
        <h1 style={{ fontSize: 24 }}>Production Description Helper</h1>
        {user && (
          <span>
            {user} <button onClick={logout}>Выйти</button>
          </span>
        )}
      </header>

      {user === undefined && <p>Проверяю вход…</p>}
      {user === null && <Login onLogin={setUser} />}
      {user && (
        <>
          <p>Черновик карточки товара для B2B-магазина по данным о приборе.</p>
          <h2>Состояние backend</h2>
          {error && <p style={{ color: "#b00020" }}>{error}</p>}
          {health && (
            <ul>
              <li>Статус: {health.status}</li>
              <li>Ключ LLM: {health.llm_configured ? "задан" : "не задан"}</li>
            </ul>
          )}
        </>
      )}
    </main>
  );
}
