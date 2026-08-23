# 0001 — Arquitectura de Monolito Modular

- **Estado:** aceptado
- **Fecha:** 2026-08-22
- **Decide:** Josué Ortega De Arco, María Restrepo Licona, Sebastián Cañas Plata, Susana Rosales Castellar
- **Escenario de calidad relacionado:** ninguno (decisión fundacional)

---

## Contexto

El sistema debe permitir a profesores universitarios calificar automáticamente exámenes de opción múltiple a partir de imágenes escaneadas o digitalizadas, utilizando un pipeline de **OMR (Reconocimiento Óptico de Marcas)** para detectar las respuestas seleccionadas por los estudiantes. Los resultados se presentan en un dashboard.

El proyecto se encuentra en su fase inicial. La entrega inmediata exige:
- Un repositorio que arranque con **un solo comando**.
- Un **esqueleto ejecutable** con paquetes vacíos y una prueba automatizada en verde.
- Que la semana 4 el equipo pueda empezar a trabajar sobre **la lógica de negocio**, no sobre el montaje del proyecto.

**Fuerzas en tensión identificadas:**
1. **Precisión del OMR vs. Tolerancia a la variabilidad de escaneo:** la calidad de las imágenes escaneadas puede variar (iluminación, inclinación, manchas), lo que afecta la detección de marcas. El sistema debe ser lo suficientemente robusto para manejar estas variaciones sin generar falsos positivos o negativos.
2. **Rendimiento del procesamiento vs. Tiempo de respuesta:** el procesamiento de múltiples exámenes (decenas o cientos) debe ser eficiente para no degradar la experiencia del usuario, especialmente al procesar lotes completos.

**Restricciones conocidas:**
- El sistema es monousuario en su primera versión (profesor/TAs).
- No se requiere escalabilidad horizontal en el corto plazo.
- El equipo tiene experiencia en Python y frameworks web monolíticos.
- La lógica de negocio es simple: comparación de marcas detectadas contra una hoja de respuestas esperada.

---

## Alternativas consideradas

### A. Arquitectura por Capas (Layered Architecture)
Descripción: Organización clásica en capas de Presentación, Negocio y Datos. Las dependencias fluyen hacia abajo.

**A favor:**
- Familiar para el equipo.
- Fácil de implementar rápidamente.
- Baja complejidad inicial.

**En contra:**
- La lógica de negocio (comparación de respuestas) queda acoplada a la infraestructura (OMR, base de datos, web).
- Cambios en la capa de negocio pueden propagarse a presentación y datos.
- Dificulta probar el dominio de forma aislada.

**Por qué no se eligió:** Aunque funcional para un dominio simple, no ofrece la misma claridad estructural ni evolutividad que un monolito modular bien organizado. La separación en módulos permite una mejor organización del código y facilita la incorporación de nuevos tipos de exámenes o formatos en el futuro.

---

### B. Microservicios
Descripción: Descomposición del sistema en servicios independientes (Captura/OMR, Calificación, Dashboard, Autenticación) que se comunican vía API REST o colas de mensajes.

**A favor:**
- Alto aislamiento del dominio.
- Escalabilidad independiente por servicio.
- Permite evolucionar cada parte por separado.

**En contra:**
- **Complejidad operacional alta:** requiere orquestación, descubrimiento de servicios, gestión de transacciones distribuidas.
- **Contradice el requisito de "un solo comando"** para arrancar el sistema.
- Sobrecarga de comunicación entre servicios para un flujo que es secuencial (digitalización → OMR → calificación → dashboard).
- Curva de aprendizaje mayor para el equipo.

**Por qué no se eligió:** La complejidad no se justifica en esta fase. El sistema no tiene requisitos de escalabilidad extrema ni equipos separados por dominio. Añadiría demoras en la entrega inicial y desviaría el foco de la lógica de negocio.

---

### C. Arquitectura Hexagonal Pura (Ports & Adapters)
Descripción: El dominio (lógica de calificación) está completamente aislado de la infraestructura (OMR, web, base de datos) mediante puertos y adaptadores.

**A favor:**
- Máximo aislamiento del dominio.
- Excelente testabilidad.
- Preparado para cambios de infraestructura.

**En contra:**
- **Sobrecarga arquitectónica excesiva** para un dominio simple (comparación de marcas).
- Curva de aprendizaje más pronunciada.
- Mayor complejidad inicial sin beneficio real.

**Por qué no se eligió:** La lógica de negocio es demasiado simple (comparación de marcas contra respuestas esperadas) para justificar la complejidad estructural que impone. No se requiere un núcleo de dominio altamente protegido ni adaptadores elaborados, ya que no hay algoritmos complejos de equivalencia matemática ni procesamiento de lenguaje natural.

---

### D. Monolito Modular (ELEGIDA)
Descripción: Un único despliegue (monolito) organizado internamente en módulos independientes con responsabilidades claras. Cada módulo expone interfaces bien definidas y las dependencias entre módulos están controladas.

