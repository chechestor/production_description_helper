import { useState } from "react";
import { api } from "./api.js";
import { EXAMPLES } from "./examples.js";

const NO_DATA = "данных нет";

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Запасной путь для небезопасного контекста (http не на localhost)
    const area = document.createElement("textarea");
    area.value = text;
    document.body.appendChild(area);
    area.select();
    const ok = document.execCommand("copy");
    area.remove();
    return ok;
  }
}

function Counter({ value, min, max }) {
  const n = value.length;
  const ok = (min === undefined || n >= min) && n <= max;
  const range = min === undefined ? `до ${max}` : `${min}–${max}`;
  return (
    <span className={ok ? "counter" : "counter bad"}>
      {n} симв. (нужно {range})
    </span>
  );
}

function List({ title, items, tone }) {
  if (!items?.length) return null;
  return (
    <section className={`notice ${tone}`}>
      <h3>{title}</h3>
      <ul>
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

function Result({ result }) {
  const { card, missing_fields: missing, warnings, markdown } = result;
  const [copied, setCopied] = useState("");

  async function copy(kind) {
    const text = kind === "md" ? markdown : JSON.stringify(card, null, 2);
    setCopied((await copyText(text)) ? `${kind === "md" ? "Markdown" : "JSON"} скопирован` : "Не удалось скопировать");
    setTimeout(() => setCopied(""), 2500);
  }

  return (
    <div className="result">
      <div className="actions">
        <button onClick={() => copy("md")}>Копировать Markdown</button>
        <button onClick={() => copy("json")}>Копировать JSON</button>
        <span className="copied" role="status">{copied}</span>
      </div>

      <List title="Недостающие данные" items={missing} tone="missing" />
      <List title="Предупреждения" items={warnings} tone="warning" />

      <section>
        <h3>
          SEO-заголовок <Counter value={card.seo_title} max={70} />
        </h3>
        <p className="title">{card.seo_title}</p>
      </section>

      <section>
        <h3>
          SEO-описание <Counter value={card.seo_description} min={800} max={1200} />
        </h3>
        <p className="description">{card.seo_description}</p>
      </section>

      <section>
        <h3>Ключевые характеристики</h3>
        <table>
          <thead>
            <tr>
              <th>Характеристика</th>
              <th>Значение</th>
            </tr>
          </thead>
          <tbody>
            {card.key_specs.map((spec, i) => {
              const noData = spec.value === NO_DATA;
              const unverified = !noData && !spec.verified;
              return (
                <tr key={i} className={noData ? "no-data" : unverified ? "unverified" : ""}>
                  <td>{spec.name}</td>
                  <td>
                    {spec.value}
                    {unverified && <span className="tag">не найдено во входных данных</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      <section>
        <h3>Поисковые запросы</h3>
        <ul>
          {card.search_queries.map((q, i) => (
            <li key={i}>{q}</li>
          ))}
        </ul>
      </section>

      <section>
        <h3>Для менеджера</h3>
        <div className="columns">
          <div>
            <h4>Кому подходит</h4>
            <ul>
              {card.commercial.audience.map((a, i) => (
                <li key={i}>{a}</li>
              ))}
            </ul>
          </div>
          <div>
            <h4>Какие задачи решает</h4>
            <ul>
              {card.commercial.tasks.map((t, i) => (
                <li key={i}>{t}</li>
              ))}
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}

export default function Generator({ onUnauthorized }) {
  const [input, setInput] = useState(EXAMPLES[0].text);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  async function generate() {
    setError(null);
    try {
      JSON.parse(input);
    } catch (e) {
      setError(`JSON в поле не разбирается: ${e.message}`);
      return;
    }
    setBusy(true);
    setResult(null);
    const response = await api("/api/generate", { method: "POST", body: input });
    setBusy(false);
    if (response.ok) setResult(response.data);
    else if (response.status === 401) onUnauthorized();
    else setError(response.error.message);
  }

  return (
    <>
      <section className="input">
        <div className="actions">
          {EXAMPLES.map((ex) => (
            <button key={ex.label} onClick={() => setInput(ex.text)} disabled={busy}>
              {ex.label}
            </button>
          ))}
        </div>
        <label htmlFor="product-json">Данные о товаре (JSON: name, manufacturer, specs, description)</label>
        <textarea
          id="product-json"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          spellCheck={false}
          rows={14}
        />
        <div className="actions">
          <button className="primary" onClick={generate} disabled={busy}>
            {busy ? "Генерирую…" : "Сгенерировать"}
          </button>
          {busy && <span className="spinner" aria-label="Идёт генерация" />}
        </div>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
      </section>
      {result && <Result result={result} />}
    </>
  );
}
