import 'modelos_panel.dart';

/// Datos de ejemplo del panel del curso.
///
/// No existe todavía nada que los produzca: la detección de marcas (A-02) y la calificación
/// (A-03) no están construidas. Se inventaron para enseñar el flujo, pero cuidando que las cifras
/// cuadren entre sí, porque un panel con números que no suman pierde la confianza del docente
/// aunque sea de ejemplo:
///
/// * Parcial 2: 32 de 43 aprobados da 74,4 %; el promedio 3,7 es el del Parcial 1 (3,3) más 0,4;
///   las competencias suman 24 preguntas y su promedio ponderado de aciertos (73,9 %) equivale a
///   3,7 sobre 5,0.
/// * Pregunta 7: 42 marcas (una hoja la dejó en blanco), y 3 + 16 + 20 + 3 = 42 da 7, 38, 48 y
///   7 por ciento.
/// * Parcial 1: 28 de 43 aprobados da 65,1 %; sus competencias suman 20 preguntas con 65,9 % de
///   aciertos, es decir 3,3 sobre 5,0.
const cursoEjemplo = CursoPanel(
  asignatura: 'Cálculo diferencial',
  grupo: 'Grupo 04',
  estudiantes: 43,
  periodo: '2026-2',
  examenes: [_parcial2, _parcial1],
);

const _parcial2 = ExamenPanel(
  id: 'parcial-2',
  nombre: 'Parcial 2',
  tema: 'Regla de la cadena y límites trigonométricos',
  resumen: ResumenExamen(
    promedio: 3.7,
    variacion: 0.4,
    referencia: 'Parcial 1',
    estudiantes: 43,
    aprobados: 32,
    hojasRecibidas: 43,
    revisionPendiente: 3,
  ),
  analisis: AnalisisPregunta(
    numero: 7,
    enunciado: 'd/dx[sen(3x²)]',
    opciones: [
      OpcionRespuesta(letra: 'A', expresion: 'cos(3x²)', marcas: 3),
      OpcionRespuesta(letra: 'B', expresion: '6x·cos(3x²)', marcas: 16, correcta: true),
      OpcionRespuesta(letra: 'C', expresion: '6x·cos(x)', marcas: 20),
      OpcionRespuesta(letra: 'D', expresion: '6x·sen(3x²)', marcas: 3),
    ],
    letraDistractor: 'C',
    // 6x·cos(x) sí deriva el argumento interno (el factor 6x está), pero evalúa el coseno en x.
    errorDistractor: 'evalúa el coseno en x y no en el argumento interno 3x²',
    enBlanco: 1,
  ),
  competencias: [
    RendimientoCompetencia(nombre: 'Derivadas básicas', porcentajeAciertos: 88, preguntas: 6),
    RendimientoCompetencia(
      nombre: 'Regla de la cadena',
      porcentajeAciertos: 60,
      preguntas: 8,
      nota: 'incluye la pregunta 7',
    ),
    RendimientoCompetencia(
      nombre: 'Límites trigonométricos',
      porcentajeAciertos: 81,
      preguntas: 6,
    ),
    RendimientoCompetencia(nombre: 'Derivación implícita', porcentajeAciertos: 70, preguntas: 4),
  ],
);

const _parcial1 = ExamenPanel(
  id: 'parcial-1',
  nombre: 'Parcial 1',
  tema: 'Límites y continuidad',
  resumen: ResumenExamen(
    promedio: 3.3,
    estudiantes: 43,
    aprobados: 28,
    hojasRecibidas: 43,
    revisionPendiente: 0,
  ),
  analisis: AnalisisPregunta(
    numero: 4,
    enunciado: 'lím x→0 sen(5x)/x',
    opciones: [
      OpcionRespuesta(letra: 'A', expresion: '0', marcas: 4),
      OpcionRespuesta(letra: 'B', expresion: '1', marcas: 12),
      OpcionRespuesta(letra: 'C', expresion: '5', marcas: 24, correcta: true),
      OpcionRespuesta(letra: 'D', expresion: '1/5', marcas: 3),
    ],
    letraDistractor: 'B',
    errorDistractor: 'aplica lím sen(u)/u = 1 sin ajustar el factor 5',
  ),
  competencias: [
    RendimientoCompetencia(nombre: 'Límites algebraicos', porcentajeAciertos: 72, preguntas: 6),
    RendimientoCompetencia(
      nombre: 'Límites trigonométricos',
      porcentajeAciertos: 56,
      preguntas: 5,
      nota: 'incluye la pregunta 4',
    ),
    RendimientoCompetencia(nombre: 'Continuidad', porcentajeAciertos: 70, preguntas: 5),
    RendimientoCompetencia(nombre: 'Asíntotas', porcentajeAciertos: 64, preguntas: 4),
  ],
);
