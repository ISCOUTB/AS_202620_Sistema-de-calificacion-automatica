import 'servicio_carga.dart';

/// Fuera del navegador no hay cámara: es como si el docente la cerrara sin tomar nada.
Future<ArchivoSeleccionado?> abrirCamara() async => null;

/// Fuera del navegador no hay pantalla táctil, así que no se ofrece «Tomar foto».
bool esPantallaTactil() => false;
