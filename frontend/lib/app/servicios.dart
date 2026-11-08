import '../common/api/servicio_salud.dart' as salud;
import '../features/carga/data/selector_archivos.dart' as selector;
import '../features/carga/data/servicio_examenes.dart' as examenes;
import '../features/carga/data/servicio_carga.dart' as carga;
import '../features/carga/data/servicio_resultados.dart' as resultados;
import '../features/pauta/data/servicio_distractores.dart' as distractores;
import '../features/revision/data/servicio_revision.dart' as revision;

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
    this.consultarResultados,
    this.listarExamenes,
    this.consultarRevision,
    this.guardarRevision,
    this.urlDelRecorte,
  });

  /// Las implementaciones reales: HTTP contra `BACKEND_URL` y el diálogo del navegador.
  factory ServiciosApp.reales() => const ServiciosApp(
        verificarSalud: salud.verificarSalud,
        seleccionarArchivos: selector.seleccionarArchivos,
        subirHojas: carga.subirHojas,
        proponerDistractores: distractores.proponerDistractores,
        consultarResultados: resultados.consultarResultados,
        listarExamenes: examenes.listarExamenes,
        consultarRevision: revision.consultarRevision,
        guardarRevision: revision.guardarRevision,
        urlDelRecorte: revision.urlDelRecorte,
      );

  final Future<bool> Function() verificarSalud;

  /// Abre el diálogo y prepara las fotos elegidas; `alAvanzar` recibe cuántas van y cuántas son.
  final Future<List<carga.ArchivoSeleccionado>> Function({
    void Function(int hechas, int total)? alAvanzar,
  }) seleccionarArchivos;
  final Future<carga.ResultadoCarga> Function(String, List<carga.ArchivoSeleccionado>) subirHojas;
  final Future<distractores.ResultadoDistractores> Function(distractores.SolicitudDistractores)
      proponerDistractores;

  /// Cómo quedó cada hoja leída de un examen. Opcional: sin él, el reporte de carga se queda en
  /// la recepción, como antes de la lectura.
  final Future<resultados.ResultadosDelExamen> Function(String examenId)? consultarResultados;

  /// Los exámenes con clave, para elegir el de la carga en una lista. Opcional: sin él, el examen
  /// se escribe a mano.
  final Future<List<examenes.ExamenConClave>> Function()? listarExamenes;

  /// La revisión manual (RF-08): lo que espera al docente, guardar lo que resolvió y dónde está
  /// el recorte de cada pregunta. Opcionales: sin ellos, la pantalla de revisión queda vacía.
  final Future<revision.RevisionDelExamen> Function(String examenId)? consultarRevision;
  final Future<resultados.ResultadoDeHoja> Function(
    String examenId,
    String hojaId,
    String por,
    Map<int, String?> opciones,
  )? guardarRevision;
  final String Function(String examenId, String hojaId, int numero)? urlDelRecorte;
}
