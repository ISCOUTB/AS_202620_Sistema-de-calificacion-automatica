import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../common/api/servicio_salud.dart' show backendUrl;
import '../../carga/data/servicio_resultados.dart' show ResultadoDeHoja;

/// Lo que se midió en una burbuja de una pregunta en revisión.
class BurbujaLeida {
  const BurbujaLeida({required this.opcion, required this.tipo, required this.confianza});

  final String opcion;

  /// `vacia`, `tenue`, `borron` o `completa`.
  final String tipo;
  final int confianza;

  factory BurbujaLeida.desdeJson(Map<String, dynamic> json) => BurbujaLeida(
        opcion: json['opcion'] as String,
        tipo: json['tipo'] as String,
        confianza: json['confianza'] as int,
      );
}

/// Una pregunta que la lectura no pudo decidir. **No trae la respuesta correcta**: el profesor dice
/// qué marcó el estudiante y el sistema decide si es correcto.
class PreguntaEnRevision {
  const PreguntaEnRevision({
    required this.numero,
    required this.burbujas,
    required this.conRecorte,
    this.resuelta = false,
    this.opcionResuelta,
    this.resueltaPor,
  });

  final int numero;
  final List<BurbujaLeida> burbujas;
  final bool conRecorte;
  final bool resuelta;

  /// La opción que el profesor vio marcada; nula si dijo que ninguna vale.
  final String? opcionResuelta;
  final String? resueltaPor;

  factory PreguntaEnRevision.desdeJson(Map<String, dynamic> json) => PreguntaEnRevision(
        numero: json['numero'] as int,
        burbujas: [
          for (final b in json['burbujas'] as List) BurbujaLeida.desdeJson(b as Map<String, dynamic>),
        ],
        conRecorte: json['con_recorte'] as bool,
        resuelta: json['resuelta'] as bool,
        opcionResuelta: json['opcion_resuelta'] as String?,
        resueltaPor: json['resuelta_por'] as String?,
      );
}

/// Una hoja con preguntas en revisión y su nota con lo resuelto hasta ahora.
class HojaEnRevision {
  const HojaEnRevision({
    required this.hojaId,
    required this.notaEnDecimas,
    required this.provisional,
    required this.codigoCompleto,
    required this.preguntas,
  });

  final String hojaId;
  final int notaEnDecimas;
  final bool provisional;
  final bool codigoCompleto;
  final List<PreguntaEnRevision> preguntas;

  int get pendientes => preguntas.where((p) => !p.resuelta).length;

  factory HojaEnRevision.desdeJson(Map<String, dynamic> json) => HojaEnRevision(
        hojaId: json['hoja_id'] as String,
        notaEnDecimas: json['nota_en_decimas'] as int,
        provisional: json['provisional'] as bool,
        codigoCompleto: json['codigo_completo'] as bool,
        preguntas: [
          for (final p in json['preguntas'] as List)
            PreguntaEnRevision.desdeJson(p as Map<String, dynamic>),
        ],
      );
}

class RevisionDelExamen {
  const RevisionDelExamen({required this.examenId, required this.hojas});

  final String examenId;
  final List<HojaEnRevision> hojas;

  factory RevisionDelExamen.desdeJson(Map<String, dynamic> json) => RevisionDelExamen(
        examenId: json['examen_id'] as String,
        hojas: [
          for (final h in json['hojas'] as List) HojaEnRevision.desdeJson(h as Map<String, dynamic>),
        ],
      );
}

/// La revisión no se pudo pedir o guardar. El mensaje es para el docente.
class ExcepcionDeRevision implements Exception {
  const ExcepcionDeRevision(this.mensaje);

  final String mensaje;

  @override
  String toString() => mensaje;
}

String _ruta(String examenId) => '$backendUrl/examenes/${Uri.encodeComponent(examenId)}';

/// Las hojas del examen con preguntas en revisión. [cliente] existe para las pruebas.
Future<RevisionDelExamen> consultarRevision(String examenId, {http.Client? cliente}) async {
  final uri = Uri.parse('${_ruta(examenId)}/revision');
  final http.Response respuesta;
  try {
    respuesta = await (cliente?.get(uri) ?? http.get(uri));
  } catch (_) {
    throw const ExcepcionDeRevision('No se pudo contactar con el servidor.');
  }
  if (respuesta.statusCode != 200) {
    throw ExcepcionDeRevision('El servidor respondió ${respuesta.statusCode}.');
  }
  try {
    return RevisionDelExamen.desdeJson(
      jsonDecode(utf8.decode(respuesta.bodyBytes)) as Map<String, dynamic>,
    );
  } catch (_) {
    throw const ExcepcionDeRevision('La revisión no se pudo leer.');
  }
}

/// Guarda lo que el profesor vio marcado en cada pregunta (nulo si ninguna opción vale) y devuelve
/// la hoja con la nota recalculada. [por] queda registrado con cada decisión.
Future<ResultadoDeHoja> guardarRevision(
  String examenId,
  String hojaId,
  String por,
  Map<int, String?> opciones, {
  http.Client? cliente,
}) async {
  final uri = Uri.parse('${_ruta(examenId)}/hojas/${Uri.encodeComponent(hojaId)}/revision');
  final cuerpo = jsonEncode({
    'por': por,
    'resoluciones': [
      for (final MapEntry(key: numero, value: opcion) in opciones.entries)
        {'numero': numero, 'opcion': opcion},
    ],
  });
  final http.Response respuesta;
  try {
    respuesta = await (cliente?.post(uri, headers: _json, body: cuerpo) ??
        http.post(uri, headers: _json, body: cuerpo));
  } catch (_) {
    throw const ExcepcionDeRevision('No se pudo contactar con el servidor. No se guardó nada.');
  }
  if (respuesta.statusCode != 200) {
    throw ExcepcionDeRevision(_motivo(respuesta));
  }
  try {
    return ResultadoDeHoja.desdeJson(
      jsonDecode(utf8.decode(respuesta.bodyBytes)) as Map<String, dynamic>,
    );
  } catch (_) {
    throw const ExcepcionDeRevision('Se guardó, pero la respuesta no se pudo leer. Recargue.');
  }
}

/// Dónde está el recorte de la fila de una pregunta.
String urlDelRecorte(String examenId, String hojaId, int numero) =>
    '${_ruta(examenId)}/hojas/${Uri.encodeComponent(hojaId)}/preguntas/$numero/recorte';

const _json = {'Content-Type': 'application/json'};

/// El `detail` de la API cuando es un texto (los errores del dominio); si no, el código.
String _motivo(http.Response respuesta) {
  try {
    final detalle = (jsonDecode(utf8.decode(respuesta.bodyBytes)) as Map)['detail'];
    if (detalle is String) return 'No se guardó: $detalle';
  } catch (_) {
    // Cae al mensaje genérico.
  }
  return 'No se guardó: el servidor respondió ${respuesta.statusCode}.';
}
