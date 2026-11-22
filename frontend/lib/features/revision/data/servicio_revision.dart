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
    this.resueltaEn,
    this.opcionSugerida,
  });

  final int numero;
  final List<BurbujaLeida> burbujas;
  final bool conRecorte;
  final bool resuelta;

  /// La opción que el profesor vio marcada; nula si dijo que ninguna vale.
  final String? opcionResuelta;
  final String? resueltaPor;

  /// Cuándo se guardó lo resuelto, en UTC tal como lo manda la API.
  final DateTime? resueltaEn;

  /// La única opción que la lectura vio marcada (ADR-0024). La pantalla la muestra elegida, pero
  /// no cuenta en la nota hasta que el profesor guarda. Nula si vio dos o ninguna, o si la hoja se
  /// leyó antes de que existiera.
  final String? opcionSugerida;

  factory PreguntaEnRevision.desdeJson(Map<String, dynamic> json) {
    final resueltaEn = json['resuelta_en'] as String?;
    return PreguntaEnRevision(
      numero: json['numero'] as int,
      burbujas: [
        for (final b in json['burbujas'] as List) BurbujaLeida.desdeJson(b as Map<String, dynamic>),
      ],
      conRecorte: json['con_recorte'] as bool,
      resuelta: json['resuelta'] as bool,
      opcionResuelta: json['opcion_resuelta'] as String?,
      resueltaPor: json['resuelta_por'] as String?,
      resueltaEn: resueltaEn == null ? null : DateTime.tryParse(resueltaEn),
      opcionSugerida: json['opcion_sugerida'] as String?,
    );
  }
}

/// Las preguntas de la hoja en el orden en que el profesor las mira: primero las confusas (sin
/// resolver y sin sugerencia), después las preseleccionadas y al final las ya resueltas; dentro de
/// cada grupo, por número. Se ordena con lo que mandó el servidor y no con lo que el profesor va
/// eligiendo, para que las tarjetas no salten mientras elige.
List<PreguntaEnRevision> preguntasEnOrden(HojaEnRevision hoja) {
  int grupo(PreguntaEnRevision pregunta) =>
      pregunta.resuelta ? 2 : (pregunta.opcionSugerida == null ? 0 : 1);
  return [...hoja.preguntas]..sort((a, b) {
      final porGrupo = grupo(a).compareTo(grupo(b));
      return porGrupo != 0 ? porGrupo : a.numero.compareTo(b.numero);
    });
}

/// Una hoja con preguntas en revisión y su nota con lo resuelto hasta ahora.
class HojaEnRevision {
  const HojaEnRevision({
    required this.hojaId,
    required this.notaEnDecimas,
    required this.provisional,
    required this.codigoCompleto,
    required this.preguntas,
    this.nombreArchivo,
    this.recibidaEn,
    this.codigo,
  });

  final String hojaId;
  final int notaEnDecimas;
  final bool provisional;
  final bool codigoCompleto;
  final List<PreguntaEnRevision> preguntas;

  /// El nombre con que se subió el archivo. Nulo si la API no lo sabe o no lo manda.
  final String? nombreArchivo;

  /// Cuándo llegó la hoja, en UTC tal como lo manda la API. Los nombres se repiten de un lote a
  /// otro (`hoja1.jpg`), y la hora es lo que las distingue.
  final DateTime? recibidaEn;

  /// El código del estudiante tal como se leyó, con `?` en los dígitos que no se leyeron. Nulo si
  /// la lectura no lo trae. Es como el profesor sabe de quién es la hoja.
  final String? codigo;

  int get pendientes => preguntas.where((p) => !p.resuelta).length;

  /// La última vez que el profesor guardó algo en la hoja; nula si todavía no guardó nada.
  DateTime? get editadaEn {
    DateTime? ultima;
    for (final pregunta in preguntas) {
      final en = pregunta.resueltaEn;
      if (en != null && (ultima == null || en.isAfter(ultima))) ultima = en;
    }
    return ultima;
  }

  factory HojaEnRevision.desdeJson(Map<String, dynamic> json) {
    final nombre = json['nombre_archivo'] as String?;
    final recibida = json['recibida_en'] as String?;
    return HojaEnRevision(
      hojaId: json['hoja_id'] as String,
      notaEnDecimas: json['nota_en_decimas'] as int,
      provisional: json['provisional'] as bool,
      codigoCompleto: json['codigo_completo'] as bool,
      preguntas: [
        for (final p in json['preguntas'] as List)
          PreguntaEnRevision.desdeJson(p as Map<String, dynamic>),
      ],
      nombreArchivo: nombre == null || nombre.trim().isEmpty ? null : nombre,
      recibidaEn: recibida == null ? null : DateTime.tryParse(recibida),
      codigo: json['codigo'] as String?,
    );
  }
}

const _meses = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

/// «Subida el 16 nov, 14:32», en la hora del navegador del docente. Sin el paquete `intl`, como
/// las cifras del panel.
String llegadaLegible(DateTime instante) => 'Subida el ${_fechaLegible(instante)}';

/// «Editada el 19 nov, 14:40»: cuándo guardó el profesor por última vez en la hoja.
String edicionLegible(DateTime instante) => 'Editada el ${_fechaLegible(instante)}';

String _fechaLegible(DateTime instante) {
  final local = instante.toLocal();
  final hora = local.hour.toString().padLeft(2, '0');
  final minuto = local.minute.toString().padLeft(2, '0');
  return '${local.day} ${_meses[local.month - 1]}, $hora:$minuto';
}

/// Las hojas que muestra la lista con los dos filtros, cada uno por su lado: las que tienen
/// preguntas pendientes con [porRevisar] y las ya revisadas con [revisadas]. Primero todas las por
/// revisar y después las revisadas, para que una revisada no quede entre dos que faltan; dentro de
/// cada grupo, de la subida más nueva a la más vieja, y las que no tienen hora al final y en el
/// orden en que llegaron.
List<HojaEnRevision> hojasVisibles(
  List<HojaEnRevision> hojas, {
  required bool porRevisar,
  required bool revisadas,
}) {
  final visibles = [
    for (final (indice, hoja) in hojas.indexed)
      if (hoja.pendientes > 0 ? porRevisar : revisadas) (indice, hoja),
  ];
  visibles.sort((a, b) {
    final (indiceA, hojaA) = a;
    final (indiceB, hojaB) = b;
    final (faltaA, faltaB) = (hojaA.pendientes > 0, hojaB.pendientes > 0);
    if (faltaA != faltaB) return faltaA ? -1 : 1;
    final (recibidaA, recibidaB) = (hojaA.recibidaEn, hojaB.recibidaEn);
    if (recibidaA != null && recibidaB != null && recibidaA != recibidaB) {
      return recibidaB.compareTo(recibidaA);
    }
    if ((recibidaA == null) != (recibidaB == null)) return recibidaA == null ? 1 : -1;
    return indiceA.compareTo(indiceB);
  });
  return [for (final (_, hoja) in visibles) hoja];
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
/// la hoja con la nota recalculada. Quién lo resolvió no viaja: la API registra al docente de la
/// sesión (ADR-0025).
Future<ResultadoDeHoja> guardarRevision(
  String examenId,
  String hojaId,
  Map<int, String?> opciones, {
  http.Client? cliente,
}) async {
  final uri = Uri.parse('${_ruta(examenId)}/hojas/${Uri.encodeComponent(hojaId)}/revision');
  final cuerpo = jsonEncode({
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
