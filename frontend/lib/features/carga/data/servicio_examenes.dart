import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../common/api/servicio_salud.dart' show backendUrl;
import 'servicio_resultados.dart' show ExcepcionDeConsulta;

/// Un examen con clave registrada, según `GET /examenes`. La ruta no trae las respuestas.
class ExamenConClave {
  const ExamenConClave({required this.examenId, required this.habilitada});

  final String examenId;

  /// Sin habilitar, las hojas se leen pero no reciben nota.
  final bool habilitada;

  factory ExamenConClave.desdeJson(Map<String, dynamic> json) => ExamenConClave(
        examenId: json['examen_id'] as String,
        habilitada: json['habilitada'] as bool,
      );
}

/// Los exámenes que tienen clave, para elegir uno al subir las hojas. [cliente] existe para las
/// pruebas.
Future<List<ExamenConClave>> listarExamenes({http.Client? cliente}) async {
  final uri = Uri.parse('$backendUrl/examenes');
  final http.Response respuesta;
  try {
    respuesta = await (cliente?.get(uri) ?? http.get(uri)).timeout(const Duration(seconds: 10));
  } catch (_) {
    throw const ExcepcionDeConsulta('No se pudo contactar con el servidor.');
  }
  if (respuesta.statusCode != 200) {
    throw ExcepcionDeConsulta('El servidor respondió ${respuesta.statusCode}.');
  }
  try {
    final cuerpo = jsonDecode(utf8.decode(respuesta.bodyBytes)) as Map<String, dynamic>;
    return [
      for (final examen in cuerpo['examenes'] as List)
        ExamenConClave.desdeJson(examen as Map<String, dynamic>),
    ];
  } catch (_) {
    throw const ExcepcionDeConsulta('La lista de exámenes no se pudo leer.');
  }
}
