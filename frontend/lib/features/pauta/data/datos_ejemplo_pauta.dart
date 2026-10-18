/// Datos de ejemplo de la parte de autoría que todavía no tiene backend.
///
/// El banco de preguntas, la clave y la habilitación del examen (A-04, RF-06 y RF-07) aún no
/// existen en la API. Mientras tanto, la pantalla de pauta muestra este examen inventado para
/// enseñar el flujo, siempre bajo el aviso de datos de ejemplo. Las preguntas sí son coherentes
/// (derivadas con su respuesta correcta verificada a mano) porque se envían tal cual al
/// generador de distractores, que es real: una respuesta mal calculada aquí haría que el modelo
/// propusiera distractores para la pregunta equivocada.
///
/// Las expresiones usan el guion del teclado como signo menos, que es lo que escribe un docente:
/// la API compara las propuestas con la respuesta correcta de forma textual, y un signo menos
/// tipográfico haría que una repetición pasara por distinta.
library;

/// Una pregunta del banco de ejemplo.
class PreguntaEjemplo {
  const PreguntaEjemplo({
    required this.numero,
    required this.tema,
    required this.funcion,
    required this.respuestaCorrecta,
  });

  final int numero;

  /// La regla de derivación que evalúa, para que el docente ubique la pregunta de un vistazo.
  final String tema;

  /// La función que se deriva, tal como aparece en la hoja.
  final String funcion;

  final String respuestaCorrecta;

  /// El enunciado completo, el que llena el formulario y llega a la API.
  String get enunciado => 'Calcule la derivada de $funcion.';
}

/// El examen de ejemplo y el estado de su clave.
class ExamenEjemplo {
  const ExamenEjemplo({
    required this.nombre,
    required this.asignatura,
    required this.grupo,
    required this.opciones,
    required this.fechaHabilitacion,
    required this.preguntas,
  });

  final String nombre;
  final String asignatura;
  final String grupo;

  /// Las letras de cada pregunta en la hoja OMR.
  final List<String> opciones;

  /// Cuándo habilitó el docente la clave. Es inventada, como el resto.
  final String fechaHabilitacion;

  final List<PreguntaEjemplo> preguntas;

  /// Una opción es la correcta; el resto son distractores.
  int get distractoresPorPregunta => opciones.length - 1;

  String get rangoOpciones => '${opciones.first} a ${opciones.last}';
}

const examenEjemplo = ExamenEjemplo(
  nombre: 'Parcial 2',
  asignatura: 'Cálculo diferencial',
  grupo: 'Grupo de ejemplo',
  opciones: ['A', 'B', 'C', 'D'],
  fechaHabilitacion: '6 de octubre de 2026',
  preguntas: [
    PreguntaEjemplo(
      numero: 1,
      tema: 'Regla de la cadena',
      funcion: 'f(x) = (3x² - 5)⁴',
      respuestaCorrecta: '24x(3x² - 5)³',
    ),
    PreguntaEjemplo(
      numero: 2,
      tema: 'Regla del producto',
      funcion: 'f(x) = x·sin(x)',
      respuestaCorrecta: 'sin(x) + x·cos(x)',
    ),
    PreguntaEjemplo(
      numero: 3,
      tema: 'Logaritmo y cadena',
      funcion: 'f(x) = ln(cos(x))',
      respuestaCorrecta: '-tan(x)',
    ),
    PreguntaEjemplo(
      numero: 4,
      tema: 'Exponencial y cadena',
      funcion: 'f(x) = e^(x²)',
      respuestaCorrecta: '2x·e^(x²)',
    ),
    PreguntaEjemplo(
      numero: 5,
      tema: 'Trigonométricas y cadena',
      funcion: 'f(x) = sin(3x)',
      respuestaCorrecta: '3·cos(3x)',
    ),
    PreguntaEjemplo(
      numero: 6,
      tema: 'Regla de la potencia',
      funcion: 'f(x) = x³ - 4x + 7',
      respuestaCorrecta: '3x² - 4',
    ),
    PreguntaEjemplo(
      numero: 7,
      tema: 'Regla del cociente',
      funcion: 'f(x) = (2x + 1)/(x - 3)',
      respuestaCorrecta: '-7/(x - 3)²',
    ),
    PreguntaEjemplo(
      numero: 8,
      tema: 'Raíz y cadena',
      funcion: 'f(x) = √(x² + 1)',
      respuestaCorrecta: 'x/√(x² + 1)',
    ),
    PreguntaEjemplo(
      numero: 9,
      tema: 'Regla del producto',
      funcion: 'f(x) = x²·e^x',
      respuestaCorrecta: '(x² + 2x)·e^x',
    ),
    // La respuesta de esta pregunta también se escribe sin(2x): es el caso que la regla
    // textual del sistema no detecta (R-11), y sirve para mostrárselo al docente.
    PreguntaEjemplo(
      numero: 10,
      tema: 'Trigonométricas y cadena',
      funcion: 'f(x) = sin²(x)',
      respuestaCorrecta: '2·sin(x)·cos(x)',
    ),
  ],
);
