import 'sesion_actual.dart';

/// Fuera del navegador no hay dónde guardar la sesión: queda en memoria.
AlmacenDeSesion almacenDelNavegador() => AlmacenEnMemoria();
