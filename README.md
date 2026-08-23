# Sistema de calificación automática de exámenes de cálculo diferencial mediante OMR, LLM y SymPy

Proyecto que automatiza la calificación de exámenes de opción múltiple de cálculo diferencial: reconocimiento óptico de marcas (OMR) para leer las hojas de respuesta escaneadas, modelos de lenguaje y computación simbólica con SymPy para validar la clave de respuestas, y un dashboard donde el profesor revisa los resultados y los casos marcados como ambiguos. El sistema está pensado como herramienta de apoyo al criterio del profesor, no como reemplazo de su decisión final.

## Cómo se arranca

Todavía no hay código para instalar ni ejecutar (el proyecto sigue en etapa de arquitectura, ver Estado actual abajo). Esta sección se completa en cuanto exista el primer contenedor implementado.

## Cómo se prueba

Por la misma razón, tampoco hay pruebas que correr todavía. Se documenta aquí en cuanto la fila de A-01 en la tabla de trazabilidad (ver `docs/aspectos.md`) deje de decir "Pendiente" en las columnas Código y Pruebas.

## Restricciones y decisiones clave

Las restricciones completas, clasificadas en técnicas, organizativas y legales, están en la [sección 2 del arc42](docs/arc42/arc42-template-ES.md). Las principales:

- Solo evalúa exámenes de opción múltiple con hoja de respuestas de formato fijo; no procesa desarrollo libre.
- Dominio acotado a cálculo diferencial: límites, derivadas y simplificaciones algebraicas.
- Usuarios: profesores y TAs autenticados. El estudiante no interactúa con el sistema, solo es la fuente de las marcas en la hoja.
- Los resultados se presentan en un dashboard interactivo, no como archivo aislado ni salida de consola.
- Las calificaciones y los escaneos son datos personales de estudiantes: su tratamiento se rige por el régimen colombiano de protección de datos, y ningún dato personal se envía al proveedor de LLM.

## Objetivos de calidad

- **Precisión:** ≥98% de exactitud en la detección de marcas OMR; validación de clave 100% libre de ambigüedad algebraica.
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

Los ADR aceptados no se editan ni se borran: si una decisión cambia, se escribe uno nuevo y el anterior pasa a estado *reemplazado por*.

## Estado actual

- [x] Aspecto A-01 (carga de examen) especificado; A-02 a A-05 declarados
- [x] arc42: objetivos de calidad, restricciones clasificadas y contexto
- [x] arc42: estrategia de solución, decisiones de arquitectura y riesgos
- [x] Escenarios de calidad: 5 priorizados y 2 complementarios
- [x] C4 Nivel 1
- [x] ADR 0001 y 0002
- [ ] arc42: Building Block View, Runtime View, Deployment View, Cross-cutting Concepts
- [ ] C4 Niveles 2 y 3
- [ ] Elección de stack y de proveedor de LLM
- [ ] Código

## Documentación

```
docs/
├── arc42/
│   └── arc42-template-ES.md                            # documento de arquitectura (arc42)
├── adr/
│   ├── 0001-usar-monolito-modular.md                   # reemplazado por 0002
│   └── 0002-procesar-calificacion-de-forma-asincrona.md
├── c4/
│   └── doc-c4.md                                       # modelo C4 (Nivel 1; 2-3 pendientes)
├── aspectos.md                                         # aspectos y tabla de trazabilidad
└── ia.md                                               # registro de uso de IA
```
