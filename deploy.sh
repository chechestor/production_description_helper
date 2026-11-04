#!/usr/bin/env bash
# Перезапуск проекта на этой машине: остановить контейнеры, обновить исходники
# из репозитория (git pull --ff-only), поднять все контейнеры заново.
# Данные в data/ не трогаются. На Windows запускать из Git Bash или WSL.
set -euo pipefail

cd "$(dirname "$0")"

fail() {
  echo "Ошибка: $*" >&2
  exit 1
}

# 1. Предпроверки — до остановки контейнеров
docker compose version >/dev/null 2>&1 \
  || fail "не найден docker compose. Установите Docker с Compose v2."

[ -f .env ] \
  || fail "нет файла .env. Скопируйте .env.example в .env и впишите OPENAI_API_KEY."

command -v git >/dev/null 2>&1 || fail "не найден git."

if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "Есть незакоммиченные изменения в отслеживаемых файлах:" >&2
  git status --short --untracked-files=no >&2
  fail "закоммитьте или отмените их и запустите скрипт снова."
fi

# Порты для вывода адресов: только эти переменные, ключ и пароли не читаются
env_value() {
  local value
  value="$(grep -E "^$1=" .env | tail -n 1 | cut -d= -f2- | tr -d '\r' || true)"
  echo "${value:-$2}"
}
FRONTEND_PORT="$(env_value FRONTEND_PORT 3000)"
BACKEND_PORT="$(env_value BACKEND_PORT 8000)"
PHOENIX_PORT="$(env_value PHOENIX_PORT 6006)"

# 2. Остановить контейнеры проекта (без -v: data/ и тома не трогаются)
echo "Останавливаю контейнеры..."
docker compose down

# 3. Обновить исходники
echo "Обновляю исходники (git pull --ff-only)..."
pull_failed=0
git pull --ff-only || pull_failed=1

# 4. Поднять все контейнеры заново
echo "Поднимаю контейнеры..."
docker compose up -d --build

# 5. Состояние и адреса
docker compose ps
echo
echo "UI:         http://localhost:${FRONTEND_PORT}"
echo "API:        http://localhost:${BACKEND_PORT}/api/health"
echo "Phoenix UI: http://localhost:${PHOENIX_PORT}"

if [ "$pull_failed" -ne 0 ]; then
  echo >&2
  fail "исходники НЕ обновлены (git pull не удался), поднята прежняя версия."
fi
