# El SDK se instala desde el repositorio de Flutter en una version fija, en lugar de usar una
# imagen publicada. Ningun registro publica Flutter 3.44.3, que es la version con la que se
# genero `pubspec.lock`: se comprobaron ghcr.io/cirruslabs/flutter en los tags 3.44.3,
# 3.44.3-sdk, 3.44 y 3.44.3-web, y docker.io/instrumentisto/flutter:3.44.3, y todos responden
# `manifest unknown`. Con una imagen `:stable` la version del SDK flota, y cada release de
# Flutter cambia los paquetes que el SDK fija (matcher, meta, test_api, vector_math), asi que
# `--enforce-lockfile` falla aunque nadie toque el `pubspec.yaml`.
FROM debian:bookworm-slim AS build
ARG BACKEND_URL=http://localhost:8000
ARG FLUTTER_VERSION=3.44.3

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates curl git unzip xz-utils zip \
 && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 --branch "${FLUTTER_VERSION}" \
      https://github.com/flutter/flutter.git /flutter
ENV PATH="/flutter/bin:${PATH}"

# `safe.directory` porque git se niega a operar sobre un repositorio de otro dueno, y Flutter
# usa git para resolver su propia version. `precache --web` descarga el SDK de Dart y los
# artefactos de web ahora, para que el build no dependa de una descarga a mitad de camino.
RUN git config --global --add safe.directory /flutter \
 && flutter precache --web

WORKDIR /app
COPY pubspec.* ./
RUN flutter pub get --enforce-lockfile
COPY . .
RUN flutter build web --release --dart-define=BACKEND_URL="${BACKEND_URL}"

FROM nginxinc/nginx-unprivileged:alpine
COPY --from=build /app/build/web /usr/share/nginx/html
USER nginx
EXPOSE 8080
