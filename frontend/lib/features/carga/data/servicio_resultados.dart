import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../common/api/servicio_salud.dart' show backendUrl;

/// Cómo quedó una hoja después de leerla, según `GET /examenes/{examen_id}/resultados`.
enum EstadoDeLectura {
  /// Tiene nota y nada espera al profesor.
  calificada,

  /// Tiene nota provisional: hay preguntas que esperan su revisión.
  enRevision,

  /// Se leyó, pero el examen no tiene una clave habilitada.
  sinClaveHabilitada,

  /// No se pudo leer: hay que volver a tomar la foto.
  ilegible;

  static EstadoDeLectura desdeTexto(String texto) => switch (texto) {
        'calificada' => calificada,
        'en_revision' => enRevision,
        'sin_clave_habilitada' => sinClaveHabilitada,
        _ => ilegible,
      };
}

/// El resultado de una hoja. **No trae el código del estudiante**: la ruta es pública hasta que
/// exista el inicio de sesión (A-05), y el código queda en el servidor.
class ResultadoDeHoja {
  const ResultadoDeHoja({
    required this.hojaId,
    required this.estado,
    this.motivo,
    this.notaEnDecimas,
    this.provisional = false,
    this.preguntasPorRevisar = const [],
    this.codigoCompleto,
    this.revisada = false,
  });

  final String hojaId;
  final EstadoDeLectura estado;
  final String? motivo;

  /// De 0 a 50: 42 es 4,2. Nula sin clave o si la hoja es ilegible.
  final int? notaEnDecimas;
  final bool provisional;
  final List<int> preguntasPorRevisar;

  /// Si el código del estudiante se leyó en sus ocho columnas. Nulo si la hoja es ilegible.
  final bool? codigoCompleto;

  /// Si la nota incluye lo que resolvió el profesor (RF-08).
  final bool revisada;

  factory ResultadoDeHoja.desdeJson(Map<String, dynamic> json) => ResultadoDeHoja(
        hojaId: json['hoja_id'] as String,
        estado: EstadoDeLectura.desdeTexto(json['estado'] as String),
        motivo: json['motivo'] as String?,
        notaEnDecimas: json['nota_en_decimas'] as int?,
        provisional: json['provisional'] as bool? ?? false,
        preguntasPorRevisar: [
          for (final n in json['preguntas_por_revisar'] as List? ?? const []) n as int,
        ],
        codigoCompleto: json['codigo_completo'] as bool?,
        revisada: json['revisada'] as bool? ?? false,
      );
}

/// Los resultados de un examen, por `hoja_id`: la identidad que la carga devolvió con cada hoja.
class ResultadosDelExamen {
  const ResultadosDelExamen({required this.examenId, required this.porHoja});

  final String examenId;
  final Map<String, ResultadoDeHoja> porHoja;

  factory ResultadosDelExamen.desdeJson(Map<String, dynamic> json) => ResultadosDelExamen(
        examenId: json['examen_id'] as String,
        porHoja: {
          for (final hoja in json['hojas'] as List)
            (hoja as Map<String, dynamic>)['hoja_id'] as String:
                ResultadoDeHoja.desdeJson(hoja),
        },
      );
}

/// La consulta no dio un resultado legible. La pantalla la reintenta en la vuelta siguiente: no
/// hay nada que el docente tenga que hacer.
class ExcepcionDeConsulta implements Exception {
  const ExcepcionDeConsulta(this.mensaje);

  final String mensaje;

  @override
  String toString() => mensaje;
}

/// Consulta cómo quedó cada hoja leída del examen (A-02 y A-03). [cliente] existe para las
/// pruebas.
Future<ResultadosDelExamen> consultarResultados(String examenId, {http.Client? cliente}) async {
  final uri = Uri.parse('$backendUrl/examenes/${Uri.encodeComponent(examenId)}/resultados');
  final http.Response respuesta;
  try {
    respuesta = await (cliente?.get(uri) ?? http.get(uri));
  } catch (_) {
    throw const ExcepcionDeConsulta('No se pudo contactar con el servidor.');
  }
  if (respuesta.statusCode != 200) {
    throw ExcepcionDeConsulta('El servidor respondió ${respuesta.statusCode}.');
  }
  try {
    return ResultadosDelExamen.desdeJson(
      jsonDecode(utf8.decode(respuesta.bodyBytes)) as Map<String, dynamic>,
    );
  } catch (_) {
    throw const ExcepcionDeConsulta('La respuesta del servidor no se pudo leer.');
  }
}

/// La nota en décimas como la escribe el docente: 49 es «4,9».
String notaLegible(int decimas) => '${decimas ~/ 10},${decimas % 10}';

/// El motivo de la API en palabras del docente.
String motivoLegible(String? motivo) => switch (motivo) {
      'formato_no_soportado' => 'el archivo no es una foto que se pueda leer',
      'imagen_ilegible' => 'la foto está borrosa, oscura o tiene poca resolución',
      'marcas_de_registro_no_encontradas' => 'no se ven las cuatro marcas negras de las esquinas',
      'hoja_no_reconocida' => 'no parece la hoja de respuestas de QuantIA',
      'sin_clave' => 'el examen todavía no tiene clave',
      'clave_sin_habilitar' => 'la clave del examen no está habilitada',
      'clave_mal_escrita' => 'la clave del examen tiene un error',
      null => 'no se pudo leer',
      _ => motivo,
    };
