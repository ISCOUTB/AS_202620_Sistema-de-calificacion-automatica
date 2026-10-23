import 'package:flutter/foundation.dart';

/// Umbral de confianza de la lectura OMR: toda marca por debajo va a revisión manual.
///
/// Es un valor supuesto, no medido. Lo fijará la detección de marcas (A-02) cuando exista; aquí
/// solo se usa para redactar los textos del panel.
const umbralConfianzaPorcentaje = 70;

/// El curso que el panel resume. Sin cuentas (A-05) no hay docente asociado: solo el grupo.
@immutable
class CursoPanel {
  const CursoPanel({
    required this.asignatura,
    required this.grupo,
    required this.estudiantes,
    required this.periodo,
    required this.examenes,
  });

  final String asignatura;
  final String grupo;
  final int estudiantes;
  final String periodo;

  /// Exámenes del periodo, del más reciente al más antiguo. El primero es el que el panel
  /// muestra al abrir.
  final List<ExamenPanel> examenes;
}

/// Un examen aplicado al grupo, con todo lo que el panel muestra de él.
@immutable
class ExamenPanel {
  const ExamenPanel({
    required this.id,
    required this.nombre,
    required this.tema,
    required this.resumen,
    required this.analisis,
    required this.competencias,
  });

  final String id;

  /// Nombre corto, como «Parcial 2».
  final String nombre;

  /// Contenido evaluado, como «Regla de la cadena y límites trigonométricos».
  final String tema;

  final ResumenExamen resumen;
  final AnalisisPregunta analisis;
  final List<RendimientoCompetencia> competencias;

  String get titulo => '$nombre · $tema';
}

/// Las cuatro cifras de cabecera de un examen.
///
/// El porcentaje de aprobación no se guarda: se calcula de [aprobados] y [estudiantes], para que
/// el número grande y la frase «32 de 43» no puedan contradecirse (el diseño original decía
/// 74,2 %, que no corresponde a 32 de 43).
@immutable
class ResumenExamen {
  const ResumenExamen({
    required this.promedio,
    required this.estudiantes,
    required this.aprobados,
    required this.hojasRecibidas,
    required this.revisionPendiente,
    this.notaMaxima = 5.0,
    this.notaAprobatoria = 3.0,
    this.variacion,
    this.referencia,
  });

  final double promedio;
  final double notaMaxima;
  final double notaAprobatoria;

  /// Diferencia del promedio frente a [referencia]. Nula en el primer examen del periodo.
  final double? variacion;

  /// Examen con el que se compara, como «Parcial 1».
  final String? referencia;

  final int estudiantes;
  final int aprobados;
  final int hojasRecibidas;

  /// Marcas leídas con confianza menor a [umbralConfianzaPorcentaje].
  final int revisionPendiente;

  /// Cero si no hay estudiantes: un examen recién creado, o sin hojas calificadas todavía,
  /// mostraría «NaN %».
  double get porcentajeAprobacion => estudiantes == 0 ? 0 : aprobados * 100 / estudiantes;
}

/// Una opción de respuesta de la pregunta analizada y cuántas marcas recibió.
@immutable
class OpcionRespuesta {
  const OpcionRespuesta({
    required this.letra,
    required this.expresion,
    required this.marcas,
    this.correcta = false,
  });

  final String letra;
  final String expresion;
  final int marcas;
  final bool correcta;
}

/// Estadística de una pregunta (RF-05): cómo se repartieron las marcas entre sus opciones.
///
/// Los porcentajes se calculan sobre las marcas leídas, no sobre los estudiantes: una hoja con la
/// pregunta en blanco no cuenta para ninguna opción, y se informa aparte en [enBlanco].
@immutable
class AnalisisPregunta {
  const AnalisisPregunta({
    required this.numero,
    required this.enunciado,
    required this.opciones,
    required this.letraDistractor,
    required this.errorDistractor,
    this.enBlanco = 0,
  });

  final int numero;

  /// Lo que se pide derivar o calcular, escrito como fórmula.
  final String enunciado;

  final List<OpcionRespuesta> opciones;

  /// La opción incorrecta más elegida.
  final String letraDistractor;

  /// El error de concepto que delata ese distractor, como lo registró el docente en la pauta.
  final String errorDistractor;

  final int enBlanco;

  int get totalMarcas => opciones.fold(0, (suma, opcion) => suma + opcion.marcas);

  OpcionRespuesta get correcta => opciones.firstWhere((opcion) => opcion.correcta);

  OpcionRespuesta get distractor =>
      opciones.firstWhere((opcion) => opcion.letra == letraDistractor);

  /// Porcentaje entero de las marcas que se llevó [opcion].
  int porcentaje(OpcionRespuesta opcion) =>
      totalMarcas == 0 ? 0 : (opcion.marcas * 100 / totalMarcas).round();

  bool get distractorSuperaACorrecta => distractor.marcas > correcta.marcas;
}

/// Nivel de una competencia según su porcentaje de aciertos.
///
/// Los cortes (80 y 65) son de ejemplo: los fijará el equipo con el docente cuando exista la
/// calificación (A-03).
enum NivelCompetencia {
  alto('Alto'),
  medio('Medio'),
  bajo('Bajo');

  const NivelCompetencia(this.texto);

  final String texto;

  static NivelCompetencia para(int porcentajeAciertos) {
    if (porcentajeAciertos >= 80) return NivelCompetencia.alto;
    if (porcentajeAciertos >= 65) return NivelCompetencia.medio;
    return NivelCompetencia.bajo;
  }
}

/// Aciertos del grupo en las preguntas de una competencia.
@immutable
class RendimientoCompetencia {
  const RendimientoCompetencia({
    required this.nombre,
    required this.porcentajeAciertos,
    required this.preguntas,
    this.nota,
  });

  final String nombre;
  final int porcentajeAciertos;
  final int preguntas;

  /// Un dato que ayuda a leer la cifra, como «incluye la pregunta 7».
  final String? nota;

  NivelCompetencia get nivel => NivelCompetencia.para(porcentajeAciertos);
}
