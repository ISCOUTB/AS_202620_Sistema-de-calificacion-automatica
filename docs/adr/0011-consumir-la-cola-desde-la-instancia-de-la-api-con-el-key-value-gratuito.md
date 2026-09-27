# 0011 · Consumir la cola desde la instancia de la API con el Key Value gratuito

- **Estado:** aceptado
- **Fecha:** 2026-09-27
- **Decide:** Josué Ortega De Arco, María Restrepo Licona, Sebastián Cañas Plata, Susana Rosales Castellar
- **Escenario de calidad relacionado:** ninguno directo. Responde a la restricción de costo (costo mensual de US$0 y ninguna cuenta con tarjeta)
- **Relación con otros ADR:** precisa, sin reemplazar, a [ADR-0002](0002-procesar-calificacion-de-forma-asincrona.md), que eligió una cola persistente: en el entorno de demostración la cola no persiste (ver Consecuencias). Lo que pasa con una hoja cuando la cola no la acepta sigue siendo lo que define [ADR-0006](0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md)

**La decisión, en una frase:** el worker corre como segundo proceso dentro de la misma instancia de la API (`backend/arrancar-api-y-worker.sh`), y la cola de trabajos es el Key Value gratuito de Render (`quantia-utb-cola`).

## Contexto

Esta es la pieza «los trabajos programados y los consumidores de cola» de la guía de despliegue, que los marca como candidatos a función «con idempotencia». Render tiene planes gratuitos para servicios web, sitios estáticos, Key Value y Postgres, pero no para *background workers*. El worker de hoy tampoco es idempotente (eso es tema del taller de la semana 12), así que llevarlo a una función quedaría a medias. La cola, además, necesita un servicio al que la API y el worker puedan conectarse los dos.

## Alternativas consideradas

- **El worker como *background worker* de Render**: no existe plan gratuito para ese tipo de servicio; el más barato cuesta US$7 al mes, lo que rompe la restricción de costo del proyecto.
- **El consumidor reescrito como función**: la guía lo acepta, pero solo «con idempotencia», y el worker de hoy no lo es. Resolverlo ahora exigiría adelantar los reintentos duplicados, que es el tema del taller de la semana 12.
- **La cola en Upstash**: su plan gratuito da 500 000 comandos al mes (fuente: https://upstash.com/docs/redis/overall/pricing, consultada el 26-sep-2026), pero el worker hace una `BLPOP` cada 5 segundos incluso sin carga: 518 400 comandos en un mes de 30 días o 535 680 en uno de 31, más que el cupo gratuito solo por esperar.
- **Redis en el servidor del laboratorio**: sus datos operativos siguen en `POR_CONFIRMAR`, incluido si responde desde fuera de la universidad, así que no es una base confiable para esta decisión todavía.
- **Key Value gratuito de Render (elegida)**: 25 MB y 50 conexiones, accesible solo por red privada (fuente: https://render.com/pricing, consultada el 27-sep-2026).

## Decisión

El worker se ejecuta como segundo proceso de la misma instancia de la API, reiniciado por un ciclo en `backend/arrancar-api-y-worker.sh` si termina. La cola de trabajos es el Key Value gratuito de Render (`quantia-utb-cola`), accesible solo por red privada (`ipAllowList: []`), con política `noeviction`.

## Consecuencias

- El worker comparte 0,1 CPU y 512 MB con la API, en vez de tener recursos propios.
- El Key Value gratuito no persiste: un reinicio del servicio vacía la cola por completo. En este entorno se aparta de la cola persistente que eligió ADR-0002: un trabajo que ya estaba en la cola se pierde si el Key Value se reinicia antes de que el worker lo tome. El worker lo toma en cuanto llega, así que la ventana es mínima, pero la recuperación ante fallos que ADR-0002 promete no vale aquí. La bitácora, que sí la cubre, vive en el disco efímero de la instancia (ADR-0012).
- Con `noeviction`, si la cola se llena, las escrituras nuevas fallan y la hoja queda en estado `pendiente_de_encolar`, tal como ya lo define [ADR-0006](0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md): `publicar` convierte cualquier error de Redis en `ColaNoDisponible`.
- Reversión: si la cola deja de servir, el respaldo es Redis en el servidor del laboratorio (una vez se confirme su disponibilidad) o pasar al Key Value de pago de Render (US$10 al mes, 256 MB, con persistencia en disco; https://render.com/pricing, consultada el 27-sep-2026); ninguna de las dos exige cambiar el código, solo la variable `REDIS_URL`.
- Llevar el consumidor a una función se reconsidera cuando el worker sea idempotente, que es el tema del taller de la semana 12.

## Trazabilidad

[`render.yaml`](../../render.yaml) · [`backend/arrancar-api-y-worker.sh`](../../backend/arrancar-api-y-worker.sh) · [ADR-0002](0002-procesar-calificacion-de-forma-asincrona.md) · [ADR-0006](0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md) · [ADR-0009](0009-desplegar-la-api-en-el-servicio-web-gratuito-de-render-y-mantenerla-despierta.md) · [arc42 §7 Deployment View](../arc42/arc42-template-ES.md#7-deployment-view)
