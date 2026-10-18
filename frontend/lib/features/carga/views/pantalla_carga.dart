import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../../common/api/servicio_salud.dart';
import '../../../common/tema/tokens.dart';
import '../../../common/widgets/q_chip_estado.dart';
import '../../../common/widgets/q_encabezado_pantalla.dart';
import '../../../common/widgets/q_estado_vacio.dart';
import '../../../common/widgets/q_pagina.dart';
import '../../../common/widgets/q_tarjeta.dart';
import '../data/servicio_carga.dart';
import 'widgets/aviso_carga.dart';
import 'widgets/formato_carga.dart';
import 'widgets/reporte_recepcion.dart';
import 'widgets/tarjeta_examen.dart';
import 'widgets/zona_seleccion.dart';

/// Pantalla de carga de hojas escaneadas: el aspecto A-01 (RF-01) del lado del docente y la cara
/// visible del escenario EC-07.
///
/// No conoce el navegador ni HTTP. Recibe inyectadas las dos operaciones (elegir archivos y
/// subirlos) y el estado de la API que vigila el marco, de modo que las pruebas de widget la
/// ejercitan entera sin diálogo de archivos y sin backend.
class PantallaCarga extends StatefulWidget {
  const PantallaCarga({
    super.key,
    required this.seleccionarArchivos,
    required this.subirHojas,
    required this.estadoApi,
  });

  final Future<List<ArchivoSeleccionado>> Function() seleccionarArchivos;
  final Future<ResultadoCarga> Function(String, List<ArchivoSeleccionado>) subirHojas;
  final ValueListenable<EstadoApi> estadoApi;

  @override
  State<PantallaCarga> createState() => _PantallaCargaState();
}

/// Una carga que no terminó en un reporte. Es distinta de un rechazo: un rechazo es una respuesta
/// del sistema sobre un archivo; esto es la falta de respuesta sobre el lote entero.
class _Falla {
  const _Falla({required this.titulo, required this.texto, required this.detalle});

  final String titulo;
  final String texto;
  final String detalle;
}

class _PantallaCargaState extends State<PantallaCarga> {
  final _examen = TextEditingController();

  /// Marca la cabecera del reporte, para llevarla a la vista cuando llega.
  final _claveCabecera = GlobalKey();

  List<ArchivoSeleccionado> _seleccionados = const [];
  bool _subiendo = false;
  _Falla? _falla;

  ResultadoCarga? _resultado;
  String _examenDelReporte = '';
  int _enviadosDelReporte = 0;

  /// Cuenta los reportes recibidos. Sirve de llave para que cada reporte nuevo entre con su
  /// animación, aunque el anterior tuviera el mismo contenido.
  int _reportes = 0;

  @override
  void dispose() {
    _examen.dispose();
    super.dispose();
  }

  String get _examenId => _examen.text.trim();

  bool _puedeSubir(EstadoApi api) =>
      !_subiendo &&
      api != EstadoApi.sinConexion &&
      _seleccionados.isNotEmpty &&
      _examenId.isNotEmpty;

  /// Dos archivos con el mismo nombre y el mismo tamaño se toman por el mismo: es lo que pasa
  /// cuando el docente vuelve a elegir una hoja que ya estaba en el lote.
  static bool _mismoArchivo(ArchivoSeleccionado a, ArchivoSeleccionado b) =>
      a.nombre == b.nombre && a.contenido.length == b.contenido.length;

  /// Suma lo elegido a la selección en vez de reemplazarla, para que el docente pueda armar el
  /// lote desde varias carpetas. Lo repetido no se agrega dos veces, porque el backend no detecta
  /// duplicados y la misma hoja se calificaría dos veces; y se avisa, para que no parezca que el
  /// archivo se perdió.
  Future<void> _elegir() async {
    final List<ArchivoSeleccionado> elegidos;
    try {
      elegidos = await widget.seleccionarArchivos();
    } catch (_) {
      if (mounted) _avisar('No se pudieron leer los archivos elegidos. Vuelva a intentarlo.');
      return;
    }
    if (!mounted || elegidos.isEmpty) return;

    final nuevos = <ArchivoSeleccionado>[];
    var repetidos = 0;
    for (final archivo in elegidos) {
      final yaEsta = [..._seleccionados, ...nuevos].any((a) => _mismoArchivo(a, archivo));
      if (yaEsta) {
        repetidos++;
      } else {
        nuevos.add(archivo);
      }
    }

    setState(() {
      _seleccionados = [..._seleccionados, ...nuevos];
      _falla = null;
    });
    if (repetidos > 0) {
      _avisar(repetidos == 1
          ? 'Un archivo ya estaba en la selección y no se agregó otra vez.'
          : '$repetidos archivos ya estaban en la selección y no se agregaron otra vez.');
    }
  }

  void _avisar(String texto) =>
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(SnackBar(content: Text(texto)));

