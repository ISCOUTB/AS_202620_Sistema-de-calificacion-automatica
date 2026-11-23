import 'package:flutter/material.dart';

import '../../../common/tema/tokens.dart';
import '../../../common/widgets/q_encabezado_pantalla.dart';
import '../../../common/widgets/q_estado_vacio.dart';
import '../../../common/widgets/q_pagina.dart';
import '../../carga/data/servicio_examenes.dart';
import '../../carga/data/servicio_resultados.dart' show ExcepcionDeConsulta;
import '../data/modelos_panel.dart';
import 'widgets/aciertos_por_pregunta.dart';
import 'widgets/distribucion_notas.dart';
import 'widgets/marcas_del_examen.dart';
import 'widgets/metricas_examen.dart';
import 'widgets/selector_examen.dart';

/// Panel del curso (RF-05): cómo le fue al grupo en el examen elegido, con las hojas que el
/// sistema leyó y lo que resolvió el docente (ADR-0028). Antes mostraba datos de ejemplo fijos.
///
/// Solo ofrece los exámenes del docente de la sesión: la API no devuelve los de nadie más. Las
/// cifras se vuelven a pedir al cambiar de examen, al volver a la sección, al guardar una revisión
/// y con el botón de actualizar, porque el worker sigue leyendo hojas mientras el panel está abierto.
class PantallaPanel extends StatefulWidget {
  const PantallaPanel({
    super.key,
    this.listarExamenes,
    this.consultarPanel,
    this.clavesCambiadas,
    this.revisionesGuardadas,
    this.alMostrarse,
  });

  final Future<List<ExamenConClave>> Function()? listarExamenes;
  final Future<PanelDelExamen> Function(String examenId)? consultarPanel;

  /// Avisa que se guardó o habilitó una clave: puede haber un examen nuevo en la lista.
  final Listenable? clavesCambiadas;

  /// Avisa que se guardó una revisión: las notas del examen pudieron cambiar.
  final Listenable? revisionesGuardadas;

  /// Avisa que el panel volvió a la vista.
  final Listenable? alMostrarse;

  @override
  State<PantallaPanel> createState() => _PantallaPanelState();
}

class _PantallaPanelState extends State<PantallaPanel> {
  /// Ancho útil desde el que las tarjetas van de a dos. Es [QAnchos.dosColumnas] medido sin los
  /// márgenes de la página (24 px por lado a ese ancho), porque aquí se mide el espacio que deja
  /// [QPagina], no la pantalla entera.
  static const _anchoDosColumnas = QAnchos.dosColumnas - 2 * QEspacios.lg;

  List<ExamenConClave>? _examenes;
  bool _cargandoExamenes = false;
  String? _errorExamenes;

  ExamenConClave? _actual;
  PanelDelExamen? _panel;
  bool _cargandoPanel = false;
  String? _errorPanel;

  bool get _conServicios => widget.listarExamenes != null && widget.consultarPanel != null;

  @override
  void initState() {
    super.initState();
    widget.clavesCambiadas?.addListener(_pedirExamenes);
    widget.revisionesGuardadas?.addListener(_pedirPanel);
    widget.alMostrarse?.addListener(_pedirPanel);
    if (_conServicios) _pedirExamenes();
  }

  @override
  void dispose() {
    widget.clavesCambiadas?.removeListener(_pedirExamenes);
    widget.revisionesGuardadas?.removeListener(_pedirPanel);
    widget.alMostrarse?.removeListener(_pedirPanel);
    super.dispose();
  }

  /// Los exámenes más recientes primero: los de identificador numérico (ADR-0028), del mayor al
  /// menor, y después los anteriores.
  static List<ExamenConClave> _ordenados(List<ExamenConClave> lista) {
    final numericos = [for (final e in lista) if (int.tryParse(e.examenId) != null) e]
      ..sort((a, b) => b.examenId.compareTo(a.examenId));
    final anteriores = [for (final e in lista) if (int.tryParse(e.examenId) == null) e];
    return [...numericos, ...anteriores];
  }

  Future<void> _pedirExamenes() async {
    if (!_conServicios) return;
    setState(() {
      _cargandoExamenes = true;
      _errorExamenes = null;
    });
    try {
      final lista = _ordenados(await widget.listarExamenes!());
      if (!mounted) return;
      final anterior = _actual;
      ExamenConClave? actual;
      for (final examen in lista) {
        if (examen.examenId == anterior?.examenId) actual = examen;
      }
      actual ??= lista.isEmpty ? null : lista.first;
      setState(() {
        _examenes = lista;
        _actual = actual;
      });
      _pedirPanel();
    } on ExcepcionDeConsulta catch (error) {
      if (mounted) setState(() => _errorExamenes = error.mensaje);
    } catch (_) {
      if (mounted) setState(() => _errorExamenes = 'No se pudo cargar la lista de exámenes.');
    } finally {
      if (mounted) setState(() => _cargandoExamenes = false);
    }
  }

