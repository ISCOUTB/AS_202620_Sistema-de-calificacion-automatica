import 'package:flutter/material.dart';

/// Pequeñas reglas de redacción y formato que comparten las piezas de la pantalla de carga.

/// «1 archivo», «3 archivos». La concordancia importa: un «1 hojas» se lee como un descuido, y en
/// un reporte cuyo valor es la exactitud cualquier descuido le resta confianza.
String contar(int cantidad, String singular, String plural) =>
    '$cantidad ${cantidad == 1 ? singular : plural}';

/// Tamaño legible de [bytes], en KB o MB y con coma decimal.
///
/// Los KB se redondean hacia arriba, como en el explorador de archivos: un archivo de 300 bytes
/// se muestra como «1 KB» y no como «0 KB», que se leería como un archivo vacío.
String describirTamano(int bytes) {
  const kb = 1024;
  const mb = kb * 1024;
  if (bytes < mb) return '${(bytes / kb).ceil()} KB';
  final valor = bytes / mb;
  final texto =
      valor >= 100 ? valor.round().toString() : valor.toStringAsFixed(1).replaceAll('.', ',');
  return '$texto MB';
}

/// Ícono según la extensión. Es solo una pista visual para reconocer el archivo en la lista: el
/// tipo real lo decide el backend leyendo los primeros bytes, no el nombre.
IconData iconoDeArchivo(String nombre) => nombre.toLowerCase().endsWith('.pdf')
    ? Icons.picture_as_pdf_outlined
    : Icons.image_outlined;

/// Los primeros ocho caracteres del identificador de un trabajo: bastan para distinguir las hojas
/// de un lote a simple vista, y el identificador completo sigue a la vista debajo.
String idCorto(String id) => id.length <= 8 ? id : id.substring(0, 8);