  void _quitar(int indice) =>
      setState(() => _seleccionados = [..._seleccionados]..removeAt(indice));

  void _quitarTodos() => setState(() => _seleccionados = const []);

  Future<void> _subir() async {
    final examen = _examenId;
    final lote = _seleccionados;
    setState(() {
      _subiendo = true;
      _falla = null;
      _resultado = null;
    });

    try {
      final resultado = await widget.subirHojas(examen, lote);
      if (!mounted) return;
      setState(() {
        _resultado = resultado;
        _examenDelReporte = examen;
        _enviadosDelReporte = lote.length;
        _reportes++;
        // Lo procesado sale de la selección: dejarlo invitaría a subir otra vez las mismas
        // hojas, y el sistema no tiene forma de detectar un duplicado. Los rechazados también
        // salen; el reporte los nombra con su motivo, y hay que corregirlos antes de reenviarlos.
        _seleccionados = const [];
      });
      _llevarReporteALaVista();
    } on ExcepcionDeCarga catch (error) {
      if (!mounted) return;
      setState(() => _falla = _Falla(
            titulo: 'No se pudo completar la carga',
            texto: error.mensaje,
            detalle: 'Sus archivos siguen seleccionados para que pueda reintentar.',
          ));
    } catch (_) {
      // Una respuesta que no se pudo leer no es lo mismo que una que no llegó: el lote pudo
      // haber entrado. Por eso el aviso no invita a reintentar sin más.
      if (!mounted) return;
      setState(() => _falla = const _Falla(
            titulo: 'Sin confirmación de la API',
            texto: 'La respuesta de la API no se pudo leer, así que no se sabe qué hojas '
                'entraron.',
            detalle: 'Sus archivos siguen seleccionados. Si vuelve a subirlos, alguna hoja '
                'podría quedar repetida.',
          ));
    } finally {
      if (mounted) setState(() => _subiendo = false);
    }
  }

