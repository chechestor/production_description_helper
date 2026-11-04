import { useEffect, useState } from "react";

// Заглушка F002: название сервиса и результат GET /api/health.
// Форму входа добавит F003, основной экран — F009.
export default function App() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setHealth)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", maxWidth: 720, margin: "40px auto", padding: "0 16px" }}>
      <h1>Production Description Helper</h1>
      <p>Черновик карточки товара для B2B-магазина по данным о приборе.</p>
      <h2>Состояние backend</h2>
      {error && <p style={{ color: "#b00020" }}>Backend недоступен: {error}</p>}
      {!error && !health && <p>Проверяю…</p>}
      {health && (
        <ul>
          <li>Статус: {health.status}</li>
          <li>Ключ LLM: {health.llm_configured ? "задан" : "не задан"}</li>
        </ul>
      )}
    </main>
  );
}
