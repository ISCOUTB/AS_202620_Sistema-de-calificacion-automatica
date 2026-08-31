import 'package:file_picker/file_picker.dart';

import 'servicio_carga.dart';

/// Abre el diálogo de archivos del navegador y devuelve lo que el docente eligió.
///
/// **Es el único punto de la aplicación que depende del navegador**, y está aislado a
/// propósito: la pantalla recibe esta función inyectada, así que se puede probar con un
/// sustituto sin abrir ningún diálogo. Si `file_picker` cambia o se reemplaza, este archivo es
/// lo único que hay que tocar. Ya sirvió para eso: la versión 12 del paquete rehízo su API por
/// completo y el cambio no salió de estas líneas.
///
/// La lista de extensiones repite la de `ingesta` como comodidad para el usuario, no como
/// validación: la validación de verdad la hace el backend, que además revisa los primeros
/// bytes. Aquí solo filtra lo que el diálogo del sistema le ofrece al docente.
Future<List<ArchivoSeleccionado>> seleccionarArchivos() async {
  // Devuelve una lista vacía si el docente cancela, así que no hay caso nulo que manejar.
  // Sin `allowMultiple`: en la versión 12 `pickFiles` ya es multiarchivo por definición, y el
  // parámetro quedó obsoleto. Para una sola hoja el paquete ofrece `pickFile`.
  final elegidos = await FilePicker.pickFiles(
    type: FileType.custom,
    allowedExtensions: const ['jpg', 'jpeg', 'png', 'pdf'],
  );

  return [
    for (final archivo in elegidos)
      ArchivoSeleccionado(
        nombre: archivo.name,
        // En web no hay ruta de archivo que el backend pueda leer: el contenido tiene que
        // viajar en bytes, y `readAsBytes` es la forma de obtenerlos desde la versión 12.
        contenido: await archivo.readAsBytes(),
      ),
  ];
}
