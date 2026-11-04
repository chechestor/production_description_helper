# Сборка из корня репозитория (context: .): в образ сборки попадают examples/input/,
# их подключают кнопки примеров (frontend/src/examples.js)
FROM node:22-alpine AS build
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY examples/input/ /build/examples/input/
COPY frontend/ ./
RUN npm run build

FROM nginx:1.29-alpine
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /build/frontend/dist /usr/share/nginx/html
EXPOSE 80
