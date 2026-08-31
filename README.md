# Sistema de calificación automática de exámenes de cálculo diferencial mediante OMR

Proyecto que automatiza la calificación de exámenes de opción múltiple de cálculo diferencial. El profesor carga su banco de preguntas y su clave de respuestas, aplica el examen en papel y sube los escaneos; el sistema los lee mediante reconocimiento óptico de marcas (OMR), califica contra esa clave y publica los resultados en un dashboard, devolviendo a revisión manual toda marca que no supere el umbral de confianza. Como apoyo opcional durante la preparación, puede proponer **distractores diagnósticos** con ayuda de un modelo de lenguaje. El sistema es una herramienta de apoyo al criterio del profesor, no un reemplazo de su decisión final.

## Cómo se arranca

Requiere Docker (con el plugin Compose). Antes de la primera vez, copiar `.env.example` a `.env`;
no hace falta editarlo todavía (no hay credenciales reales), pero establece la convención de
RNF-11 para cuando las haya.

Desde la raíz del repositorio:

```
docker compose up
```

Levanta, con un solo comando, la aplicación web (FastAPI, puerto 8000), un worker que comparte
el mismo código de dominio que la API, la cola de trabajos (Redis), la base de datos (Postgres,
todavía sin esquema) y el frontend (Flutter compilado a estáticos, servido en el puerto 8080).
La primera construcción es lenta por el SDK de Flutter de la etapa de build del frontend; no
está colgado. Para reconstruir tras cambiar código: `docker compose up --build`.

- API: http://localhost:8000 (documentación interactiva en `/docs`, salud en `/health`).
- Frontend: http://localhost:8080.

Alternativas para desarrollo, que no reemplazan el comando oficial de arriba:
- Backend sin Docker: `docker compose up -d redis postgres` y luego, dentro de `backend/` con un
  entorno virtual, `pip install -r requirements.txt` y `uvicorn api.main:app --reload`.
- Frontend con recarga en caliente: dentro de `frontend/`,
  `flutter run -d chrome --dart-define=BACKEND_URL=http://localhost:8000`, sin reconstruir la
  imagen en cada cambio.

## Corte vertical: carga de examen (aspecto A-01)