  Future<void> _pedirPanel() async {
    final examen = _actual;
    if (!mounted || examen == null || widget.consultarPanel == null) return;
    setState(() {
      _cargandoPanel = true;
      _errorPanel = null;
    });
    try {
      final panel = await widget.consultarPanel!(examen.examenId);
      // Si mientras tanto se eligió otro examen, esta respuesta ya no sirve.
      if (!mounted || _actual?.examenId != examen.examenId) return;
      setState(() => _panel = panel);
    } on ExcepcionDeConsulta catch (error) {
      if (mounted && _actual?.examenId == examen.examenId) {
        setState(() => _errorPanel = error.mensaje);
      }
    } catch (_) {
      if (mounted && _actual?.examenId == examen.examenId) {
        setState(() => _errorPanel = 'No se pudieron cargar las cifras del examen.');
      }
    } finally {
      if (mounted && _actual?.examenId == examen.examenId) {
        setState(() => _cargandoPanel = false);
      }
    }
  }

  void _elegir(ExamenConClave examen) {
    if (examen.examenId == _actual?.examenId) return;
    setState(() {
      _actual = examen;
      _panel = null;
    });
    _pedirPanel();
  }

  @override
  Widget build(BuildContext context) {
    final sinMovimiento = MediaQuery.disableAnimationsOf(context);
    final examenes = _examenes;
    final actual = _actual;
    final panel = _panel;

    return QPagina(
      children: [
        QEncabezadoPantalla(
          titulo: 'Panel del curso',
          descripcion: 'Cómo le fue al grupo en cada uno de sus exámenes',
          extremo: _conServicios && actual != null
              ? IconButton(
                  tooltip: 'Actualizar las cifras',
                  onPressed: _cargandoPanel ? null : _pedirPanel,
                  icon: const Icon(Icons.refresh_outlined),
                )
              : null,
        ),
        const SizedBox(height: QEspacios.lg),
        if (!_conServicios)
          const QEstadoVacio(
            icono: Icons.cloud_off_outlined,
            titulo: 'El panel necesita el servidor',
            texto: 'Sin conexión con la API no hay exámenes que mostrar.',
          )
        else if (examenes == null && _cargandoExamenes)
          const Center(
            child: Padding(
              padding: EdgeInsets.all(QEspacios.xl),
              child: CircularProgressIndicator(),
            ),
          )
        else if (_errorExamenes != null && examenes == null)
          QEstadoVacio(
            icono: Icons.error_outline,
            colorIcono: QColores.errorTexto,
            titulo: 'No se pudieron cargar sus exámenes',
            texto: _errorExamenes!,
            accion: OutlinedButton(
              onPressed: _pedirExamenes,
              child: const Text('Volver a intentar'),
            ),
          )
        else if (examenes == null || examenes.isEmpty || actual == null)
          const QEstadoVacio(
            icono: Icons.assignment_outlined,
            titulo: 'Todavía no tiene exámenes',
            texto: 'Cree uno en Pauta & IA: escriba su nombre, guarde la clave y habilítela. '
                'Cuando suba las hojas, aquí verá cómo le fue al grupo.',
          )
        else ...[
          SelectorExamen(examenes: examenes, actual: actual, alElegir: _elegir),
          const SizedBox(height: QEspacios.lg),
          if (panel == null && _cargandoPanel)
            const Center(
              child: Padding(
                padding: EdgeInsets.all(QEspacios.xl),
                child: CircularProgressIndicator(),
              ),
            )
          else if (panel == null && _errorPanel != null)
            QEstadoVacio(
              icono: Icons.error_outline,
              colorIcono: QColores.errorTexto,
              titulo: 'No se pudieron cargar las cifras',
              texto: _errorPanel!,
              accion: OutlinedButton(
                onPressed: _pedirPanel,
                child: const Text('Volver a intentar'),
              ),
            )
          else if (panel != null)
            LayoutBuilder(
              builder: (context, restricciones) {
                final columnas = restricciones.maxWidth >= _anchoDosColumnas ? 2 : 1;
                // Al cambiar de examen las cifras se funden en vez de saltar, para que se note
                // que cambió el conjunto de datos y no solo un número. Sin animación si el
                // sistema pide reducir el movimiento.
                return AnimatedSwitcher(
                  duration: sinMovimiento ? Duration.zero : QDuraciones.media,
                  switchInCurve: Curves.easeOut,
                  switchOutCurve: Curves.easeIn,
                  layoutBuilder: (actual, anteriores) => Stack(
                    alignment: AlignmentDirectional.topStart,
                    children: [...anteriores, if (actual != null) actual],
                  ),
                  child: _ContenidoExamen(
                    key: ValueKey(panel.examenId),
                    panel: panel,
                    columnas: columnas,
                  ),
                );
              },
            ),
        ],
      ],
    );
  }
}

/// Lo que depende del examen elegido: métricas, marcas, notas y aciertos por pregunta.
class _ContenidoExamen extends StatelessWidget {
  const _ContenidoExamen({super.key, required this.panel, required this.columnas});

  final PanelDelExamen panel;
  final int columnas;

  @override
  Widget build(BuildContext context) {
    final resumen = panel.resumen;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        MetricasExamen(resumen: resumen, columnas: columnas),
        const SizedBox(height: QEspacios.xl),
        MarcasDelExamenVista(marcas: panel.marcas, hojasConNota: resumen.hojasConNota),
        const SizedBox(height: QEspacios.xl),
        DistribucionNotas(
          notas: panel.notas,
          notaAprobatoria: resumen.notaAprobatoria,
          media: resumen.promedio,
          desviacion: resumen.desviacion,
        ),
        const SizedBox(height: QEspacios.xl),
        AciertosPorPregunta(preguntas: panel.preguntas),
      ],
    );
  }
}
