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

## Cómo se prueba

Backend (dentro de `backend/`, con Redis disponible vía `docker compose up -d redis` o local):

```
pytest
```

Verifica: que la aplicación FastAPI arranca y su endpoint de salud responde 200; que los siete
módulos del dominio se importan sin error ni ciclos; que ningún módulo importa por fuera de lo
declarado en el docstring de su `__init__.py` (la prueba de fronteras entre módulos); y que un
trabajo encolado en Redis se recupera igual al desencolarlo.

Frontend (dentro de `frontend/`):

```
flutter test
```

Verifica que la única pantalla muestra el nombre del sistema y refleja el estado de conexión con
el backend.

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

- [x] Aspecto A-01 (carga de examen) especificado; A-02 a A-05 declarados
- [x] arc42: objetivos de calidad, restricciones clasificadas y contexto
- [x] arc42: estrategia de solución, decisiones de arquitectura y riesgos
- [x] Escenarios de calidad: 5 priorizados y 2 complementarios
- [x] C4 Nivel 1
- [x] ADR 0001, 0002, 0003, 0004 y 0005
- [x] Elección de stack: FastAPI en el backend, Flutter en el frontend
- [ ] arc42: Building Block View, Runtime View, Deployment View, Cross-cutting Concepts
- [ ] C4 Niveles 2 y 3
- [x] Esqueleto ejecutable
- [ ] Elección de proveedor de LLM
- [ ] Código

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
├── Ficha-problema.md                                   # el problema, usuarios y alcance
├── aspectos.md                                         # aspectos y tabla de trazabilidad
└── ia.md                                               # registro de uso de IA
```
