import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../common/api/servicio_salud.dart' show backendUrl;
import 'servicio_resultados.dart' show ExcepcionDeConsulta;

/// Un examen del docente con clave registrada, según `GET /examenes`. La ruta no trae las
/// respuestas.
///
/// Desde ADR-0028 el identificador lo acuña el sistema (`000001`) y el nombre lo pone el docente
/// («Parcial 1»). Dos docentes pueden usar el mismo nombre; cada uno ve solo los suyos.
class ExamenConClave {
  const ExamenConClave({required this.examenId, required this.habilitada, String? nombre})
      : nombre = nombre ?? examenId;

  final String examenId;

  /// Como lo llamó el docente. Un examen anterior a ADR-0028 se llama como su identificador.
  final String nombre;

  /// Sin habilitar, las hojas se leen pero no reciben nota.
  final bool habilitada;

  /// Cómo se muestra en las listas: el nombre, y el identificador al lado si son distintos.
  String get etiqueta => nombre == examenId ? examenId : '$nombre · $examenId';

  factory ExamenConClave.desdeJson(Map<String, dynamic> json) => ExamenConClave(
        examenId: json['examen_id'] as String,
        nombre: json['nombre'] as String?,
        habilitada: json['habilitada'] as bool,
      );
}

/// Un examen recién pedido con `POST /examenes`. [creado] es falso si el docente ya tenía uno con
/// ese nombre: entonces es ese.
class ExamenCreado {
  const ExamenCreado({required this.examenId, required this.nombre, required this.creado});

  final String examenId;
  final String nombre;
  final bool creado;
}

/// Los nombres se comparan como en la API: sin espacios de más y sin distinguir mayúsculas.
String claveDelNombre(String nombre) =>
    nombre.trim().split(RegExp(r'\s+')).join(' ').toLowerCase();

/// El largo máximo del nombre, el mismo que acepta la API.
const largoMaximoDelNombre = 80;

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

/// Crea el examen del docente con ese nombre, o devuelve el que ya tenía (ADR-0028). Lanza
/// [ExcepcionDeConsulta] con un mensaje para el docente.
Future<ExamenCreado> crearExamen(String nombre, {http.Client? cliente}) async {
  final uri = Uri.parse('$backendUrl/examenes');
  final cuerpo = jsonEncode({'nombre': nombre});
  const encabezados = {'Content-Type': 'application/json'};
  final http.Response respuesta;
  try {
    respuesta = await (cliente?.post(uri, headers: encabezados, body: cuerpo) ??
            http.post(uri, headers: encabezados, body: cuerpo))
        .timeout(const Duration(seconds: 15));
  } catch (_) {
    throw const ExcepcionDeConsulta('No se pudo contactar con el servidor.');
  }
  if (respuesta.statusCode != 200 && respuesta.statusCode != 201) {
    var motivo = 'No se creó el examen. El servidor respondió ${respuesta.statusCode}.';
    try {
      final detalle = (jsonDecode(utf8.decode(respuesta.bodyBytes)) as Map)['detail'];
      if (detalle is String) motivo = detalle;
    } catch (_) {
      // Queda el mensaje genérico.
    }
    throw ExcepcionDeConsulta(motivo);
  }
  try {
    final datos = jsonDecode(utf8.decode(respuesta.bodyBytes)) as Map<String, dynamic>;
    return ExamenCreado(
      examenId: datos['examen_id'] as String,
      nombre: datos['nombre'] as String,
      creado: respuesta.statusCode == 201,
    );
  } catch (_) {
    throw const ExcepcionDeConsulta('La respuesta del servidor no se pudo leer.');
  }
}
