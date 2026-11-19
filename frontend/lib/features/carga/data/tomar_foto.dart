import 'camara.dart' as camara;
import 'preparacion_de_hojas.dart';
import 'reducir_foto.dart' as reduccion;
import 'servicio_carga.dart';

/// Toma una foto con la cámara del celular y la deja lista para subir, como si se hubiera elegido
/// en la galería: con un nombre propio y preparada por `prepararUna`.
///
/// Devuelve null si el docente cierra la cámara sin tomar nada. Toma una sola foto: el navegador
/// solo abre la cámara cuando la persona toca un botón, así que cada hoja es un toque. La pantalla
/// suma cada foto a la selección, como hace con lo que se elige en la galería.
///
/// Las tres dependencias se reciben para probarla sin navegador; por omisión son la cámara, el
/// reloj y la reducción de verdad.
Future<ArchivoSeleccionado?> tomarFoto({
  Future<ArchivoSeleccionado?> Function() abrir = camara.abrirCamara,
  DateTime Function() ahora = DateTime.now,
  Future<ArchivoSeleccionado?> Function(ArchivoSeleccionado) reducir = reduccion.reducirFoto,
}) async {
  final foto = await abrir();
  if (foto == null) return null;
  final renombrada = ArchivoSeleccionado(
    nombre: nombreDeFoto(ahora(), foto.nombre),
    contenido: foto.contenido,
  );
  return prepararUna(renombrada, reducir);
}

/// «foto 14.32.05.jpg»: la hora en que se tomó, con la extensión que trae la cámara. En iPhone
/// todas las fotos de la cámara llegan como «image.jpg», y con ese nombre el docente no las
/// distinguiría en la pantalla de revisión.
String nombreDeFoto(DateTime momento, String nombreDeLaCamara) {
  String dos(int n) => n.toString().padLeft(2, '0');
  final punto = nombreDeLaCamara.lastIndexOf('.');
  final extension = punto < 0 ? 'jpg' : nombreDeLaCamara.substring(punto + 1).toLowerCase();
  return 'foto ${dos(momento.hour)}.${dos(momento.minute)}.${dos(momento.second)}.$extension';
}
