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
  const MarcoApp({super.key, required this.servicios, this.seccionInicial = Seccion.panel});

  final ServiciosApp servicios;
  final Seccion seccionInicial;

  @override
  State<MarcoApp> createState() => _MarcoAppState();
}

class _MarcoAppState extends State<MarcoApp> {
  final _estadoApi = ValueNotifier<EstadoApi>(EstadoApi.verificando);
  late Seccion _seccion = widget.seccionInicial;

  @override
  void initState() {
    super.initState();
    _comprobarApi();
  }

  @override
  void dispose() {
    _estadoApi.dispose();
    super.dispose();
  }

  Future<void> _comprobarApi() async {
    _estadoApi.value = EstadoApi.verificando;
    final conectada = await widget.servicios.verificarSalud();
    if (!mounted) return;
    _estadoApi.value = conectada ? EstadoApi.conectada : EstadoApi.sinConexion;
  }

  void _ir(int indice) => setState(() => _seccion = Seccion.values[indice]);

  @override
  Widget build(BuildContext context) {
    final servicios = widget.servicios;
    final pantallas = [
      const PantallaPanel(),
      PantallaCarga(
        seleccionarArchivos: servicios.seleccionarArchivos,
        subirHojas: servicios.subirHojas,
        estadoApi: _estadoApi,
      ),
      const PantallaRevision(),
      PantallaPauta(
        proponerDistractores: servicios.proponerDistractores,
        estadoApi: _estadoApi,
      ),
    ];

    // `StackFit.expand`: cada pantalla recibe el área completa, así que su desplazamiento ocupa
    // el alto entero y una pantalla corta queda arriba, no centrada en el espacio que sobra.
    final contenido = IndexedStack(
      index: _seccion.index,
      sizing: StackFit.expand,
      children: pantallas,
    );
    final ancha = MediaQuery.sizeOf(context).width >= QAnchos.riel;

    return Scaffold(
      appBar: BarraSuperior(estado: _estadoApi, alReintentar: _comprobarApi),
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
