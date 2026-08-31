import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import 'servicio_salud.dart' show backendUrl;

/// Un archivo elegido por el docente, ya leído a memoria.
///
/// Flutter web no puede pasarle una ruta al backend —el navegador no expone rutas del sistema
/// de archivos—, así que el contenido viaja en bytes.
class ArchivoSeleccionado {
  const ArchivoSeleccionado({required this.nombre, required this.contenido});

  final String nombre;
  final Uint8List contenido;
}

/// Una hoja que el backend aceptó, almacenó y encoló.
class HojaAceptada {
  const HojaAceptada({required this.nombreArchivo, required this.trabajoId});

  final String nombreArchivo;
  final String trabajoId;

  factory HojaAceptada.desdeJson(Map<String, dynamic> json) => HojaAceptada(
        nombreArchivo: json['nombre_archivo'] as String,
        trabajoId: json['trabajo_id'] as String,
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
      'No se pudo contactar al backend. Revisa que esté levantado y vuelve a intentar.',
    );
  }

  final respuesta = await http.Response.fromStream(flujo);
  if (respuesta.statusCode != 200) {
    throw ExcepcionDeCarga(
      'El backend respondió ${respuesta.statusCode}. No se recibió ninguna hoja.',
    );
  }

  return ResultadoCarga.desdeJson(
    jsonDecode(utf8.decode(respuesta.bodyBytes)) as Map<String, dynamic>,
  );
}
