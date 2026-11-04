// Запросы к backend по относительному пути /api/… (в контейнере проксирует nginx).
export async function api(path, { method = "GET", body } = {}) {
  let response;
  try {
    response = await fetch(path, {
      method,
      credentials: "same-origin",
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : typeof body === "string" ? body : JSON.stringify(body),
    });
  } catch {
    return { ok: false, status: 0, error: { code: "network", message: "Backend недоступен" } };
  }
  let data = null;
  try {
    data = await response.json();
  } catch {
    // не JSON — например, 502 от nginx
  }
  if (!response.ok) {
    const fallback = [502, 503, 504].includes(response.status)
      ? `Backend недоступен (HTTP ${response.status})`
      : `Ошибка сервера (HTTP ${response.status})`;
    const error = data?.error ?? { code: `http_${response.status}`, message: fallback };
    return { ok: false, status: response.status, error };
  }
  return { ok: true, status: response.status, data };
}
