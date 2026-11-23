import 'dart:math' as math;

import 'package:flutter/foundation.dart';

// Lo que muestra el panel de un examen (RF-05), tal como lo calcula la API en
// `GET /examenes/{examen_id}/panel` (ADR-0028). Reemplaza a los datos de ejemplo con los que
// nació la pantalla: todo sale de las hojas que el sistema leyó y de lo que resolvió el docente.

/// La API manda las notas en décimas (37 es 3,7); aquí se pasan a la escala de 0 a 5.
double _nota(Object? decimas) => decimas == null ? 0 : (decimas as num) / 10;

/// Las cifras de cabecera: promedio, aprobación, hojas recibidas y revisión pendiente.
@immutable
class ResumenExamen {
  const ResumenExamen({
    required this.hojasRecibidas,
    required this.hojasLeidas,
    required this.hojasConNota,
    required this.hojasSinNota,
    required this.hojasIlegibles,
    required this.hojasEnRevision,
    required this.preguntasPorRevisar,
    required this.aprobados,
    this.promedio,
    this.desviacion,
    this.notaAprobatoria = 3.0,
    this.notaMaxima = 5.0,
  });

  factory ResumenExamen.desdeJson(Map<String, dynamic> json) => ResumenExamen(
        hojasRecibidas: json['hojas_recibidas'] as int,
        hojasLeidas: json['hojas_leidas'] as int,
        hojasConNota: json['hojas_con_nota'] as int,
        hojasSinNota: json['hojas_sin_nota'] as int,
        hojasIlegibles: json['hojas_ilegibles'] as int,
        hojasEnRevision: json['hojas_en_revision'] as int,
        preguntasPorRevisar: json['preguntas_por_revisar'] as int,
        aprobados: json['aprobados'] as int,
        promedio: json['promedio_en_decimas'] == null ? null : _nota(json['promedio_en_decimas']),
        desviacion:
            json['desviacion_en_decimas'] == null ? null : _nota(json['desviacion_en_decimas']),
        notaAprobatoria: _nota(json['nota_aprobatoria_en_decimas'] ?? 30),
      );

  /// Las que registró la recepción, se hayan leído o no.
  final int hojasRecibidas;
  final int hojasLeidas;

  /// También las de nota provisional, que solo puede subir al resolver lo pendiente.
  final int hojasConNota;

  /// Leídas sin clave habilitada.
  final int hojasSinNota;
  final int hojasIlegibles;

  /// Hojas con alguna pregunta que espera al docente.
  final int hojasEnRevision;
  final int preguntasPorRevisar;
  final int aprobados;

  /// Nulos mientras ninguna hoja tenga nota.
  final double? promedio;
  final double? desviacion;

  final double notaAprobatoria;
  final double notaMaxima;

  /// Recibidas que el sistema todavía no termina de leer.
  int get porLeer => math.max(0, hojasRecibidas - hojasLeidas);

  /// Cero si no hay hojas con nota: un examen recién creado mostraría «NaN %».
  double get porcentajeAprobacion => hojasConNota == 0 ? 0 : aprobados * 100 / hojasConNota;
}

/// Cada pregunta de cada hoja con nota, en una sola categoría según lo que vio la lectura.
@immutable
class MarcasDelExamen {
  const MarcasDelExamen({
    required this.correctas,
    required this.incorrectas,
    required this.tenuesODudosas,
    required this.dobles,
    required this.enBlanco,
    required this.pendientes,
  });

  factory MarcasDelExamen.desdeJson(Map<String, dynamic> json) => MarcasDelExamen(
        correctas: json['correctas'] as int,
        incorrectas: json['incorrectas'] as int,
        tenuesODudosas: json['tenues_o_dudosas'] as int,
        dobles: json['dobles'] as int,
        enBlanco: json['en_blanco'] as int,
        pendientes: json['pendientes'] as int,
      );

  final int correctas;
  final int incorrectas;
  final int tenuesODudosas;
  final int dobles;
  final int enBlanco;

  /// De las dudosas y las dobles, las que el docente todavía no resolvió.
  final int pendientes;

  int get total => correctas + incorrectas + tenuesODudosas + dobles + enBlanco;
}

/// Una pregunta de la clave en las hojas con nota.
@immutable
class PreguntaDelPanel {
  const PreguntaDelPanel({
    required this.numero,
    required this.correcta,
    required this.aciertos,
    required this.hojas,
    required this.marcadas,
    this.enBlanco = 0,
    this.dobles = 0,
    this.dudosas = 0,
  });

