/// Reduce una foto en el navegador: la pasa a gris y le deja 3 200 px en el lado mayor.
///
/// La versión de verdad usa el canvas del navegador, que no existe fuera de él. Las pruebas
/// corren en la máquina virtual de Dart, así que ahí se usa una que no reduce nada; la lógica que
/// decide qué hacer con el resultado (`preparacion_de_hojas.dart`) se prueba igual con un
/// sustituto.
library;

export 'reducir_foto_sin_navegador.dart'
    if (dart.library.js_interop) 'reducir_foto_navegador.dart';
