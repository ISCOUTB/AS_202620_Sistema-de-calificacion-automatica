import 'dart:math' as math;

import 'servicio_carga.dart';

/// Cómo se preparan las fotos antes de subirlas, sin depender del navegador: cuánto se reducen,
/// cómo se llaman después y en qué tandas viajan.
///
/// **Por qué se reducen.** Una foto de celular pesa de 3,5 a 4,6 MB, en color y con mucha calidad.
/// La API acepta hasta 100 MB por petición y 256 MB por día (ADR-0022): un examen de 200 fotos así
/// no cabe ni en un día. La lectura trabaja en gris y no necesita tanta resolución, así que el
/// navegador pasa cada foto a gris y la deja con [ladoMaximoPx] en el lado mayor. En las fotos del
/// prototipo (R-05) eso dejó cada hoja en unos 650 KB, y la lectura dio lo mismo, burbuja por
/// burbuja, que con la original.
///
/// **Por qué 3 200 px.** La lectura rechaza una hoja por debajo de 7,5 px/mm (ADR-0023). La hoja
/// mide 279,4 mm de alto: con 3 200 px en el lado mayor, alcanza con que ocupe dos tercios de la
/// foto. Una foto que ya es más chica no se agranda.

/// El lado mayor de una foto después de prepararla.
const ladoMaximoPx = 3200;

/// Por debajo de este lado mayor, una foto no alcanza los 7,5 px/mm ni con la hoja llenándola
/// entera: 279,4 mm × 7,5 = 2 096 px. La pantalla lo avisa antes de subir; la lectura la dejaría
/// ilegible.
const ladoMinimoPx = 2100;

/// Si la foto, ya preparada, no puede llegar a la resolución que pide la lectura.
bool tienePocaResolucion(ArchivoSeleccionado archivo) =>
    archivo.ladoMayorPx != null && archivo.ladoMayorPx! < ladoMinimoPx;

/// La calidad del JPEG que sale del navegador, de 0 a 1.
const calidadJpeg = 0.8;

/// Lo que se manda en cada petición. La API corta el cuerpo en 100 MB (incluido lo que agrega el
/// formulario) y admite 250 hojas por lote (`ingesta/presupuesto.py`).
const bytesPorTanda = 90 * 1024 * 1024;
const hojasPorTanda = 250;

/// Cuánto hay que multiplicar el ancho y el alto de una foto para que su lado mayor quede en
/// [ladoMaximoPx]. Nunca agranda.
double escalaPara(int ancho, int alto) {
  final mayor = math.max(ancho, alto);
  return mayor <= ladoMaximoPx ? 1 : ladoMaximoPx / mayor;
}

/// Las fotos son lo que se prepara; un PDF o cualquier otra cosa viaja como está, y la API dice
/// qué hacer con ella.
bool esFoto(ArchivoSeleccionado archivo) {
  final nombre = archivo.nombre.toLowerCase();
  return nombre.endsWith('.jpg') || nombre.endsWith('.jpeg') || nombre.endsWith('.png');
}

/// El nombre de una foto preparada, que siempre es un JPEG: la API compara la extensión con los
/// primeros bytes, y un PNG convertido a JPEG con su nombre de antes se rechazaría.
String nombreJpg(String nombre) {
  final punto = nombre.lastIndexOf('.');
  final base = punto > 0 ? nombre.substring(0, punto) : nombre;
  return '$base.jpg';
}

/// Prepara una hoja con [reducir], que devuelve la foto reducida o null si el navegador no la pudo
/// procesar. Se queda con la versión más liviana: un escaneo que ya era chico, o una foto que el
/// navegador no entendió, viaja como llegó, y la API decide.
Future<ArchivoSeleccionado> prepararUna(
  ArchivoSeleccionado archivo,
  Future<ArchivoSeleccionado?> Function(ArchivoSeleccionado) reducir,
) async {
  if (!esFoto(archivo)) return archivo;
  final reducida = await reducir(archivo);
  if (reducida == null) return archivo;
  if (reducida.contenido.length >= archivo.contenido.length) {
    // Se sube la original, pero con el tamaño que midió el navegador: si no hubo que reducirla,
    // es el mismo.
    return ArchivoSeleccionado(
      nombre: archivo.nombre,
      contenido: archivo.contenido,
      ladoMayorPx: reducida.ladoMayorPx,
    );
  }
  return reducida;
}

/// Reparte los archivos en tandas de hasta [maxBytes] y [maxHojas], en el orden en que vienen.
/// Un archivo más grande que [maxBytes] va solo en su tanda: la API lo rechaza con su motivo.
List<List<ArchivoSeleccionado>> repartirEnTandas(
  List<ArchivoSeleccionado> archivos, {
  int maxBytes = bytesPorTanda,
  int maxHojas = hojasPorTanda,
}) {
  final tandas = <List<ArchivoSeleccionado>>[];
  var actual = <ArchivoSeleccionado>[];
  var bytes = 0;
  for (final archivo in archivos) {
    final peso = archivo.contenido.length;
    if (actual.isNotEmpty && (bytes + peso > maxBytes || actual.length == maxHojas)) {
      tandas.add(actual);
      actual = <ArchivoSeleccionado>[];
      bytes = 0;
    }
    actual.add(archivo);
    bytes += peso;
  }
  if (actual.isNotEmpty) tandas.add(actual);
  return tandas;
}