Del sistema hay **un aspecto construido de punta a punta** y los demás solo declarados. Ese es
[A-01, la carga de examen para calificación](docs/aspectos.md#a-01), que realiza RF-01: el
docente sube las hojas escaneadas de un examen y el sistema le confirma cuáles recibió y cuáles
no, con el motivo de cada rechazo.

Se eligió construir este primero porque es el punto de entrada del flujo —sin una hoja cargada
no hay nada que calificar— y porque no depende de las partes de mayor riesgo técnico: no hace
falta haber elegido el algoritmo de OMR ni el umbral de confianza para que funcione.

El recorrido atraviesa todas las capas, que es lo que lo hace un corte vertical y no una capa
horizontal:

```
navegador (Flutter)  ->  POST /examenes/{id}/hojas  ->  ingesta         (valida formato)
                                                    ->  infraestructura (almacena y encola)
                                                    ->  worker          (desencola y registra)
```

### Cómo recorrerlo

Con el sistema levantado (`docker compose up --build`), crea dos archivos de prueba: uno válido
y otro que finja serlo.

```bash
# una imagen PNG valida de 8x8 pixeles (o usa cualquier foto, escaneo o PDF propio)
base64 -d > /tmp/hoja-real.png <<'FIN'
iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAEUlEQVR4nGOQqziBFTEMLQkABkZXgRDDjAEAAAAASUVORK5CYII=
FIN

# un archivo de texto al que solo se le puso extension .jpg
echo "esto no es una imagen" > /tmp/hoja-falsa.jpg
```

En `http://localhost:8080`, escribe un identificador de examen (por ejemplo `CALC-2026-01`),
selecciona los dos archivos y súbelos. La respuesta separa lo recibido de lo rechazado:

```
Se procesaron 2 archivo(s)
Recibidas: 1
  hoja-real.png    En cola · trabajo 2eede6b8-dd9f-4db6-a3ab-6205644ea416
Rechazadas: 1
  hoja-falsa.jpg   El contenido no corresponde a un JPG; puede que el archivo
                   esté dañado o que se le haya cambiado la extensión.
```

Ese rechazo es el que muestra que la validación **lee los primeros bytes y no la extensión**: el
archivo se llama `.jpg` y aun así no pasa. Comprobarlo importa porque un archivo que se cuela
por tener el nombre correcto reaparece como error dentro del worker, cuando ya no hay a quién
avisarle.

Para ver el otro extremo del recorrido:

```
docker compose logs worker
```

```
Hoja recibida | trabajo=2eede6b8-dd9f-4db6-a3ab-6205644ea416 examen=CALC-2026-01
               archivo=hoja-real.png referencia=CALC-2026-01/e6c7e4cc-...-hoja-real.png
```

El identificador de trabajo es el mismo que muestra la pantalla. Esa coincidencia es la prueba
de que el recorrido se completó: la hoja pasó del navegador a la API, de ahí al volumen de
imágenes y a la cola de Redis, y de ahí a un proceso distinto en otro contenedor.

### Qué falta de este aspecto

El worker registra la hoja y ahí termina, porque el paso siguiente es el aspecto A-02 (detección
de marcas), que todavía no existe. La política de retención de imágenes que exige RNF-14 tampoco
está implementada: hoy nada borra lo que se guarda.

El almacenamiento está **detrás de un puerto** en `infraestructura`, con un adaptador en disco
declarado provisional. Es deliberado: el corte necesitaba guardar archivos sin cerrar de paso la
decisión de persistencia, que sigue abierta como riesgo R-06 del arc42. Cuando se escriba ese
ADR, lo que cambia es el adaptador; `ingesta`, el modelo de datos y las pruebas del aspecto no
se tocan.

## Cómo se prueba

Backend (dentro de `backend/`, con Redis disponible vía `docker compose up -d redis` o local):

```
pytest
```

Son 34 pruebas. Verifican: que la aplicación FastAPI arranca y su endpoint de salud responde
200; que los siete módulos del dominio se importan sin error ni ciclos; que ningún módulo
importa por fuera de lo declarado en el docstring de su `__init__.py` (la prueba de fronteras
entre módulos); que un trabajo encolado en Redis se recupera igual al desencolarlo; y, para el
aspecto A-01, que se aceptan los formatos declarados, que cada rechazo lleva motivo legible, que
ningún archivo del lote desaparece del reporte, que se encola un trabajo por hoja aceptada y
ninguno por rechazada, y que un nombre de archivo con rutas no escapa del directorio del examen.

Sin Redis levantado, la prueba de encolado se salta con un mensaje que dice qué levantar, en vez
de fallar con un error de conexión confuso. Las demás corren igual.

Frontend (dentro de `frontend/`):

```
flutter test
```

Son 6 pruebas de widget. Verifican que la pantalla de inicio refleja el estado de conexión con
el backend y que no ofrece cargar hojas si el backend no responde; y, sobre la pantalla de
carga, que el botón de subir sigue deshabilitado hasta que haya examen y archivos, que el
reporte lista las aceptadas y las rechazadas con su motivo, y que una falla de red se muestra
como aviso y no como rechazo.

Ninguna toca la red ni el diálogo de archivos del navegador: la pantalla recibe esas dos
operaciones inyectadas y las pruebas les pasan sustitutos.

Estas mismas pruebas corren en cada push y pull request vía `.github/workflows/ci.yml`.

## Restricciones y decisiones clave

Las restricciones completas, clasificadas en técnicas, organizativas y legales, están en la [sección 2 del arc42](docs/arc42/arc42-template-ES.md). Las principales:

- Solo evalúa exámenes de opción múltiple con hoja de respuestas de formato fijo; no procesa desarrollo libre.
- Dominio acotado a cálculo diferencial: límites, derivadas y simplificaciones algebraicas.
- Usuarios: profesores y TAs autenticados. El estudiante no interactúa con el sistema, solo es la fuente de las marcas en la hoja.
- Los resultados se presentan en un dashboard interactivo, no como archivo aislado ni salida de consola.
- Las calificaciones y los escaneos son datos personales de estudiantes: su tratamiento se rige por el régimen colombiano de protección de datos, y ningún dato personal se envía al proveedor de LLM.
- El stack está limitado a las opciones del curso. Se eligió FastAPI en el backend, porque el ecosistema de OpenCV solo existe con madurez en Python, y Flutter en el frontend, por la experiencia previa del equipo.
- El modelo de lenguaje no participa en la calificación: es una capacidad de apoyo de la fase de autoría, y el sistema funciona completo sin invocarla ([ADR-0005](docs/adr/0005-acotar-el-llm-a-la-generacion-de-distractores-diagnosticos.md)).

## Objetivos de calidad

- **Precisión:** ≥98% de exactitud en la detección de marcas OMR; 100% de los exámenes habilitados con aprobación manual registrada de la clave de respuestas.
- **Rendimiento:** ≤5 segundos por examen individual (percentil 95); requiere procesamiento en paralelo, no secuencial, para que un lote de 200 hojas quepa en ≤10 minutos.
- **Degradación controlada:** toda marca con confianza <70% se envía a revisión manual; el sistema detecta correctamente ≥99% de esos casos ambiguos.
- **Seguridad:** un profesor solo accede a los datos de los cursos que tiene autorizados.

## Metodología

El desarrollo sigue Aspect Driven Development (ADD): cada funcionalidad se declara como un aspecto que se puede trazar de principio a fin, desde el requisito hasta la evidencia de que funciona (ver [`docs/aspectos.md`](docs/aspectos.md)).

## Decisiones de arquitectura

| ADR | Título | Estado |
|---|---|---|
| [0001](docs/adr/0001-usar-monolito-modular.md) | Arquitectura de Monolito Modular | reemplazado por 0002 |
| [0002](docs/adr/0002-procesar-calificacion-de-forma-asincrona.md) | Procesar la calificación de forma asíncrona sobre el monolito modular | aceptado |
| [0003](docs/adr/0003-usar-fastapi-y-flutter.md) | Usar FastAPI en el backend y Flutter en el frontend | aceptado |
| [0004](docs/adr/0004-quitar-validacion-simbolica-obligatoria-de-la-clave.md) | Quitar la validación simbólica obligatoria de la clave de respuestas | aceptado |
| [0005](docs/adr/0005-acotar-el-llm-a-la-generacion-de-distractores-diagnosticos.md) | Acotar el LLM a la generación de distractores diagnósticos | aceptado |

Los ADR aceptados no se editan ni se borran: si una decisión cambia, se escribe uno nuevo y el anterior pasa a estado *reemplazado por*.

## Estado actual

- [x] Aspecto A-01 (carga de examen) construido de punta a punta; A-02 a A-05 declarados
- [x] arc42: objetivos de calidad, restricciones clasificadas y contexto
- [x] arc42: estrategia de solución, decisiones de arquitectura y riesgos
- [x] Escenarios de calidad: 5 priorizados y 2 complementarios
- [x] C4 Nivel 1
- [x] ADR 0001, 0002, 0003, 0004 y 0005
- [x] Elección de stack: FastAPI en el backend, Flutter en el frontend
- [ ] arc42: Building Block View, Runtime View, Deployment View, Cross-cutting Concepts
- [ ] C4 Niveles 2 y 3
- [x] Esqueleto ejecutable
- [x] Corte vertical de A-01: `ingesta`, almacén, encolado y pantalla de carga
- [ ] ADR de persistencia y almacenamiento (riesgo R-06); el adaptador actual es provisional
- [ ] Modelo de datos compartido más allá de lo que A-01 necesitó
- [ ] Elección de proveedor de LLM
- [ ] Aspectos A-02 a A-05

## Documentación

```
docs/
├── arc42/
│   └── arc42-template-ES.md                            # documento de arquitectura (arc42)
├── adr/
│   ├── 0001-usar-monolito-modular.md                   # reemplazado por 0002
│   ├── 0002-procesar-calificacion-de-forma-asincrona.md
│   ├── 0003-usar-fastapi-y-flutter.md
│   ├── 0004-quitar-validacion-simbolica-obligatoria-de-la-clave.md
│   └── 0005-acotar-el-llm-a-la-generacion-de-distractores-diagnosticos.md
├── c4/
│   └── doc-c4.md                                       # modelo C4 (Nivel 1; 2-3 pendientes)
├── ficha-problema.md                                    # el problema, usuarios y alcance
├── aspectos.md                                         # aspectos y tabla de trazabilidad
└── ia.md                                               # registro de uso de IA
```
