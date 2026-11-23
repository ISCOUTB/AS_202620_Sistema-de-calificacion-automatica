/// Dónde guarda el navegador la sesión entre una recarga de la página y la siguiente (ADR-0025).
///
/// La versión de verdad usa el almacenamiento del navegador, que no existe en las pruebas: ahí la
/// sesión vive solo en memoria. Lo que hace la aplicación con ella se prueba igual, con
/// `AlmacenEnMemoria`.
library;

export 'almacen_de_sesion_sin_navegador.dart'
    if (dart.library.js_interop) 'almacen_de_sesion_navegador.dart';
