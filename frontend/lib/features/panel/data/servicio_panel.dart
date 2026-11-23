import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../common/api/servicio_salud.dart' show backendUrl;
import '../../carga/data/servicio_resultados.dart' show ExcepcionDeConsulta;
import 'modelos_panel.dart';

export 'modelos_panel.dart' show PanelDelExamen;

/// Las cifras del panel de un examen del docente (`GET /examenes/{examen_id}/panel`, ADR-0028).
/// Lanza [ExcepcionDeConsulta] con un mensaje para el docente. [cliente] existe para las pruebas.
Future<PanelDelExamen> consultarPanel(String examenId, {http.Client? cliente}) async {
  final uri = Uri.parse('$backendUrl/examenes/${Uri.encodeComponent(examenId)}/panel');
  final http.Response respuesta;
  try {
    respuesta = await (cliente?.get(uri) ?? http.get(uri)).timeout(const Duration(seconds: 15));
  } catch (_) {
    throw const ExcepcionDeConsulta('No se pudo contactar con el servidor.');
  }
  if (respuesta.statusCode == 404) {
    throw const ExcepcionDeConsulta('Ese examen no existe en su cuenta.');
  }
  if (respuesta.statusCode != 200) {
    throw ExcepcionDeConsulta('El servidor respondió ${respuesta.statusCode}.');
  }
  try {
    return PanelDelExamen.desdeJson(
      jsonDecode(utf8.decode(respuesta.bodyBytes)) as Map<String, dynamic>,
    );
  } catch (_) {
    throw const ExcepcionDeConsulta('Las cifras del panel no se pudieron leer.');
  }
}
