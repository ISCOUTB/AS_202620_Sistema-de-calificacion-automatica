import 'package:http/http.dart' as http;

import '../common/api/cliente_con_sesion.dart';
import '../common/api/servicio_salud.dart' as salud;
import '../features/carga/data/camara.dart' as camara;
import '../features/carga/data/selector_archivos.dart' as selector;
import '../features/carga/data/tomar_foto.dart' as foto;
import '../features/carga/data/servicio_examenes.dart' as examenes;
import '../features/carga/data/servicio_carga.dart' as carga;
import '../features/carga/data/servicio_resultados.dart' as resultados;
import '../features/panel/data/servicio_panel.dart' as panel;
import '../features/pauta/data/servicio_clave.dart' as clave;
import '../features/pauta/data/servicio_distractores.dart' as distractores;
import '../features/revision/data/servicio_revision.dart' as revision;
import 'sesion_actual.dart';

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
    this.encabezadosDelRecorte,
    this.consultarClave,
    this.guardarClave,
    this.habilitarClave,
    this.crearExamen,
    this.consultarPanel,
    this.tomarFoto,
  });

  /// Las implementaciones reales: HTTP contra `BACKEND_URL` y el diálogo del navegador. La cámara
  /// solo en una pantalla táctil.
  ///
  /// Todo lo que va a la API pasa por un mismo [ClienteConSesion] (ADR-0025): manda el token de
  /// [sesion] y, si la API responde 401, la cierra para volver a la entrada. `/health` no lo usa,
  /// porque la sonda de vida no pide sesión. [interno] existe para las pruebas.
  factory ServiciosApp.reales(SesionActual sesion, {http.Client? interno}) {
    final cliente = ClienteConSesion(
      token: () => sesion.token,
      alVencer: sesion.vencer,
      interno: interno,
    );
    return ServiciosApp(
      tomarFoto: camara.esPantallaTactil() ? foto.tomarFoto : null,
      verificarSalud: salud.verificarSalud,
      seleccionarArchivos: selector.seleccionarArchivos,
      subirHojas: (examenId, archivos) => carga.subirHojas(examenId, archivos, cliente: cliente),
      proponerDistractores: (solicitud) =>
          distractores.proponerDistractores(solicitud, cliente: cliente),
      consultarResultados: (examenId) =>
          resultados.consultarResultados(examenId, cliente: cliente),
      listarExamenes: () => examenes.listarExamenes(cliente: cliente),
      consultarRevision: (examenId) => revision.consultarRevision(examenId, cliente: cliente),
      guardarRevision: (examenId, hojaId, opciones) =>
          revision.guardarRevision(examenId, hojaId, opciones, cliente: cliente),
      urlDelRecorte: revision.urlDelRecorte,
      // El recorte lo pide `Image.network`, que no pasa por el cliente: en web baja la imagen sin
      // credenciales, así que el token va como encabezado de la imagen.
      encabezadosDelRecorte: () => {
        if (sesion.token case final token?) 'Authorization': 'Bearer $token',
      },
      consultarClave: (examenId) => clave.consultarClave(examenId, cliente: cliente),
      guardarClave: (examenId, respuestas) =>
          clave.guardarClave(examenId, respuestas, cliente: cliente),
      habilitarClave: (examenId) => clave.habilitarClave(examenId, cliente: cliente),
      crearExamen: (nombre) => examenes.crearExamen(nombre, cliente: cliente),
      consultarPanel: (examenId) => panel.consultarPanel(examenId, cliente: cliente),
    );
  }

  final Future<bool> Function() verificarSalud;

  /// Toma una foto con la cámara del celular y la prepara para subir. Opcional: sin él, la carga
  /// solo ofrece elegir archivos.
  final Future<carga.ArchivoSeleccionado?> Function()? tomarFoto;

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
  /// el recorte de cada pregunta. Opcionales: sin ellos, la pantalla de revisión queda vacía. Quién
  /// guarda no viaja: es el docente de la sesión (ADR-0025).
  final Future<revision.RevisionDelExamen> Function(String examenId)? consultarRevision;
  final Future<resultados.ResultadoDeHoja> Function(
    String examenId,
    String hojaId,
    Map<int, String?> opciones,
  )? guardarRevision;
  final String Function(String examenId, String hojaId, int numero)? urlDelRecorte;

  /// Los encabezados con que se pide cada recorte: el token de la sesión. Sin él, la imagen se
  /// pide sin encabezados.
  final Map<String, String> Function()? encabezadosDelRecorte;

  /// La clave de un examen (A-04, ADR-0026): pedirla, guardarla y habilitarla. Opcionales: sin
  /// ellos, la pantalla de pauta no ofrece registrar la clave.
  final Future<clave.ClaveDelExamen?> Function(String examenId)? consultarClave;
  final Future<clave.ClaveDelExamen> Function(String examenId, List<String> respuestas)?
      guardarClave;
  final Future<clave.ClaveDelExamen> Function(String examenId)? habilitarClave;

  /// Crea el examen con el nombre que escribe el docente y le da su identificador (ADR-0028).
  /// Opcional: sin él, la clave se registra con el identificador escrito, como antes.
  final Future<examenes.ExamenCreado> Function(String nombre)? crearExamen;

  /// Las cifras del panel de un examen (RF-05). Opcional: sin él, el panel no muestra cifras.
  final Future<panel.PanelDelExamen> Function(String examenId)? consultarPanel;
}
