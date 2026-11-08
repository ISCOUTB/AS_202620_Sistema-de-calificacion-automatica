import 'package:file_picker/file_picker.dart';

import 'preparacion_de_hojas.dart';
import 'reducir_foto.dart';
import 'servicio_carga.dart';

/// Abre el diálogo de archivos del navegador y devuelve lo que el docente eligió, con las fotos
/// ya preparadas para subir (`preparacion_de_hojas.dart`).
///
/// **Es el único punto de la aplicación que depende del navegador**, junto con
/// `reducir_foto.dart`, y está aislado a propósito: la pantalla recibe esta función inyectada,
/// así que se puede probar con un sustituto sin abrir ningún diálogo. Si `file_picker` cambia o
/// se reemplaza, este archivo es lo único que hay que tocar. Ya sirvió para eso: la versión 12 del
/// paquete rehízo su API por completo y el cambio no salió de estas líneas.
///
/// La lista de extensiones repite la de `ingesta` como comodidad para el usuario, no como
/// validación: la validación de verdad la hace el backend, que además revisa los primeros
/// bytes. Aquí solo filtra lo que el diálogo del sistema le ofrece al docente. No ofrece PDF:
/// `ingesta` lo recibe, pero la lectura de esta versión no lo lee, y la hoja quedaría ilegible.
///
/// Cada archivo se lee y se prepara antes de leer el siguiente, y de la foto original no queda
/// nada en memoria: 200 fotos de celular son unos 800 MB, que el navegador no tiene por qué
/// juntar. [alAvanzar] recibe cuántos van y cuántos son.
Future<List<ArchivoSeleccionado>> seleccionarArchivos({
  void Function(int hechas, int total)? alAvanzar,
}) async {
  // Devuelve una lista vacía si el docente cancela, así que no hay caso nulo que manejar.
  // Sin `allowMultiple`: en la versión 12 `pickFiles` ya es multiarchivo por definición, y el
  // parámetro quedó obsoleto. Para una sola hoja el paquete ofrece `pickFile`.
  final elegidos = await FilePicker.pickFiles(
    type: FileType.custom,
    allowedExtensions: const ['jpg', 'jpeg', 'png'],
  );

  final preparados = <ArchivoSeleccionado>[];
  for (final archivo in elegidos) {
    final leido = ArchivoSeleccionado(
      nombre: archivo.name,
      // En web no hay ruta de archivo que el backend pueda leer: el contenido tiene que
      // viajar en bytes, y `readAsBytes` es la forma de obtenerlos desde la versión 12.
      contenido: await archivo.readAsBytes(),
    );
    preparados.add(await prepararUna(leido, reducirFoto));
    alAvanzar?.call(preparados.length, elegidos.length);
  }
  return preparados;
}
