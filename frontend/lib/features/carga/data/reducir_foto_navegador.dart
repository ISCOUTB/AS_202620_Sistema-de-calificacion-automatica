import 'dart:async';
import 'dart:js_interop';

import 'package:web/web.dart' as web;

import 'preparacion_de_hojas.dart';
import 'servicio_carga.dart';

/// Reduce una foto con el canvas del navegador, que la decodifica y la vuelve a codificar con el
/// código nativo: unos milisegundos por foto, donde decodificarla en Dart tardaría segundos.
///
/// `createImageBitmap` aplica la orientación que guarda la cámara en el EXIF, así que la foto
/// sale derecha aunque el celular estuviera de lado; de todos modos, la lectura se orienta sola.
/// El gris lo pone el filtro del canvas; un navegador que no lo tenga deja la foto en color, que
/// pesa más pero se lee igual.
///
/// Devuelve null si el navegador no pudo con el archivo: entonces viaja como llegó, y la API dice
/// si sirve.
Future<ArchivoSeleccionado?> reducirFoto(ArchivoSeleccionado archivo) async {
  try {
    final blob = web.Blob(<JSAny>[archivo.contenido.toJS].toJS);
    final imagen = await web.window.createImageBitmap(blob).toDart;
    final escala = escalaPara(imagen.width, imagen.height);
    final ancho = (imagen.width * escala).round();
    final alto = (imagen.height * escala).round();

    final lienzo = web.HTMLCanvasElement()
      ..width = ancho
      ..height = alto;
    final contexto = lienzo.getContext('2d') as web.CanvasRenderingContext2D;
    contexto
      ..filter = 'grayscale(1)'
      ..imageSmoothingEnabled = true
      ..imageSmoothingQuality = 'high'
      ..drawImage(imagen, 0, 0, ancho, alto);
    imagen.close();

    final listo = Completer<web.Blob?>();
    lienzo.toBlob(
      ((web.Blob? resultado) => listo.complete(resultado)).toJS,
      'image/jpeg',
      calidadJpeg.toJS,
    );
    final jpeg = await listo.future;
    if (jpeg == null) return null;
    final bytes = (await jpeg.arrayBuffer().toDart).toDart.asUint8List();
    return ArchivoSeleccionado(
      nombre: nombreJpg(archivo.nombre),
      contenido: bytes,
      ladoMayorPx: ancho > alto ? ancho : alto,
    );
  } catch (_) {
    return null;
  }
}
