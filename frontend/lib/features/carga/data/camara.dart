/// La cámara del celular, desde el navegador: abrirla para una foto y saber si la pantalla es
/// táctil, que es cuando se ofrece el botón «Tomar foto».
///
/// La versión de verdad usa el navegador, que no existe en las pruebas: ahí la cámara no se abre
/// y la pantalla no es táctil. Lo que hace la aplicación con la foto (`tomar_foto.dart`) se prueba
/// igual, con un sustituto.
library;

export 'camara_sin_navegador.dart' if (dart.library.js_interop) 'camara_navegador.dart';