**A favor:**
- **Simplicidad de despliegue:** un solo comando para arrancar.
- **Estructura clara:** los módulos (`captura`, `calificacion`, `dashboard`, `infraestructura`) organizan el código de forma comprensible.
- **Evolutividad:** los módulos pueden crecer o ser extraídos a microservicios en el futuro si se necesita.
- **Testabilidad:** cada módulo se puede probar de forma aislada.
- **Proporcional a la complejidad:** no añade sobrecarga innecesaria para un dominio simple.
- **Alineación con tensiones:** la precisión del OMR y el rendimiento se pueden optimizar dentro de cada módulo sin afectar al resto del sistema.

**En contra:**
- Requiere disciplina para mantener los límites de los módulos y no caer en un "big ball of mud".
- Mayor estructura inicial que una arquitectura por capas simple, pero significativamente menor que una hexagonal pura.

**Por qué se eligió:** Equilibra perfectamente la simplicidad de despliegue que exige la entrega con una organización clara que permite el crecimiento controlado del sistema, sin añadir la sobrecarga de una arquitectura hexagonal para un dominio que no lo requiere.

---

## Decisión

Se elige el **Monolito Modular**, porque:

- Permite que el repositorio arranque con **un solo comando**, cumpliendo el requisito de la entrega.
- Ofrece una **estructura clara y proporcionada** a la complejidad del dominio (OMR + comparación de respuestas).
- Encapsula la complejidad del **pipeline de captura y OMR** en un módulo independiente, facilitando ajustes de precisión sin afectar al resto.
- Proporciona un **esqueleto claro** con paquetes vacíos (`captura`, `calificacion`, `dashboard`, `infraestructura`) que permite empezar a trabajar en la lógica de negocio desde la semana 4, tal como se pide.
- Permite que los módulos evolucionen de forma independiente y, si en el futuro se requiere, puedan extraerse como microservicios.

---

## Consecuencias

### Positivas:
- **Despliegue y desarrollo ágil:** el equipo puede enfocarse en la lógica de negocio desde el día 1, sin configurar infraestructura distribuida.
- **Estructura comprensible:** la separación en módulos facilita la navegación y el mantenimiento del código.
- **Testabilidad:** cada módulo se puede probar de forma aislada sin levantar todo el sistema.
- **Evolución controlada:** cada módulo puede crecer independientemente; por ejemplo, se puede mejorar el módulo de OMR sin afectar al dashboard.
- **Facilidad de extracción:** si en el futuro se requiere escalar, los módulos se pueden convertir en microservicios con bajo esfuerzo.
- **Sin sobrecarga innecesaria:** la arquitectura es proporcional a la complejidad del problema.

### Negativas / costos asumidos:
- **Riesgo de acoplamiento interno:** si no se respetan los límites entre módulos, el sistema puede degenerar en un monolito desordenado.
- **Disciplina requerida:** se deben definir y respetar las interfaces entre módulos.
- **Estructura inicial mayor:** requiere un poco más de diseño inicial que una arquitectura por capas simple.

### Riesgos y qué los dispararía:
- **Riesgo:** el sistema se convierta en un "big ball of mud" por falta de disciplina.
  - **Disparador:** que los desarrolladores empiecen a importar clases entre módulos sin pasar por las interfaces definidas.
  - **Mitigación:** revisiones de código (code reviews) y herramientas de análisis de dependencias.

- **Riesgo:** la separación en módulos sea excesiva para un dominio tan simple.
  - **Disparador:** que la lógica de negocio no justifique la estructura modular.
  - **Mitigación:** se puede simplificar a una estructura plana si se demuestra que no aporta valor, pero se mantiene la modularidad inicial para permitir crecimiento.

### Qué habría que revisar si cambia Y:
- **Si cambia el requisito de "un solo comando"** a "despliegue independiente por módulo", se debería reevaluar la decisión y considerar migrar a microservicios.
- **Si el dominio crece significativamente** y aparecen múltiples equipos trabajando en paralelo, se podría extraer cada módulo a un servicio independiente.
- **Si se añaden preguntas abiertas con OCR y LLM** al sistema, se debería reconsiderar la arquitectura y evaluar si se requiere un núcleo hexagonal para proteger esa lógica más compleja.
- **Si el volumen de exámenes crece exponencialmente,** se podría evaluar el procesamiento asíncrono con colas de mensajes entre módulos.

---

## Trazabilidad

- **Requisito / aspecto:** RQ-01 (calificación automática de exámenes mediante OMR), RQ-02 (dashboard de resultados), RQ-03 (arranque con un solo comando).
- **Elementos C4 afectados:** Contenedor "Sistema de Calificación" (monolito); componentes internos: `captura`, `calificacion`, `dashboard`, `infraestructura`.
- **Implementación:** commit / PR: `feat: esqueleto inicial con arquitectura modular`
- **Pruebas que lo cubren:** Prueba automatizada de ejemplo (verde) que valida que el contexto de la aplicación se carga correctamente; prueba de integración que verifica que los módulos se importan sin errores cíclicos.
