import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../../../common/api/servicio_salud.dart' show backendUrl;
import 'preparacion_de_hojas.dart' show repartirEnTandas;

/// Un archivo elegido por el docente, ya leído a memoria.
///
/// Flutter web no puede pasarle una ruta al backend (el navegador no expone rutas del sistema
/// de archivos), así que el contenido viaja en bytes.
class ArchivoSeleccionado {
  const ArchivoSeleccionado({required this.nombre, required this.contenido, this.ladoMayorPx});

  final String nombre;
  final Uint8List contenido;

  /// El lado mayor de la imagen, en píxeles, tal como se va a subir. Nulo si el navegador no la
  /// pudo abrir. Sirve para avisar antes de subir que una foto no alcanza la resolución mínima
  /// (`tienePocaResolucion`).
  final int? ladoMayorPx;
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
    this.hojaId,
  });

  final String nombreArchivo;
  final String trabajoId;
  final EstadoHoja estado;

  /// La identidad de la hoja (ADR-0018). Con ella se une el resultado de la lectura con el
  /// archivo que eligió el docente. Nula solo en respuestas anteriores al contrato 1.3.0.
  final String? hojaId;

  factory HojaAceptada.desdeJson(Map<String, dynamic> json) => HojaAceptada(
        nombreArchivo: json['nombre_archivo'] as String,
        trabajoId: json['trabajo_id'] as String,
        estado: EstadoHoja.desdeTexto(json['estado'] as String?),
        hojaId: json['hoja_id'] as String?,
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
/// dice «este archivo no sirve, y por esto»; esta excepción significa que no hubo reporte.
///
/// [pudieronEntrar] separa los dos casos que el docente tiene que tratar distinto: si es falso,
/// la petición no llegó a procesarse y volver a subir el lote es lo correcto; si es verdadero,
/// algunas hojas pudieron entrar, y volver a subirlas las duplicaría, porque el sistema todavía
/// no detecta una hoja repetida (R-24).
class ExcepcionDeCarga implements Exception {
  const ExcepcionDeCarga(this.mensaje, {this.pudieronEntrar = false});

  final String mensaje;
  final bool pudieronEntrar;

  @override
  String toString() => mensaje;
}

/// Sube las hojas de un examen y devuelve el reporte de recepción (RF-01).
///
/// Las manda en tandas de hasta 90 MB y 250 hojas (`repartirEnTandas`), una petición por tanda, y
/// junta los reportes en uno: un examen de 200 fotos ya preparadas pesa unos 130 MB, y la API corta
/// cada petición en 100 MB. Si una tanda falla después de que otra entró, la excepción lo dice:
/// volver a subir todo duplicaría las hojas que ya entraron (R-24).
///
/// [cliente] existe para las pruebas; en la aplicación se usa el de `package:http`.
Future<ResultadoCarga> subirHojas(
  String examenId,
  List<ArchivoSeleccionado> archivos, {
  http.Client? cliente,
}) async {
  final aceptadas = <HojaAceptada>[];
  final rechazados = <ArchivoRechazado>[];
  var procesados = 0;
  for (final tanda in repartirEnTandas(archivos)) {
    final ResultadoCarga parcial;
    try {
      parcial = await _subirTanda(examenId, tanda, cliente: cliente);
    } on ExcepcionDeCarga catch (error) {
      if (procesados == 0) rethrow;
      throw ExcepcionDeCarga(
        'Entraron ${aceptadas.length} de ${archivos.length} hojas en las primeras tandas, y la '
        'siguiente no se completó. ${error.mensaje}',
        pudieronEntrar: true,
      );
    }
    procesados += parcial.totalProcesados;
    aceptadas.addAll(parcial.aceptadas);
    rechazados.addAll(parcial.rechazados);
  }
  return ResultadoCarga(totalProcesados: procesados, aceptadas: aceptadas, rechazados: rechazados);
}

/// Una petición con una tanda de hojas.
///
/// El nombre del campo del formulario, `archivos`, tiene que coincidir con el del parámetro
/// del endpoint en `api/main.py`: es el contrato entre los dos lados.
Future<ResultadoCarga> _subirTanda(
  String examenId,
  List<ArchivoSeleccionado> archivos, {
  http.Client? cliente,
}) async {
  final http.StreamedResponse flujo;
  try {
    // El examen va codificado: sin eso, `P2#1` mandaba la petición a `/examenes/P2` (lo demás
    // quedaba como fragmento) y un `?` la cortaba como consulta. Va dentro del `try` para que
    // cualquier error al armarla se explique como una petición que no salió.
    final uri = Uri.parse('$backendUrl/examenes/${Uri.encodeComponent(examenId)}/hojas');
    final peticion = http.MultipartRequest('POST', uri);
    for (final archivo in archivos) {
      peticion.files.add(http.MultipartFile.fromBytes(
        'archivos',
        archivo.contenido,
        filename: archivo.nombre,
      ));
    }
    flujo = await (cliente?.send(peticion) ?? peticion.send());
  } catch (error) {
    throw const ExcepcionDeCarga(
      'No se pudo contactar con el servidor. Revise su conexión y vuelva a intentarlo.',
    );
  }

  final http.Response respuesta;
  try {
    respuesta = await http.Response.fromStream(flujo);
  } catch (_) {
    throw const ExcepcionDeCarga(
      'Se cortó la conexión mientras llegaba la respuesta. Algunas hojas pudieron entrar: '
      'revise antes de volver a subir el lote.',
      pudieronEntrar: true,
    );
  }
  // Un 4xx sale antes de procesar el lote (validación, ruta, tamaño), así que ahí sí no entró
  // nada. Un 5xx no lo garantiza: el proxy de Render puede devolver 502 o 504 mientras la API
  // sigue trabajando, y antes este mensaje decía «No se recibió ninguna hoja» en los dos casos.
  final codigo = respuesta.statusCode;
  if (codigo >= 400 && codigo < 500) {
    throw ExcepcionDeCarga('El servidor rechazó la petición ($codigo). No entró ninguna hoja.');
  }
  if (codigo != 200) {
    throw ExcepcionDeCarga(
      'El servidor respondió $codigo. Algunas hojas pudieron entrar: revise antes de volver a subir '
      'el lote.',
      pudieronEntrar: true,
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
      'El servidor recibió el lote, pero su reporte no se pudo leer. Algunas hojas pudieron entrar: '
      'revise antes de volver a subir el lote.',
      pudieronEntrar: true,
    );
  }
}
