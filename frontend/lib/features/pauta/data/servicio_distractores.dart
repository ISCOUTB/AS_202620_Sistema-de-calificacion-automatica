import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../common/api/servicio_salud.dart' show backendUrl;

/// Lo que el docente envía para pedir distractores (RF-11): los mismos tres campos de
/// `SolicitudDeDistractores` en `backend/api/esquemas.py`, y ninguno más. Es lo único que llega
/// al proveedor de LLM (RNF-13).
///
/// Desde el contrato 1.4.0 puede llevar además `otras: true`, que no llega al proveedor: le dice
/// a la API que no responda con las propuestas guardadas para esta misma pregunta (ADR-0019). Solo
/// viaja cuando vale `true`, así que una solicitud normal sigue siendo la de los tres campos.
class SolicitudDistractores {
  const SolicitudDistractores({
    required this.enunciado,
    required this.respuestaCorrecta,
    this.cantidad = 3,
    this.otras = false,
  });

  final String enunciado;
  final String respuestaCorrecta;

  /// Entre 1 y 5, el rango que acepta la API.
  final int cantidad;

  /// `true` para pedir propuestas nuevas en vez de las guardadas: es lo que hace «Pedir otras
  /// propuestas».
  final bool otras;

  /// La misma pregunta, pidiendo propuestas nuevas.
  SolicitudDistractores paraPedirOtras() => SolicitudDistractores(
        enunciado: enunciado,
        respuestaCorrecta: respuestaCorrecta,
        cantidad: cantidad,
        otras: true,
      );

  Map<String, dynamic> aJson() => {
        'enunciado': enunciado,
        'respuesta_correcta': respuestaCorrecta,
        'cantidad': cantidad,
        if (otras) 'otras': true,
      };
}

/// Una opción incorrecta propuesta, con el error de procedimiento que representa.
class DistractorPropuesto {
  const DistractorPropuesto({required this.expresion, required this.error});

  final String expresion;
  final String error;

  factory DistractorPropuesto.desdeJson(Map<String, dynamic> json) => DistractorPropuesto(
        expresion: json['expresion'] as String,
        error: json['error'] as String,
      );
}

/// Una propuesta que la regla del dominio no dejó pasar, con el motivo.
class PropuestaDescartada {
  const PropuestaDescartada({required this.expresion, required this.motivo});

  final String expresion;
  final String motivo;

  factory PropuestaDescartada.desdeJson(Map<String, dynamic> json) => PropuestaDescartada(
        expresion: json['expresion'] as String,
        motivo: json['motivo'] as String,
      );
}

/// La respuesta de `POST /distractores`: lo que pasó la regla y lo que no.
class ResultadoDistractores {
  const ResultadoDistractores({required this.distractores, required this.descartados});

  final List<DistractorPropuesto> distractores;
  final List<PropuestaDescartada> descartados;

  factory ResultadoDistractores.desdeJson(Map<String, dynamic> json) => ResultadoDistractores(
        distractores: (json['distractores'] as List)
            .map((e) => DistractorPropuesto.desdeJson(e as Map<String, dynamic>))
            .toList(),
        descartados: (json['descartados'] as List)
            .map((e) => PropuestaDescartada.desdeJson(e as Map<String, dynamic>))
            .toList(),
      );
}

/// La solicitud no produjo propuestas. [mensaje] va redactado para el docente.
///
/// [proveedorNoDisponible] distingue el 503 (el proveedor falló o tardó más de 20 s, ADR-0013)
/// de una falla de red o de datos inválidos: en ese caso lo útil es volver a pedir más tarde o
/// escribir los distractores a mano, y la pantalla lo dice así.
///
/// [presupuestoAgotado] es el 429: la API cortó la solicitud antes de llegar al proveedor porque
/// se acabó el cupo (ADR-0015). [reintentarEn] es la espera que anuncia `Retry-After`, o `null`
/// si la cabecera no llegó o no se pudo leer.
class ExcepcionDistractores implements Exception {
  const ExcepcionDistractores(
    this.mensaje, {
    this.proveedorNoDisponible = false,
    this.presupuestoAgotado = false,
    this.reintentarEn,
  });

  final String mensaje;
  final bool proveedorNoDisponible;
  final bool presupuestoAgotado;
  final Duration? reintentarEn;

  /// La ventana corta del presupuesto es de un minuto (ADR-0015): una espera más larga solo
  /// puede venir del límite diario, y entonces volver a pedir en la misma sesión no sirve.
  bool get cupoDiarioAgotado =>
      presupuestoAgotado && reintentarEn != null && reintentarEn! > const Duration(minutes: 1);

  @override
  String toString() => mensaje;
}

/// Pide distractores diagnósticos para una pregunta (`POST /distractores`, RF-11).
///
/// Espera hasta 25 s: el adaptador del backend se rinde a los 20 y responde 503, así que el
/// margen evita que el navegador corte antes de recibir ese motivo.
///
/// [cliente] existe para las pruebas: con `MockClient` se ejerce la traducción de cada código
/// sin red. En operación se deja en `null` y se usa el cliente por omisión de `package:http`.
Future<ResultadoDistractores> proponerDistractores(
  SolicitudDistractores solicitud, {
  http.Client? cliente,
}) async {
  final post = cliente?.post ?? http.post;
  final http.Response respuesta;
  try {
    respuesta = await post(
      Uri.parse('$backendUrl/distractores'),
      headers: const {'Content-Type': 'application/json'},
      body: jsonEncode(solicitud.aJson()),
    ).timeout(const Duration(seconds: 25));
  } on TimeoutException {
    throw const ExcepcionDistractores(
      'La API no respondió a tiempo. Puede volver a pedirlo o escribir los distractores a mano.',
      proveedorNoDisponible: true,
    );
  } catch (_) {
    throw const ExcepcionDistractores(
      'No se pudo contactar con la API. Revise su conexión y vuelva a intentarlo.',
    );
  }

  final cuerpo = utf8.decode(respuesta.bodyBytes);
  switch (respuesta.statusCode) {
    case 200:
      try {
        return ResultadoDistractores.desdeJson(jsonDecode(cuerpo) as Map<String, dynamic>);
      } catch (_) {
        throw const ExcepcionDistractores(
          'La API respondió, pero las propuestas no se pudieron leer. Vuelva a pedirlas.',
        );
      }
    case 503:
      throw ExcepcionDistractores(
        _detalle(cuerpo) ??
            'El proveedor de IA no está disponible. Puede volver a pedirlo o escribir los '
                'distractores a mano.',
        proveedorNoDisponible: true,
      );
    case 429:
      // El `detail` ya dice cuánto falta y qué hacer mientras tanto (autoria/presupuesto.py).
      // `Retry-After` llega en segundos, y el navegador solo deja leerlo si la API lo expone en
      // CORS: que falte no es un error, solo quita la cuenta regresiva.
      final segundos = int.tryParse(respuesta.headers['retry-after'] ?? '');
      throw ExcepcionDistractores(
        _detalle(cuerpo) ??
            'Se alcanzó el límite de solicitudes al proveedor de IA. Mientras tanto, los '
                'distractores se pueden escribir a mano.',
        presupuestoAgotado: true,
        reintentarEn: segundos != null && segundos > 0 ? Duration(seconds: segundos) : null,
      );
    case 422:
      throw const ExcepcionDistractores(
        'Revise el enunciado y la respuesta correcta: no pueden quedar vacíos ni pasar del '
        'largo permitido.',
      );
    default:
      throw ExcepcionDistractores('La API respondió ${respuesta.statusCode}.');
  }
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
