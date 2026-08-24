FROM ghcr.io/cirruslabs/flutter:stable AS build
ARG BACKEND_URL=http://localhost:8000
WORKDIR /app
COPY pubspec.* ./
RUN flutter pub get
COPY . .
RUN flutter build web --release --dart-define=BACKEND_URL=${BACKEND_URL}

FROM nginx:alpine
COPY --from=build /app/build/web /usr/share/nginx/html
EXPOSE 80
