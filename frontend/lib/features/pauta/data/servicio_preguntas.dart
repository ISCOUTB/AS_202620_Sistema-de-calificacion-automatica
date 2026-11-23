import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../common/api/servicio_salud.dart';

/// Las preguntas que el docente agrega en Pauta, guardadas a su nombre (ADR-0030): el comienzo del
/// banco de preguntas (RF-06).

/// Una pregunta agregada, con los espacios normalizados por la API. [llave] es como la API la
/// reconoce, y con ella se elimina.
class PreguntaDelDocente {
  const PreguntaDelDocente({
    required this.llave,
    required this.enunciado,
    required this.respuestaCorrecta,
    required this.agregadaEn,
  });

  final String llave;
  final String enunciado;
  final String respuestaCorrecta;
  final DateTime agregadaEn;

  factory PreguntaDelDocente.desdeJson(Map<String, dynamic> json) => PreguntaDelDocente(
        llave: json['llave'] as String,
        enunciado: json['enunciado'] as String,
        respuestaCorrecta: json['respuesta_correcta'] as String,
        agregadaEn: DateTime.parse(json['agregada_en'] as String),
      );
}

/// Algo salió mal con las preguntas. [mensaje] va redactado para el docente; [yaEstaba] dice que
/// el docente ya tenía la pregunta (409).
class ExcepcionPreguntas implements Exception {
  const ExcepcionPreguntas(this.mensaje, {this.yaEstaba = false});

  final String mensaje;
  final bool yaEstaba;

  @override
  String toString() => mensaje;
}

/// Cómo se reconoce una pregunta en la pantalla: el enunciado y la respuesta correcta sin espacios
/// de más, como `llave_de_la_pregunta` en la API.
String formaDeLaPregunta(String enunciado, String respuestaCorrecta) =>
    '${_sinEspaciosDeMas(enunciado)}\n${_sinEspaciosDeMas(respuestaCorrecta)}';

String _sinEspaciosDeMas(String texto) => texto.trim().split(RegExp(r'\s+')).join(' ');

/// Las preguntas del docente de la sesión (`GET /preguntas`), de la más reciente a la más antigua.
Future<List<PreguntaDelDocente>> listarPreguntas({http.Client? cliente}) async {
  final get = cliente?.get ?? http.get;
  final cuerpo = await _pedir(() => get(Uri.parse('$backendUrl/preguntas')), esperado: 200);
  try {
    return [
      for (final p in jsonDecode(cuerpo) as List)
        PreguntaDelDocente.desdeJson(p as Map<String, dynamic>),
    ];
  } catch (_) {
    throw const ExcepcionPreguntas('La respuesta del servidor no se pudo leer.');
  }
}

/// Agrega la pregunta a las del docente (`POST /preguntas`). Un 409 trae el motivo redactado por
/// la API: ya la tenía.
Future<PreguntaDelDocente> agregarPregunta(
  String enunciado,
  String respuestaCorrecta, {
  http.Client? cliente,
}) async {
  final post = cliente?.post ?? http.post;
  final cuerpo = await _pedir(
    () => post(
      Uri.parse('$backendUrl/preguntas'),
      headers: const {'Content-Type': 'application/json'},
      body: jsonEncode({'enunciado': enunciado, 'respuesta_correcta': respuestaCorrecta}),
    ),
    esperado: 201,
  );
  try {
    return PreguntaDelDocente.desdeJson(jsonDecode(cuerpo) as Map<String, dynamic>);
  } catch (_) {
    throw const ExcepcionPreguntas('La respuesta del servidor no se pudo leer.');
  }
}

/// Elimina la pregunta de [llave] (`DELETE /preguntas/{llave}`). Si ya no estaba, el resultado es
/// el mismo y no se trata como un error.
Future<void> eliminarPregunta(String llave, {http.Client? cliente}) async {
  final delete = cliente?.delete ?? http.delete;
  await _pedir(() => delete(Uri.parse('$backendUrl/preguntas/$llave')), esperado: 204, o: 404);
}

Future<String> _pedir(
  Future<http.Response> Function() pedir, {
  required int esperado,
  int? o,
}) async {
  final http.Response respuesta;
  try {
    respuesta = await pedir().timeout(const Duration(seconds: 15));
  } catch (_) {
    throw const ExcepcionPreguntas(
      'No se pudo contactar con el servidor. Revise su conexión y vuelva a intentarlo.',
    );
  }
  final cuerpo = utf8.decode(respuesta.bodyBytes);
  if (respuesta.statusCode == esperado || respuesta.statusCode == o) return cuerpo;
  if (respuesta.statusCode == 409 || respuesta.statusCode == 422) {
    throw ExcepcionPreguntas(
      _detalle(cuerpo) ?? 'Revise el enunciado y la respuesta correcta.',
      yaEstaba: respuesta.statusCode == 409,
    );
  }
  throw ExcepcionPreguntas('El servidor respondió ${respuesta.statusCode}.');
}

/// El campo `detail` de un error de FastAPI, si es texto.
String? _detalle(String cuerpo) {
  try {
    final json = jsonDecode(cuerpo);
    final detalle = json is Map<String, dynamic> ? json['detail'] : null;
    return detalle is String ? detalle : null;
  } catch (_) {
    return null;
  }
}
