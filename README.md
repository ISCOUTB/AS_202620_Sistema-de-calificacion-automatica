# Sistema de calificación automática de exámenes de cálculo diferencial mediante OMR, LLM y SymPy

Proyecto que automatiza la calificación de exámenes de opción múltiple de cálculo diferencial: reconocimiento óptico de marcas (OMR) para leer las hojas de respuesta escaneadas, modelos de lenguaje y computación simbólica con SymPy para validar la clave de respuestas, y un dashboard donde el profesor revisa los resultados y los casos marcados como ambiguos. El sistema está pensado como herramienta de apoyo al criterio del profesor, no como reemplazo de su decisión final.

## Cómo se arranca

Todavía no hay código para instalar ni ejecutar (el proyecto sigue en etapa de arquitectura, ver Estado actual abajo). Esta sección se completa en cuanto exista el primer contenedor implementado.

## Cómo se prueba

Por la misma razón, tampoco hay pruebas que correr todavía. Se documenta aquí en cuanto la fila de A-01 en la tabla de trazabilidad (ver `docs/aspectos.md`) deje de decir "Pendiente" en las columnas Código y Pruebas.

## Restricciones y decisiones clave

- Solo evalúa exámenes de opción múltiple con hoja de respuestas de formato fijo; no procesa desarrollo libre.
- Dominio acotado a cálculo diferencial: límites, derivadas y simplificaciones algebraicas.
- Usuarios: profesores y TAs autenticados. El estudiante no interactúa con el sistema, solo es la fuente de las marcas en la hoja.
- Los resultados se presentan en un dashboard interactivo, no como archivo aislado ni salida de consola.

## Objetivos de calidad

- **Precisión:** ≥98% de exactitud en la detección de marcas OMR; validación de clave 100% libre de ambigüedad algebraica.
- **Rendimiento:** ≤5 segundos por examen individual (percentil 95); requiere procesamiento en paralelo, no secuencial, para que un lote de 200 hojas quepa en ≤10 minutos.
- **Degradación controlada:** toda marca con confianza <70% se envía a revisión manual; el sistema detecta correctamente ≥99% de esos casos ambiguos.
- **Seguridad:** un profesor solo accede a los datos de los cursos que tiene autorizados.

## Metodología

El desarrollo sigue Aspect Driven Development (ADD): cada funcionalidad se declara como un aspecto que se puede trazar de principio a fin, desde el requisito hasta la evidencia de que funciona (ver `docs/aspectos.md`).

## Estado actual

- [x] Aspecto A-01 (carga de examen)
- [x] arc42: contexto, restricciones y objetivos de calidad
- [x] C4 Nivel 1
- [ ] arc42: Building Block View, Runtime View, Deployment View, Architecture Decisions
- [ ] C4 Niveles 2 a 4
- [ ] ADR
- [ ] Código

## Documentación

```
docs/
├── arc42/
│   └── arc42-template-ES.md   # documento de arquitectura completo (arc42)
├── adr/
│   └── docr-adr.md            # plantilla de ADR y convenciones (sin decisiones registradas aún)
├── c4/
│   └── doc-c4.md              # modelo C4 (Nivel 1 definido; 2-4 pendientes)
├── aspectos.md                # aspectos identificados y tabla de trazabilidad
└── ia.md                      # registro de uso de IA durante el desarrollo
```
