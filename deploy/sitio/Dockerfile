# El sitio de QuantIA en el servidor del laboratorio: Flutter web ya compilado, servido por nginx.
#
# Aquí no se compila Flutter. Su imagen ocupa unos 3 GB y el servidor tiene 2 compilaciones para
# 23 equipos, así que el manual del servidor pide no hacerlo ahí. El job `publicar-despliegue` de
# `.github/workflows/ci.yml` compila el sitio después de las pruebas y lo deja en `web/`, en la
# rama `despliegue`, que es la que lee el servidor.
#
# En `master` esa carpeta solo tiene un `.gitkeep` (lo demás está en .gitignore), y el compose
# tiene que levantar igual en limpio: por eso primero se copia una página provisional que lo
# explica, y después el sitio compilado encima, que en `master` no es nada. Las dos carpetas se
# copian por su nombre, sin comodines, y `.dockerignore` no deja entrar nada más a la imagen. Para
# ver el sitio de verdad en local, compílalo antes como dice deploy/compose.local-override.yaml.
#
# La misma imagen base que frontend/Dockerfile, que es el sitio del entorno local.
FROM nginxinc/nginx-unprivileged:alpine
COPY provisional/ /usr/share/nginx/html/
COPY web/ /usr/share/nginx/html/
EXPOSE 8080
