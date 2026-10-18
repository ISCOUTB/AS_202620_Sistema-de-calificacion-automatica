import '../common/api/servicio_salud.dart' as salud;
import '../features/carga/data/selector_archivos.dart' as selector;
import '../features/carga/data/servicio_carga.dart' as carga;
import '../features/pauta/data/servicio_distractores.dart' as distractores;

/// Las operaciones que la interfaz necesita del mundo exterior (la API y el navegador),
/// reunidas para inyectarlas.
///
/// Las pantallas no llaman a HTTP ni abren diálogos por su cuenta: reciben estas funciones. Así
/// las pruebas de widget ejercitan la aplicación entera con sustitutos, sin backend y sin
/// diálogo de archivos.
///
/// Los imports llevan prefijo a propósito: dentro del constructor de abajo, un nombre como
/// `subirHojas` se resolvería al campo y no a la función del servicio, el choque que ya apareció
/// una vez con `verificarSalud`.
class ServiciosApp {
  const ServiciosApp({
    required this.verificarSalud,
    required this.seleccionarArchivos,
    required this.subirHojas,
    required this.proponerDistractores,
  });

  /// Las implementaciones reales: HTTP contra `BACKEND_URL` y el diálogo del navegador.
  factory ServiciosApp.reales() => const ServiciosApp(
        verificarSalud: salud.verificarSalud,
        seleccionarArchivos: selector.seleccionarArchivos,
        subirHojas: carga.subirHojas,
        proponerDistractores: distractores.proponerDistractores,
      );

  final Future<bool> Function() verificarSalud;
  final Future<List<carga.ArchivoSeleccionado>> Function() seleccionarArchivos;
  final Future<carga.ResultadoCarga> Function(String, List<carga.ArchivoSeleccionado>) subirHojas;
  final Future<distractores.ResultadoDistractores> Function(distractores.SolicitudDistractores)
      proponerDistractores;
}
