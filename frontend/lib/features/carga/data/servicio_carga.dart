import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../../../common/api/servicio_salud.dart' show backendUrl;

/// Un archivo elegido por el docente, ya leído a memoria.
///
/// Flutter web no puede pasarle una ruta al backend (el navegador no expone rutas del sistema
/// de archivos), así que el contenido viaja en bytes.
class ArchivoSeleccionado {
  const ArchivoSeleccionado({required this.nombre, required this.contenido});

  final String nombre;
  final Uint8List contenido;
}

/// Estado de una hoja aceptada, tal como lo publica el contrato (`HojaAceptadaEnRespuesta`).
enum EstadoHoja {
  /// Su trabajo llegó a la cola.
  encolada,

  /// La hoja está almacenada y en la bitácora, pero su trabajo no llegó a la cola (ADR-0006).
  /// No es una pérdida, y la pantalla no debe mostrarla como tal. El reintento todavía no está
  /// automatizado: `bitacora.pendientes()` deja el dato listo y consumirlo es trabajo de A-02.
  pendienteDeEncolar;

  static EstadoHoja desdeTexto(String? texto) =>
      texto == 'pendiente_de_encolar' ? pendienteDeEncolar : encolada;
}

/// Una hoja que el backend aceptó y almacenó.
class HojaAceptada {
  const HojaAceptada({
    required this.nombreArchivo,
    required this.trabajoId,
    this.estado = EstadoHoja.encolada,
  });

  final String nombreArchivo;
  final String trabajoId;
  final EstadoHoja estado;

  factory HojaAceptada.desdeJson(Map<String, dynamic> json) => HojaAceptada(
        nombreArchivo: json['nombre_archivo'] as String,
        trabajoId: json['trabajo_id'] as String,
        estado: EstadoHoja.desdeTexto(json['estado'] as String?),
      );
}

/// Un archivo que el backend no admitió, con el motivo que hay que mostrarle al docente.
class ArchivoRechazado {
  const ArchivoRechazado({required this.nombreArchivo, required this.motivo});

  final String nombreArchivo;
  final String motivo;

  factory ArchivoRechazado.desdeJson(Map<String, dynamic> json) => ArchivoRechazado(
        nombreArchivo: json['nombre_archivo'] as String,
        motivo: json['motivo'] as String,
      );
}

/// El reporte de recepción completo. Es el espejo de `ResultadoRecepcion` del backend.
class ResultadoCarga {
  const ResultadoCarga({
    required this.totalProcesados,
    required this.aceptadas,
    required this.rechazados,
  });

  final int totalProcesados;
  final List<HojaAceptada> aceptadas;
  final List<ArchivoRechazado> rechazados;

  factory ResultadoCarga.desdeJson(Map<String, dynamic> json) => ResultadoCarga(
        totalProcesados: json['total_procesados'] as int,
        aceptadas: (json['aceptadas'] as List)
            .map((e) => HojaAceptada.desdeJson(e as Map<String, dynamic>))
            .toList(),
        rechazados: (json['rechazados'] as List)
            .map((e) => ArchivoRechazado.desdeJson(e as Map<String, dynamic>))
            .toList(),
      );
}

/// Falla de la carga como tal: no se pudo alcanzar al backend o respondió algo inesperado.
///
/// Es distinta de un archivo rechazado. Un rechazo es una respuesta exitosa del sistema que
/// dice «este archivo no sirve, y por esto»; esta excepción significa que no hubo respuesta,
/// así que el docente no sabe si algo entró y debe reintentar el lote.
class ExcepcionDeCarga implements Exception {
  const ExcepcionDeCarga(this.mensaje);

  final String mensaje;

  @override
  String toString() => mensaje;
}

/// Sube las hojas de un examen y devuelve el reporte de recepción (RF-01).
///
/// El nombre del campo del formulario, `archivos`, tiene que coincidir con el del parámetro
/// del endpoint en `api/main.py`: es el contrato entre los dos lados.
Future<ResultadoCarga> subirHojas(
  String examenId,
  List<ArchivoSeleccionado> archivos,
) async {
  final uri = Uri.parse('$backendUrl/examenes/$examenId/hojas');
  final peticion = http.MultipartRequest('POST', uri);

  for (final archivo in archivos) {
    peticion.files.add(http.MultipartFile.fromBytes(
      'archivos',
      archivo.contenido,
      filename: archivo.nombre,
    ));
  }

  final http.StreamedResponse flujo;
  try {
    flujo = await peticion.send();
  } catch (error) {
    throw const ExcepcionDeCarga(
      'No se pudo contactar con la API. Revise su conexión y vuelva a intentarlo.',
    );
  }

  final http.Response respuesta;
  try {
    respuesta = await http.Response.fromStream(flujo);
  } catch (_) {
    throw const ExcepcionDeCarga(
      'Se cortó la conexión mientras llegaba la respuesta. Algunas hojas pudieron entrar: '
      'revise antes de volver a subir el lote.',
    );
  }
  if (respuesta.statusCode != 200) {
    throw ExcepcionDeCarga(
      'La API respondió ${respuesta.statusCode}. No se recibió ninguna hoja.',
    );
  }

  // Un 200 con un cuerpo que no se puede leer es tan grave como no tener respuesta: las hojas
  // pudieron entrar y el docente no tiene el reporte. Se dice así, en vez de dejar escapar un
  // error de formato que la pantalla no sabría explicar.
  try {
    return ResultadoCarga.desdeJson(
      jsonDecode(utf8.decode(respuesta.bodyBytes)) as Map<String, dynamic>,
    );
  } catch (_) {
    throw const ExcepcionDeCarga(
      'La API recibió el lote, pero su reporte no se pudo leer. Algunas hojas pudieron entrar: '
      'revise antes de volver a subir el lote.',
    );
  }
}
