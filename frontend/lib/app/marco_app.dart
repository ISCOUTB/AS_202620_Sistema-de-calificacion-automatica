import 'package:flutter/material.dart';

import '../common/api/servicio_salud.dart';
import '../common/tema/tokens.dart';
import '../features/carga/views/pantalla_carga.dart';
import '../features/panel/views/pantalla_panel.dart';
import '../features/pauta/views/pantalla_pauta.dart';
import '../features/revision/views/pantalla_revision.dart';
import 'barra_superior.dart';
import 'servicios.dart';

/// Las cuatro secciones de la aplicación, en el orden del diseño.
enum Seccion {
  panel('Panel', Icons.space_dashboard_outlined, Icons.space_dashboard),
  carga('Carga', Icons.document_scanner_outlined, Icons.document_scanner),
  revision('Revisión', Icons.rate_review_outlined, Icons.rate_review),
  pauta('Pauta & IA', Icons.psychology_outlined, Icons.psychology);

  const Seccion(this.etiqueta, this.icono, this.iconoActivo);

  final String etiqueta;
  final IconData icono;
  final IconData iconoActivo;
}

/// Marco de la aplicación: barra superior, navegación entre secciones y estado de la API.
///
/// La navegación se adapta al ancho: barra inferior en teléfono (zona del pulgar, como pide el
/// diseño) y riel lateral desde [QAnchos.riel], donde una barra inferior de 1 900 px dejaría los
/// destinos lejos entre sí. Las cuatro pantallas viven en un [IndexedStack], así que cambiar de
/// sección no pierde lo que el docente estaba escribiendo o el reporte de la última carga.
class MarcoApp extends StatefulWidget {
  const MarcoApp({
    super.key,
    required this.servicios,
    this.seccionInicial = Seccion.panel,
    this.correo,
    this.alSalir,
  });

  final ServiciosApp servicios;
  final Seccion seccionInicial;

  /// El correo de la sesión, para la barra superior (ADR-0025).
  final String? correo;

  /// Cierra la sesión; sin él, la barra no ofrece salir.
  final VoidCallback? alSalir;

  @override
  State<MarcoApp> createState() => _MarcoAppState();
}

class _MarcoAppState extends State<MarcoApp> {
  final _estadoApi = ValueNotifier<EstadoApi>(EstadoApi.verificando);

  /// Lo que comparten la carga y la revisión: el nombre de archivo de cada hoja subida, el
  /// examen que la carga pide revisar y un aviso cada vez que se guarda una revisión.
  final _nombresDeHojas = ValueNotifier<Map<String, String>>(const {});
  final _examenParaRevisar = ValueNotifier<String?>(null);
  final _revisionesGuardadas = ValueNotifier<int>(0);

  /// Avisa cada vez que Revisión vuelve a la vista: la pantalla sigue viva mientras se mira otra
  /// sección, y lo subido en Carga no aparecía hasta recargar la página.
  final _revisionALaVista = ValueNotifier<int>(0);

  /// Lo mismo para el panel: el worker sigue leyendo hojas, y las cifras se vuelven a pedir.
  final _panelALaVista = ValueNotifier<int>(0);

  /// Avisa que se guardó o se habilitó una clave en Pauta, para que la carga y la revisión
  /// vuelvan a pedir la lista de exámenes: sin esto, uno nuevo no aparecía hasta recargar.
  final _clavesCambiadas = ValueNotifier<int>(0);
  late Seccion _seccion = widget.seccionInicial;

  @override
  void initState() {
    super.initState();
    _comprobarApi();
  }

  @override
  void dispose() {
    _estadoApi.dispose();
    _nombresDeHojas.dispose();
    _examenParaRevisar.dispose();
    _revisionesGuardadas.dispose();
    _revisionALaVista.dispose();
    _panelALaVista.dispose();
    _clavesCambiadas.dispose();
    super.dispose();
  }

  Future<void> _comprobarApi() async {
    _estadoApi.value = EstadoApi.verificando;
    final conectada = await widget.servicios.verificarSalud();
    if (!mounted) return;
    _estadoApi.value = conectada ? EstadoApi.conectada : EstadoApi.sinConexion;
  }

  void _ir(int indice) => _mostrar(Seccion.values[indice]);

  void _mostrar(Seccion seccion) {
    if (seccion == Seccion.revision && _seccion != Seccion.revision) _revisionALaVista.value++;
    if (seccion == Seccion.panel && _seccion != Seccion.panel) _panelALaVista.value++;
    setState(() => _seccion = seccion);
  }

