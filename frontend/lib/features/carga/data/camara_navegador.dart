import 'dart:async';
import 'dart:js_interop';

import 'package:web/web.dart' as web;

import 'servicio_carga.dart';

/// Abre la cámara trasera para una foto: un selector de archivos con `capture="environment"`, que
/// Android y iPhone abren directo en la cámara. Se mete oculto en la página, se le hace clic y se
/// saca, como hace `file_picker` (algunos Safari no lo abren si no está en la página).
///
/// Devuelve la foto con el nombre que le puso la cámara, o null si el docente la cierra sin tomar
/// nada (el evento `cancel`). Un navegador viejo que no avise la cancelación deja esta espera
/// abierta; la pantalla no se bloquea por eso, y el siguiente toque abre otra.
Future<ArchivoSeleccionado?> abrirCamara() async {
  final entrada = web.HTMLInputElement()
    ..type = 'file'
    ..accept = 'image/*'
    ..style.display = 'none';
  entrada.setAttribute('capture', 'environment');

  final elegido = Completer<web.File?>();
  entrada.addEventListener(
    'change',
    ((web.Event _) {
      if (!elegido.isCompleted) elegido.complete(entrada.files?.item(0));
    }).toJS,
  );
  entrada.addEventListener(
    'cancel',
    ((web.Event _) {
      if (!elegido.isCompleted) elegido.complete(null);
    }).toJS,
  );

  web.document.body?.append(entrada);
  entrada.click();
  entrada.remove();

  final archivo = await elegido.future;
  if (archivo == null) return null;
  final bytes = (await archivo.arrayBuffer().toDart).toDart.asUint8List();
  return ArchivoSeleccionado(nombre: archivo.name, contenido: bytes);
}

/// Si el puntero principal es un dedo: celular o tablet, incluido el iPad, que se presenta como
/// computador. Es cuando se ofrece «Tomar foto»; en el computador ese botón abriría el mismo
/// diálogo de archivos que «Seleccionar archivos».
bool esPantallaTactil() => web.window.matchMedia('(pointer: coarse)').matches;
