import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../common/api/servicio_salud.dart' show backendUrl;

/// Las preguntas que imprime la hoja v1. Una clave tiene de 1 a esta cantidad.
const maximoDePreguntas = 40;

/// Las opciones de cada pregunta, en el orden de la hoja.
const opcionesDeLaHoja = ['A', 'B', 'C', 'D'];

/// La clave de un examen tal como la guarda la API (A-04, ADR-0026).
class ClaveDelExamen {
  const ClaveDelExamen({
    required this.examenId,
    required this.respuestas,
    required this.sePuedeCambiar,
    this.habilitadaPor,
    this.habilitadaEn,
  });

  final String examenId;

  /// La respuesta correcta de cada pregunta, desde la 1.
  final List<String> respuestas;

  /// Falso si ya hay hojas del examen calificadas con ella.
  final bool sePuedeCambiar;

  final String? habilitadaPor;
  final DateTime? habilitadaEn;

  bool get habilitada => habilitadaPor != null;

  factory ClaveDelExamen.desdeJson(Map<String, dynamic> json) {
    final en = json['habilitada_en'] as String?;
    return ClaveDelExamen(
      examenId: json['examen_id'] as String,
      respuestas: [for (final r in json['respuestas'] as List) r as String],
      sePuedeCambiar: json['se_puede_cambiar'] as bool,
      habilitadaPor: json['habilitada_por'] as String?,
      habilitadaEn: en == null ? null : DateTime.parse(en),
    );
  }
}

/// La clave no se pudo pedir, guardar o habilitar. El mensaje es para el docente.
class ExcepcionDeClave implements Exception {
  const ExcepcionDeClave(this.mensaje);

  final String mensaje;

  @override
  String toString() => mensaje;
}

/// La misma regla que la API: letras sin acento, dígitos, guion y guion bajo, hasta 64, y que
/// empiece por letra o dígito.
bool identificadorValido(String examenId) =>
    RegExp(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$').hasMatch(examenId);

/// Las respuestas de un texto pegado: se quedan las letras y se descartan los números, los
/// espacios y la puntuación, así que valen «ABCD», «A B C D» y «1. A, 2. B, …». Lanza
/// [FormatException] con un mensaje para el docente.
List<String> respuestasDesdeTexto(String texto) {
  final letras = [
    for (final caracter in texto.toUpperCase().split(''))
      if (RegExp(r'\p{L}', unicode: true).hasMatch(caracter)) caracter,
  ];
  if (letras.isEmpty) throw const FormatException('No hay respuestas en el texto.');
  for (final (indice, letra) in letras.indexed) {
    if (!opcionesDeLaHoja.contains(letra)) {
      throw FormatException('La pregunta ${indice + 1} dice «$letra»: solo valen A, B, C y D.');
    }
  }
  if (letras.length > maximoDePreguntas) {
    throw FormatException(
      'Hay ${letras.length} respuestas; la hoja tiene $maximoDePreguntas.',
    );
  }
  return letras;
}

String _ruta(String examenId) => '$backendUrl/examenes/${Uri.encodeComponent(examenId)}/clave';

const _json = {'Content-Type': 'application/json'};

/// La clave del examen, o null si todavía no tiene. [cliente] existe para las pruebas.
Future<ClaveDelExamen?> consultarClave(String examenId, {http.Client? cliente}) async {
  final respuesta = await _pedir(() {
    final uri = Uri.parse(_ruta(examenId));
    return cliente?.get(uri) ?? http.get(uri);
  });
  if (respuesta.statusCode == 404) return null;
  return _clave(respuesta, 'La clave no se pudo leer.');
}

/// Guarda las respuestas del examen, la de la pregunta 1 primero. Queda sin habilitar.
Future<ClaveDelExamen> guardarClave(
  String examenId,
  List<String> respuestas, {
  http.Client? cliente,
}) async {
  final cuerpo = jsonEncode({'respuestas': respuestas});
  final respuesta = await _pedir(() {
    final uri = Uri.parse(_ruta(examenId));
    return cliente?.put(uri, headers: _json, body: cuerpo) ??
        http.put(uri, headers: _json, body: cuerpo);
  });
  return _clave(respuesta, 'No se guardó la clave.');
}

/// Habilita la clave a nombre del docente de la sesión (RF-07).
Future<ClaveDelExamen> habilitarClave(String examenId, {http.Client? cliente}) async {
  final respuesta = await _pedir(() {
    final uri = Uri.parse('${_ruta(examenId)}/habilitacion');
    return cliente?.post(uri) ?? http.post(uri);
  });
  return _clave(respuesta, 'No se habilitó la clave.');
}

Future<http.Response> _pedir(Future<http.Response> Function() peticion) async {
  try {
    return await peticion().timeout(const Duration(seconds: 15));
  } catch (_) {
    throw const ExcepcionDeClave('No se pudo contactar con el servidor.');
  }
}

ClaveDelExamen _clave(http.Response respuesta, String sinRespuesta) {
  if (respuesta.statusCode != 200) {
    throw ExcepcionDeClave(_motivo(respuesta, sinRespuesta));
  }
  try {
    return ClaveDelExamen.desdeJson(
      jsonDecode(utf8.decode(respuesta.bodyBytes)) as Map<String, dynamic>,
    );
  } catch (_) {
    throw const ExcepcionDeClave('La respuesta del servidor no se pudo leer.');
  }
}

/// El `detail` de la API cuando es un texto; si no, el código.
String _motivo(http.Response respuesta, String sinRespuesta) {
  try {
    final detalle = (jsonDecode(utf8.decode(respuesta.bodyBytes)) as Map)['detail'];
    if (detalle is String) return detalle;
  } catch (_) {
    // Cae al mensaje genérico.
  }
  return '$sinRespuesta El servidor respondió ${respuesta.statusCode}.';
}