  factory PreguntaDelPanel.desdeJson(Map<String, dynamic> json) => PreguntaDelPanel(
        numero: json['numero'] as int,
        correcta: json['correcta'] as String,
        aciertos: json['aciertos'] as int,
        hojas: json['hojas'] as int,
        marcadas: {
          for (final MapEntry(:key, :value) in (json['marcadas'] as Map).entries)
            (key as String): (value as int),
        },
        enBlanco: json['en_blanco'] as int,
        dobles: json['dobles'] as int,
        dudosas: json['dudosas'] as int,
      );

  final int numero;
  final String correcta;
  final int aciertos;

  /// Hojas con nota que no anularon la pregunta.
  final int hojas;

  /// Cuántas veces quedó marcada cada opción, con lo resuelto por el docente.
  final Map<String, int> marcadas;
  final int enBlanco;
  final int dobles;
  final int dudosas;

  double get porcentajeAciertos => hojas == 0 ? 0 : aciertos * 100 / hojas;

  /// La opción incorrecta más marcada, o nula si ninguna incorrecta se marcó.
  String? get distractorMasMarcado {
    String? elegido;
    var maximo = 0;
    for (final MapEntry(:key, :value) in marcadas.entries) {
      if (key != correcta && value > maximo) {
        elegido = key;
        maximo = value;
      }
    }
    return elegido;
  }
}

/// El panel completo de un examen.
@immutable
class PanelDelExamen {
  const PanelDelExamen({
    required this.examenId,
    required this.nombre,
    required this.resumen,
    required this.marcas,
    required this.notas,
    required this.preguntas,
  });

  factory PanelDelExamen.desdeJson(Map<String, dynamic> json) => PanelDelExamen(
        examenId: json['examen_id'] as String,
        nombre: json['nombre'] as String,
        resumen: ResumenExamen.desdeJson(json['resumen'] as Map<String, dynamic>),
        marcas: MarcasDelExamen.desdeJson(json['marcas'] as Map<String, dynamic>),
        notas: [for (final n in json['notas_en_decimas'] as List) _nota(n)],
        preguntas: [
          for (final p in json['preguntas'] as List)
            PreguntaDelPanel.desdeJson(p as Map<String, dynamic>),
        ],
      );

  final String examenId;
  final String nombre;
  final ResumenExamen resumen;
  final MarcasDelExamen marcas;

  /// La nota de cada hoja con nota, de 0 a 5, de menor a mayor.
  final List<double> notas;
  final List<PreguntaDelPanel> preguntas;
}

/// Un tramo del histograma de notas: [desde, hasta), salvo el último, que incluye el 5,0.
@immutable
class TramoDeNotas {
  const TramoDeNotas({required this.desde, required this.hasta, required this.hojas});

  final double desde;
  final double hasta;
  final int hojas;
}

/// Las notas en tramos de [ancho] desde 1,0 hasta 5,0. Si alguna nota es menor que 1,0 el
/// histograma empieza en 0,0, para no esconderla en el primer tramo. Los tramos empiezan en
/// múltiplos de [ancho], así que 3,0 abre un tramo y la aprobación cae justo en un borde.
List<TramoDeNotas> tramosDeNotas(List<double> notas, {double ancho = 0.5, double maxima = 5.0}) {
  final inicio = notas.any((n) => n < 1.0) ? 0.0 : 1.0;
  final cantidad = ((maxima - inicio) / ancho).round();
  final hojas = List.filled(cantidad, 0);
  for (final nota in notas) {
    // Con un pequeño margen, para que 3,0 guardado como 2,9999 no caiga un tramo abajo.
    final indice = ((nota - inicio) / ancho + 1e-9).floor().clamp(0, cantidad - 1);
    hojas[indice]++;
  }
  return [
    for (var i = 0; i < cantidad; i++)
      TramoDeNotas(desde: inicio + i * ancho, hasta: inicio + (i + 1) * ancho, hojas: hojas[i]),
  ];
}

/// La densidad de la curva normal con [media] y [desviacion] en [x]. Multiplicada por el número
/// de hojas y el ancho del tramo, da cuántas hojas esperaría ese tramo si las notas siguieran la
/// campana: así la curva y las barras comparten el eje.
double densidadNormal(double x, double media, double desviacion) {
  final z = (x - media) / desviacion;
  return math.exp(-0.5 * z * z) / (desviacion * math.sqrt(2 * math.pi));
}