  /// En una columna, el reporte aparece debajo del botón y casi siempre fuera de la vista: sin
  /// este desplazamiento el docente no sabría que llegó. Se mueve lo justo para que la cabecera
  /// asome, y nada si ya está a la vista.
  void _llevarReporteALaVista() {
    final animar = !MediaQuery.of(context).disableAnimations;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final destino = _claveCabecera.currentContext;
      if (!mounted || destino == null) return;
      Scrollable.ensureVisible(
        destino,
        duration: animar ? QDuraciones.media : Duration.zero,
        curve: Curves.easeOutCubic,
        alignmentPolicy: ScrollPositionAlignmentPolicy.keepVisibleAtEnd,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<EstadoApi>(
      valueListenable: widget.estadoApi,
      builder: (context, estadoApi, _) => QPagina(
        children: [
          const QEncabezadoPantalla(
            etiqueta: 'Carga de hojas',
            iconoEtiqueta: Icons.document_scanner_outlined,
            titulo: 'Cargar hojas escaneadas',
            descripcion: 'Suba los escaneos de un examen en JPG, PNG o PDF. Cada archivo '
                'recibe su confirmación o el motivo del rechazo.',
          ),
          const SizedBox(height: QEspacios.lg),
          LayoutBuilder(
            builder: (context, restricciones) {
              final ancho = restricciones.maxWidth;
              // En dos columnas el reporte queda junto al botón que lo produce, y el docente lo
              // ve llegar sin desplazarse. En un teléfono va debajo, en el orden de los pasos.
              final dosColumnas = ancho >= QAnchos.dosColumnas;
              final anchoColumna = dosColumnas ? (ancho - QEspacios.lg) / 2 : ancho;
              final preparacion = _preparacion(estadoApi, anchoColumna);
              final reporte = _zonaReporte(anchoColumna);

              if (!dosColumnas) {
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [preparacion, const SizedBox(height: QEspacios.xl), reporte],
                );
              }
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(child: preparacion),
                  const SizedBox(width: QEspacios.lg),
                  Expanded(child: reporte),
                ],
              );
            },
          ),
        ],
      ),
    );
  }

  /// Los tres pasos del docente: el examen, los archivos y la subida.
  Widget _preparacion(EstadoApi estadoApi, double anchoColumna) {
    final compacta = anchoColumna < 480;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        TarjetaExamen(
          controlador: _examen,
          habilitada: !_subiendo,
          compacta: compacta,
          alCambiar: (_) => setState(() {}),
        ),
        const SizedBox(height: QEspacios.md),
        ZonaSeleccion(
          archivos: _seleccionados,
          habilitada: !_subiendo,
          compacta: compacta,
          alSeleccionar: _elegir,
          alQuitar: _quitar,
          alQuitarTodos: _quitarTodos,
        ),
        const SizedBox(height: QEspacios.lg),
        _accion(estadoApi, enLinea: !compacta),
      ],
    );
  }

  Widget _accion(EstadoApi estadoApi, {required bool enLinea}) {
    final textos = Theme.of(context).textTheme;
    final indicacion = _indicacion(estadoApi);
    final textoIndicacion = indicacion == null
        ? null
        : Text(indicacion, style: textos.bodyMedium?.copyWith(color: QColores.textoSuave));
    final boton = FilledButton.icon(
      onPressed: _puedeSubir(estadoApi) ? _subir : null,
      icon: Icon(_subiendo ? Icons.hourglass_top_outlined : Icons.upload_outlined),
      label: Text(_subiendo ? 'Subiendo…' : 'Subir al sistema'),
    );
    final falla = _falla;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (estadoApi == EstadoApi.sinConexion) ...[
          const AvisoCarga(
            tono: QTono.advertencia,
            icono: Icons.cloud_off_outlined,
            titulo: 'Sin conexión con la API',
            texto: 'No se puede subir mientras la API no responda.',
            detalle: 'Su selección se conserva. Cuando la barra superior indique que la API '
                'está conectada, podrá subir el lote.',
          ),
          const SizedBox(height: QEspacios.md),
        ],
        if (enLinea)
          Row(
            children: [
              Expanded(child: textoIndicacion ?? const SizedBox.shrink()),
              const SizedBox(width: QEspacios.md),
              boton,
            ],
          )
        else ...[
          if (textoIndicacion != null) ...[
            textoIndicacion,
            const SizedBox(height: QEspacios.sm + 4),
          ],
          boton,
        ],
        if (_subiendo) ...[
          const SizedBox(height: QEspacios.sm + 4),
          const LinearProgressIndicator(semanticsLabel: 'Subiendo los archivos'),
        ],
        if (falla != null) ...[
          const SizedBox(height: QEspacios.md),
          AvisoCarga(
            tono: QTono.error,
            icono: Icons.error_outlined,
            titulo: falla.titulo,
            texto: falla.texto,
            detalle: falla.detalle,
          ),
        ],
      ],
    );
  }

  /// Qué falta para poder subir, o qué se va a subir. Un botón deshabilitado sin explicación
  /// deja al docente adivinando qué hizo mal.
  String? _indicacion(EstadoApi estadoApi) {
    final archivos = contar(_seleccionados.length, 'archivo', 'archivos');
    if (_subiendo) return 'Enviando $archivos al examen $_examenId…';
    // Sin conexión ya lo explica el aviso de arriba.
    if (estadoApi == EstadoApi.sinConexion) return null;
    final faltaExamen = _examenId.isEmpty;
    final faltanArchivos = _seleccionados.isEmpty;
    if (faltaExamen && faltanArchivos) {
      return 'Escriba el identificador del examen y seleccione los archivos para subirlos.';
    }
    if (faltaExamen) return 'Escriba el identificador del examen para subir los archivos.';
    if (faltanArchivos) return 'Seleccione al menos un archivo para subirlo.';
    return 'Se enviarán $archivos al examen $_examenId.';
  }

  /// El reporte, o lo que ocupa su lugar mientras no hay uno, para que la columna no quede vacía
  /// ni haga pensar que algo falló.
  Widget _zonaReporte(double anchoColumna) {
    final resultado = _resultado;
    if (resultado == null) {
      return QTarjeta(
        padding: const EdgeInsets.all(QEspacios.sm),
        child: _subiendo
            ? const QEstadoVacio(
                icono: Icons.hourglass_top_outlined,
                titulo: 'Esperando la confirmación',
                texto: 'La API responde con el resultado de cada archivo en cuanto termina de '
                    'recibir el lote.',
              )
            : const QEstadoVacio(
                icono: Icons.fact_check_outlined,
                titulo: 'Todavía no hay un reporte',
                texto: 'Cuando suba un lote, aquí verá cuántos archivos se procesaron, cuáles '
                    'quedaron recibidos y el motivo de cada rechazo.',
              ),
      );
    }

    // Aparece en 220 ms, con un desplazamiento corto hacia arriba: lo bastante para que el ojo
    // note que llegó algo nuevo, y nada si el sistema pide no animar.
    final animar = !MediaQuery.of(context).disableAnimations;
    return TweenAnimationBuilder<double>(
      key: ValueKey(_reportes),
      tween: Tween(begin: 0, end: 1),
      duration: animar ? QDuraciones.media : Duration.zero,
      curve: Curves.easeOutCubic,
      builder: (context, avance, hijo) => Opacity(
        opacity: avance,
        child: Transform.translate(offset: Offset(0, (1 - avance) * 8), child: hijo),
      ),
      child: ReporteRecepcion(
        resultado: resultado,
        examenId: _examenDelReporte,
        enviados: _enviadosDelReporte,
        ancho: anchoColumna,
        claveCabecera: _claveCabecera,
      ),
    );
  }
}
