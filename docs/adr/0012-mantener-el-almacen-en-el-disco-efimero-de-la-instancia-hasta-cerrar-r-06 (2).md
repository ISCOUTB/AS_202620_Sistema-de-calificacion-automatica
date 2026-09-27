# 0012 · Mantener el almacén en el disco efímero de la instancia hasta cerrar R-06

- **Estado:** aceptado
- **Fecha:** 2026-09-27
- **Decide:** Josué Ortega De Arco, María Restrepo Licona, Sebastián Cañas Plata, Susana Rosales Castellar
- **Escenario de calidad relacionado:** [EC-07](../arc42/arc42-template-ES.md#ec-07) (0 % de pérdida silenciosa), que en este entorno se cumple solo dentro del proceso vivo
- **Restricción que acota:** R-06 (deuda: no hay decisión de persistencia ni de almacenamiento de imágenes), RNF-12, RNF-14, RNF-16
- **Relación con otros ADR:** no reemplaza ni precisa a ninguno; R-06 sigue abierto después de esta decisión

**La decisión, en una frase:** en el entorno de demostración, las hojas escaneadas y la bitácora de recepción quedan en el disco efímero de la instancia de la API, y se acepta ese riesgo solo porque ahí no entran datos reales y porque R-06 sigue abierto.

---

## Contexto

La «Guía de despliegue y costos» del curso es explícita: «Ficheros y objetos: Almacenamiento de objetos, nunca el disco […] lo que escribas ahí desaparece en el siguiente despliegue», y entre los errores frecuentes que busca el revisor está «guardar ficheros en el disco del contenedor». Este ADR no ignora esa regla: la reconoce y explica por qué, solo para esta demostración puntual, el equipo la incumple de forma acotada.

`AlmacenEnDisco` y `BitacoraEnDisco` (ADR-0006) ya escriben en disco. El plan gratuito de Render no ofrece disco persistente: `quantia-utb-api` pierde cualquier archivo cuando la instancia se reemplaza, en cada despliegue y en cada reinicio ([ADR-0009](0009-desplegar-la-api-en-el-servicio-web-gratuito-de-render-y-mantenerla-despierta.md)). R-06 sigue abierto desde ADR-0006, y también fija la retención de RNF-14.

## Alternativas consideradas

**A. Disco persistente de Render.** Solo existe en instancias de pago: US$0,25 por GB al mes, sobre una instancia Starter de US$7 al mes que además exige tarjeta (capa gratuita de Render, https://render.com/pricing, consultada el 27-sep-2026). Incumple RNF-16 (costo US$0, sin tarjeta).

**B. Almacenamiento de objetos.** Es la alternativa que la guía prefiere. Dos opciones evaluadas, consultadas el 27-sep-2026, sin verificar todavía si alguna pide tarjeta:

| Opción | Capa gratuita | Fuente |
|---|---|---|
| Supabase Storage | 1 GB de archivos, hasta 50 MB por archivo, 5 GB de salida; el proyecto gratuito se pausa tras 1 semana sin uso | https://supabase.com/pricing |
| Backblaze B2 | 10 GB gratis; después US$6,95 por TB al mes | https://www.backblaze.com/cloud-storage/pricing |

Se descarta para esta semana porque exige un adaptador nuevo detrás del puerto `AlmacenDeImagenes` (`backend/infraestructura/almacen.py`), con credenciales, acceso y ciclo de vida propios: es la decisión que R-06 tiene pendiente. Esa decisión incluye la retención de RNF-14 y el manejo de las credenciales del proveedor, y ninguna de las dos opciones tiene todavía verificado si pide tarjeta: se toma en el ADR que cierre R-06, no aquí.

## Decisión

1. `AlmacenEnDisco` y `BitacoraEnDisco` siguen escribiendo, sin cambios de código, sobre el disco efímero de `quantia-utb-api`.
2. Se acepta por dos razones: **(1)** el entorno de demostración solo recibe **hojas sintéticas** (RNF-12); la guía es igual de explícita: «nada de datos personales reales, ni en el repositorio ni en el entorno desplegado»; **(2)** migrar a objetos es la decisión de R-06, que también fija la retención (RNF-14), y no se toma en este ADR.
3. R-06 sigue abierto.

## Consecuencias

**Positivas:** el sistema se despliega dentro de la capa gratuita, sin tarjeta ni costo mensual (RNF-16), reutilizando el código y las pruebas de A-01 sin modificarlos.

**Negativas:** lo cargado se pierde en cada despliegue y reinicio de la instancia. EC-07 («0 % de pérdida») se cumple dentro de un proceso vivo, no entre reinicios; quien evalúe el sistema debe saberlo, y queda declarado en el README y en el arc42 §7.

**Qué dato haría revisar esta decisión:** que el sistema necesite conservar hojas entre despliegues, para una demostración prolongada o un uso con datos reales. Ese día se toma el ADR de persistencia definitiva que R-06 tiene pendiente, verificando antes si Supabase Storage o Backblaze B2 piden tarjeta, y el cambio queda detrás de los mismos puertos, sin tocar `ingesta` ni el modelo de datos.

## Trazabilidad

- **Restricción que acota:** R-06 ([arc42 §11](../arc42/arc42-template-ES.md#11-risks-and-technical-debts)), RNF-12 y RNF-14 ([arc42 §2.3](../arc42/arc42-template-ES.md#23-restricciones-legales)), RNF-16 ([arc42 §2.2](../arc42/arc42-template-ES.md#22-restricciones-organizativas)).
- **ADR relacionados, no modificados:** [ADR-0006](0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md), cuyos adaptadores en disco sostienen esta decisión sin cambios, y [ADR-0009](0009-desplegar-la-api-en-el-servicio-web-gratuito-de-render-y-mantenerla-despierta.md), que decide la instancia donde vive ese disco.
- **Código:** el puerto `AlmacenDeImagenes` en [`backend/infraestructura/almacen.py`](../../backend/infraestructura/almacen.py); la instancia, en [`render.yaml`](../../render.yaml).
- **Documentos afectados:** `README.md` («Entorno desplegado»), [arc42 §7](../arc42/arc42-template-ES.md#7-deployment-view) (Deployment View) y §11 (fila R-06).