  /// El examen va antes que el aviso: si es otro, la revisión lo pide una sola vez.
  void _irARevisar(String examenId) {
    // Se pasa por null para que avise aunque se pida el mismo examen que la vez anterior: en
    // Revisión pudieron elegir otro desde entonces.
    _examenParaRevisar.value = null;
    _examenParaRevisar.value = examenId;
    _mostrar(Seccion.revision);
  }

  final _claveContenido = GlobalKey();

  @override
  Widget build(BuildContext context) {
    final servicios = widget.servicios;
    final pantallas = [
      PantallaPanel(
        listarExamenes: servicios.listarExamenes,
        consultarPanel: servicios.consultarPanel,
        clavesCambiadas: _clavesCambiadas,
        revisionesGuardadas: _revisionesGuardadas,
        alMostrarse: _panelALaVista,
      ),
      PantallaCarga(
        seleccionarArchivos: servicios.seleccionarArchivos,
        tomarFoto: servicios.tomarFoto,
        subirHojas: servicios.subirHojas,
        consultarResultados: servicios.consultarResultados,
        listarExamenes: servicios.listarExamenes,
        alRecibirHojas: (nombres) =>
            _nombresDeHojas.value = {..._nombresDeHojas.value, ...nombres},
        alRevisar: _irARevisar,
        revisionesGuardadas: _revisionesGuardadas,
        clavesCambiadas: _clavesCambiadas,
        estadoApi: _estadoApi,
      ),
      PantallaRevision(
        listarExamenes: servicios.listarExamenes,
        consultarRevision: servicios.consultarRevision,
        guardarRevision: servicios.guardarRevision,
        urlDelRecorte: servicios.urlDelRecorte,
        encabezadosDelRecorte: servicios.encabezadosDelRecorte,
        nombresDeHojas: _nombresDeHojas,
        examenPedido: _examenParaRevisar,
        alMostrarse: _revisionALaVista,
        clavesCambiadas: _clavesCambiadas,
        alGuardar: () => _revisionesGuardadas.value++,
      ),
      PantallaPauta(
        proponerDistractores: servicios.proponerDistractores,
        estadoApi: _estadoApi,
        listarExamenes: servicios.listarExamenes,
        consultarClave: servicios.consultarClave,
        guardarClave: servicios.guardarClave,
        habilitarClave: servicios.habilitarClave,
        crearExamen: servicios.crearExamen,
        alCambiarLaClave: () => _clavesCambiadas.value++,
      ),
    ];

    // `StackFit.expand`: cada pantalla recibe el área completa, así que su desplazamiento ocupa
    // el alto entero y una pantalla corta queda arriba, no centrada en el espacio que sobra.
    //
    // La llave global lo mantiene vivo cuando cambia de lugar: en una ventana ancha va dentro de
    // una fila junto al riel, y en una angosta va directo en el cuerpo. Sin ella, cruzar ese ancho
    // creaba las pantallas de nuevo y el docente perdía el examen y las fotos que ya había elegido.
    final contenido = IndexedStack(
      key: _claveContenido,
      index: _seccion.index,
      sizing: StackFit.expand,
      children: pantallas,
    );
    final ancha = MediaQuery.sizeOf(context).width >= QAnchos.riel;

    return Scaffold(
      appBar: BarraSuperior(
        estado: _estadoApi,
        alReintentar: _comprobarApi,
        correo: widget.correo,
        alSalir: widget.alSalir,
      ),
      body: ancha
          ? Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                NavigationRail(
                  selectedIndex: _seccion.index,
                  onDestinationSelected: _ir,
                  labelType: NavigationRailLabelType.all,
                  minWidth: 88,
                  groupAlignment: -1,
                  destinations: [
                    for (final s in Seccion.values)
                      NavigationRailDestination(
                        icon: Icon(s.icono),
                        selectedIcon: Icon(s.iconoActivo),
                        label: Text(s.etiqueta),
                      ),
                  ],
                ),
                const VerticalDivider(width: 1),
                Expanded(child: contenido),
              ],
            )
          : contenido,
      bottomNavigationBar: ancha
          ? null
          : DecoratedBox(
              decoration: const BoxDecoration(
                border: Border(top: BorderSide(color: QColores.borde)),
              ),
              child: NavigationBar(
                selectedIndex: _seccion.index,
                onDestinationSelected: _ir,
                destinations: [
                  for (final s in Seccion.values)
                    NavigationDestination(
                      icon: Icon(s.icono),
                      selectedIcon: Icon(s.iconoActivo),
                      label: s.etiqueta,
                    ),
                ],
              ),
            ),
    );
  }
}
