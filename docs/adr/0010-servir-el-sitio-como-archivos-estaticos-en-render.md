# 0010 · Servir el sitio como archivos estáticos en Render

- **Estado:** aceptado
- **Fecha:** 2026-09-27
- **Decide:** Josué Ortega De Arco, María Restrepo Licona, Sebastián Cañas Plata, Susana Rosales Castellar
- **Escenario de calidad relacionado:** ninguno directo. Responde a la restricción de costo RNF-16 (costo mensual de US$0 y ninguna cuenta con tarjeta)
- **Relación con otros ADR:** no reemplaza ni precisa a ninguno; parte de [ADR-0003](0003-usar-fastapi-y-flutter.md), que eligió Flutter compilado a web

**La decisión, en una frase:** el frontend de QuantIA se publica como *Static Site* de Render (`quantia-utb`), declarado en `render.yaml` junto con la API y la cola.

## Contexto

Esta es la pieza «el sitio o la interfaz que ve el usuario» de la guía de despliegue y costos, que describe un sitio estático o SPA como el caso más simple y el más barato, sin nada que arrancar, y nombra como opciones habituales GitHub Pages, Cloudflare Pages y Netlify. En este proyecto pesa además un número concreto: el arranque en frío medido de un servicio web gratuito de este mismo workspace (la API, [ADR-0009](0009-desplegar-la-api-en-el-servicio-web-gratuito-de-render-y-mantenerla-despierta.md)) es de 12,5 s, y esa misma API ya usa entre 720 y 744 de las 750 horas de instancia compartidas del workspace por mantenerse despierta con un monitor. Cualquier segundo servicio web que también quede despierto compite por ese mismo cupo.

## Alternativas consideradas

- **Servicio web gratuito con nginx** (`frontend/Dockerfile`, la imagen que ya usa el entorno local): se apagaría a los 15 minutos sin tráfico igual que la API, y el primer visitante después de una pausa enfrentaría un arranque en frío del orden de los 12,5 s medidos. Gastaría además horas del mismo cupo compartido de 750, que la API ya consume casi por completo con su monitor: con los dos servicios despiertos todo el mes, el cupo se agota antes de terminar.
- **GitHub Pages**: la guía la nombra y es gratis en repositorios públicos, pero exige activar Pages en la configuración del repositorio y agregar un job de publicación nuevo al pipeline. El *Static Site* de Render, en cambio, queda declarado en el mismo `render.yaml` que la API y la cola: un solo archivo recrea el entorno completo.
- **Render Static Site (elegida)**: la página de precios de Render lo describe como «Always free to deploy», con CDN y despliegue automático desde Git (fuente: https://render.com/pricing, consultada el 27-sep-2026).

## Decisión

El sitio se sirve como *Static Site* de Render, servicio `quantia-utb`. Render lo compila directamente desde `frontend/` con Flutter 3.44.3 (la misma versión fijada en el CI) y publica `frontend/build/web`, con la URL pública de la API horneada como `BACKEND_URL` al momento de compilar. La API, a su vez, solo acepta peticiones del origen del sitio (`ALLOWED_ORIGIN`).

## Consecuencias

- La URL de la API queda horneada en el sitio al compilar: si cambia, hay que reconstruir el sitio y actualizar `ALLOWED_ORIGIN`.
- El sitio depende del CDN de Google (`www.gstatic.com`) para CanvasKit, el motor de dibujo de Flutter (2,2 a 2,9 MB comprimido), que Render no sirve.
- Punto de ruptura: 5 GB de ancho de banda al mes (fuente: https://render.com/pricing, consultada el 27-sep-2026). Medido sobre el sitio desplegado, una primera visita pesa unos 0,75 MB servidos por Render (`main.dart.js` en 0,72 MB comprimido con brotli, más index.html y manifiestos), lo que da margen para unas 6600 primeras visitas al mes antes de pagar US$0,15 por GB adicional. El otro límite son los 500 minutos de build al mes (US$5 por cada 1000 adicionales, misma fuente), y el sitio solo se reconstruye cuando cambia `frontend/`. Con un docente por curso cargando exámenes en fechas de corte puntuales, el volumen real queda lejos de ese punto.
- Reversión: la imagen de `frontend/Dockerfile` ya existe y funciona en el entorno local, así que volver a un servicio web es cambiar el tipo de servicio en `render.yaml`. Render conserva además los últimos 5 despliegues del sitio para revertir a uno anterior.
- El sitio solo se reconstruye si el CI del commit termina en verde (`autoDeployTrigger: checksPass`) y si el cambio tocó algo dentro de `frontend/` (`buildFilter`).

## Trazabilidad

[`render.yaml`](../../render.yaml) · [`frontend/Dockerfile`](../../frontend/Dockerfile) · [ADR-0009](0009-desplegar-la-api-en-el-servicio-web-gratuito-de-render-y-mantenerla-despierta.md) · [arc42 §7 Deployment View](../arc42/arc42-template-ES.md#7-deployment-view)
