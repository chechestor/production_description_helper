import { useEffect, useState } from "react";
import { api } from "./api.js";
import Generator from "./Generator.jsx";
import Login from "./Login.jsx";

// Экран входа (F003) и основной экран генерации (F009).
export default function App() {
  const [user, setUser] = useState(undefined); // undefined — проверяю, null — не вошёл
  const [health, setHealth] = useState(null);

  useEffect(() => {
    api("/api/me").then((r) => setUser(r.ok ? r.data.login : r.status === 401 ? null : false));
    api("/api/health").then((r) => setHealth(r.ok ? r.data : { error: r.error.message }));
  }, []);

  async function logout() {
    await api("/api/logout", { method: "POST" });
    setUser(null);
  }

  return (
    <main>
      <header>
        <h1>Production Description Helper</h1>
        {user && (
          <span className="user">
            {user} <button onClick={logout}>Выйти</button>
          </span>
        )}
      </header>
      <p className="lead">Черновик карточки товара для B2B-магазина по данным о контрольно-измерительном приборе.</p>

      {health?.error && <p className="error">{health.error}</p>}
      {health && !health.error && !health.llm_configured && (
        <p className="error">Ключ OpenAI не задан (OPENAI_API_KEY в .env) — генерация вернёт ошибку.</p>
      )}

      {user === undefined && <p>Проверяю вход…</p>}
      {user === false && <p className="error">Не удалось проверить вход: backend недоступен.</p>}
      {user === null && <Login onLogin={setUser} />}
      {user && <Generator onUnauthorized={() => setUser(null)} />}
    </main>
  );
}
