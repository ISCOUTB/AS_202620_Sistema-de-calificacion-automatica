import 'dart:convert';

import 'package:http/http.dart' as http;

import 'servicio_salud.dart' show backendUrl;

/// Una sesión abierta (A-05, ADR-0025): el token que va en `Authorization: Bearer`, el correo con
/// que se entró y hasta cuándo vale el token.
class Sesion {
  const Sesion({required this.token, required this.correo, required this.vence});

  final String token;
  final String correo;
  final DateTime vence;

  /// Si en [ahora] el token ya no vale. La API lo rechazaría igual; esto evita mandarlo.
  bool vencidaEn(DateTime ahora) => !ahora.isBefore(vence);

  factory Sesion.desdeJson(Map<String, dynamic> json) => Sesion(
        token: json['token'] as String,
        correo: json['correo'] as String,
        vence: DateTime.parse(json['vence'] as String).toUtc(),
      );

  Map<String, dynamic> aJson() =>
      {'token': token, 'correo': correo, 'vence': vence.toUtc().toIso8601String()};

  @override
  bool operator ==(Object other) =>
      other is Sesion && other.token == token && other.correo == correo && other.vence == vence;

  @override
  int get hashCode => Object.hash(token, correo, vence);
}

/// No se pudo entrar. El mensaje es para el docente.
class ExcepcionDeSesion implements Exception {
  const ExcepcionDeSesion(this.mensaje);

  final String mensaje;

  @override
  String toString() => mensaje;
}

/// Entra con el correo y la contraseña de un docente de la lista (`POST /sesion`). [cliente]
/// existe para las pruebas.
///
/// Un correo sin cuenta y una contraseña equivocada dan el mismo mensaje: la API tampoco dice
/// cuál de los dos falló.
Future<Sesion> iniciarSesion(String correo, String contrasena, {http.Client? cliente}) async {
  final uri = Uri.parse('$backendUrl/sesion');
  final cuerpo = jsonEncode({'correo': correo, 'contrasena': contrasena});
  const encabezados = {'Content-Type': 'application/json'};
  final http.Response respuesta;
  try {
    respuesta = await (cliente?.post(uri, headers: encabezados, body: cuerpo) ??
            http.post(uri, headers: encabezados, body: cuerpo))
        .timeout(const Duration(seconds: 15));
  } catch (_) {
    throw const ExcepcionDeSesion('No se pudo contactar con el servidor.');
  }
  switch (respuesta.statusCode) {
    case 200:
      break;
    case 401:
      throw const ExcepcionDeSesion('El correo o la contraseña no coinciden.');
    case 503:
      throw const ExcepcionDeSesion(
        'El inicio de sesión no está configurado en el servidor. Avise a quien administra QuantIA.',
      );
    default:
      throw ExcepcionDeSesion('El servidor respondió ${respuesta.statusCode}.');
  }
  try {
    return Sesion.desdeJson(jsonDecode(utf8.decode(respuesta.bodyBytes)) as Map<String, dynamic>);
  } catch (_) {
    throw const ExcepcionDeSesion('La respuesta del servidor no se pudo leer.');
  }
}
