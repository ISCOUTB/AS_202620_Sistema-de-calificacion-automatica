import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';

import '../../../common/api/servicio_salud.dart';
import '../../../common/tema/tokens.dart';
import '../../../common/widgets/q_chip_estado.dart';
import '../../../common/widgets/q_encabezado_pantalla.dart';
import '../../../common/widgets/q_estado_vacio.dart';
import '../../../common/widgets/q_pagina.dart';
import '../../../common/widgets/q_tarjeta.dart';
import '../data/preparacion_de_hojas.dart';
import '../data/servicio_carga.dart';
import '../data/servicio_examenes.dart';
import '../data/servicio_resultados.dart';
import 'widgets/aviso_carga.dart';
import 'widgets/como_tomar_las_fotos.dart';
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
    this.consultarResultados,
    this.listarExamenes,
    this.alRecibirHojas,
    this.alRevisar,
    this.revisionesGuardadas,
    this.intervaloDeConsulta = const Duration(seconds: 3),
  });

  final Future<List<ArchivoSeleccionado>> Function({
    void Function(int hechas, int total)? alAvanzar,
  }) seleccionarArchivos;
  final Future<ResultadoCarga> Function(String, List<ArchivoSeleccionado>) subirHojas;
  final ValueListenable<EstadoApi> estadoApi;

  /// Cómo quedó cada hoja leída (A-02 y A-03). Sin él, el reporte se queda en la recepción.
  final Future<ResultadosDelExamen> Function(String examenId)? consultarResultados;

  /// Los exámenes con clave, para elegir el de la carga en una lista. Sin él, se escribe.
  final Future<List<ExamenConClave>> Function()? listarExamenes;

  /// Recibe el nombre de archivo de cada hoja aceptada, por `hoja_id`: la revisión los muestra.
  final void Function(Map<String, String> nombres)? alRecibirHojas;

  /// Lleva a la revisión del examen del reporte.
  final void Function(String examenId)? alRevisar;

  /// Cambia cada vez que el docente guarda una revisión: el reporte vuelve a pedir las notas.
  final ValueListenable<int>? revisionesGuardadas;

  /// Cada cuánto se pregunta, después de subir, si ya se leyeron las hojas. Una hoja tarda unos
  /// dos segundos en el servidor (EC-03).
  final Duration intervaloDeConsulta;

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

/// Lo que se le dice al docente cuando algunas hojas pudieron entrar sin reporte: el sistema no
/// detecta una hoja subida dos veces (R-24), así que reintentar sin revisar las duplicaría.
const _detalleSiPudieronEntrar =
    'Sus archivos siguen seleccionados. Si vuelve a subirlos, alguna hoja podría quedar repetida.';

class _PantallaCargaState extends State<PantallaCarga> {
  final _examen = TextEditingController();

  /// Marca la cabecera del reporte, para llevarla a la vista cuando llega.
  final _claveCabecera = GlobalKey();

  List<ArchivoSeleccionado> _seleccionados = const [];
  bool _subiendo = false;

  /// Cuántas fotos van preparadas y cuántas son, mientras el navegador las pasa a gris y las
  /// reduce. Con 200 fotos tarda, y sin avance parecería colgado.
  (int, int)? _preparando;
  _Falla? _falla;

  ResultadoCarga? _resultado;
  String _examenDelReporte = '';
  int _enviadosDelReporte = 0;

  /// Cuenta los reportes recibidos. Sirve de llave para que cada reporte nuevo entre con su
  /// animación, aunque el anterior tuviera el mismo contenido.
  int _reportes = 0;

  /// Lo que ya se leyó de las hojas del último reporte, por `hoja_id`. Se pregunta cada
  /// [PantallaCarga.intervaloDeConsulta] hasta que estén todas, o hasta [_esperaMaxima].
  Map<String, ResultadoDeHoja> _lecturas = const {};
  Timer? _consulta;
  bool _consultando = false;
  DateTime? _consultarHasta;

  /// Doscientas hojas tardan unos cuatro minutos en el servidor (EC-04). Después de este tiempo
  /// se deja de preguntar, y el docente puede volver a consultar con un botón.
  static const _esperaMaxima = Duration(minutes: 15);

  /// Los exámenes con clave. Nula mientras no haya lista: sin el servicio, mientras se pide o si
  /// no se pudo cargar.
  List<ExamenConClave>? _examenes;
  bool _cargandoExamenes = false;
  bool _fallaExamenes = false;

  @override
  void initState() {
    super.initState();
    _examen.addListener(_alCambiarElExamen);
    widget.estadoApi.addListener(_alCambiarLaConexion);
    widget.revisionesGuardadas?.addListener(_consultarUnaVez);
    if (widget.listarExamenes != null) {
      _cargandoExamenes = true;
      _pedirExamenes();
    }
  }

  @override
  void dispose() {
    _consulta?.cancel();
    widget.estadoApi.removeListener(_alCambiarLaConexion);
    widget.revisionesGuardadas?.removeListener(_consultarUnaVez);
    _examen.dispose();
    super.dispose();
  }

  /// El desplegable cambia el texto al elegir y al filtrar, sin avisar por otra vía. Si el cambio
  /// llega mientras se construye la pantalla, se redibuja en el cuadro siguiente.
  void _alCambiarElExamen() {
    if (!mounted) return;
    if (SchedulerBinding.instance.schedulerPhase == SchedulerPhase.persistentCallbacks) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) setState(() {});
      });
    } else {
      setState(() {});
    }
  }

  Future<void> _pedirExamenes() async {
    try {
      final examenes = await widget.listarExamenes!();
      if (!mounted) return;
      setState(() {
        _examenes = examenes;
        _fallaExamenes = false;
      });
    } catch (_) {
      if (mounted) setState(() => _fallaExamenes = true);
    } finally {
      if (mounted) setState(() => _cargandoExamenes = false);
    }
  }

  void _volverAPedirExamenes() {
    if (widget.listarExamenes == null || _cargandoExamenes) return;
    setState(() => _cargandoExamenes = true);
    _pedirExamenes();
  }

  /// Si la lista falló porque la API todavía no respondía, se vuelve a pedir cuando conecta.
  void _alCambiarLaConexion() {
    if (_fallaExamenes && widget.estadoApi.value == EstadoApi.conectada) _volverAPedirExamenes();
  }

  /// Las hojas que se van a leer: las que llegaron a la cola. Una en espera no entra a la lectura,
  /// y esperarla dejaría la pantalla preguntando quince minutos por nada.
  Set<String> get _hojasEsperadas => {
        for (final hoja in _resultado?.aceptadas ?? const <HojaAceptada>[])
          if (hoja.hojaId != null && hoja.estado == EstadoHoja.encolada) hoja.hojaId!,
      };

  bool get _faltanLecturas => _hojasEsperadas.any((id) => !_lecturas.containsKey(id));

  /// Empieza a preguntar por los resultados del último reporte.
  void _consultarResultados() {
    _consulta?.cancel();
    if (widget.consultarResultados == null || _hojasEsperadas.isEmpty) return;
    _consultarHasta = DateTime.now().add(_esperaMaxima);
    _consultarUnaVez();
    _consulta = Timer.periodic(widget.intervaloDeConsulta, (_) => _consultarUnaVez());
    setState(() {});
  }

  Future<void> _consultarUnaVez() async {
    final consultar = widget.consultarResultados;
    if (consultar == null || _consultando) return;
    _consultando = true;
    final examen = _examenDelReporte;
    final esperadas = _hojasEsperadas;
    try {
      final resultados = await consultar(examen);
      if (!mounted || examen != _examenDelReporte) return;
      setState(() => _lecturas = {
            for (final id in esperadas)
              if (resultados.porHoja[id] case final lectura?) id: lectura,
          });
    } catch (_) {
      // Una consulta que falla se repite en la vuelta siguiente: no hay nada que hacer aquí.
    } finally {
      _consultando = false;
      final vencida = _consultarHasta != null && DateTime.now().isAfter(_consultarHasta!);
      if (mounted && (!_faltanLecturas || vencida)) {
        _consulta?.cancel();
        setState(() => _consulta = null);
      }
    }
  }

  /// El examen al que van las hojas. Con lista, solo uno de ella, con su nombre exacto.
  String get _examenId {
    final lista = _examenes;
    if (lista == null) return _examen.text.trim();
    return examenElegido(_examen.text, lista)?.examenId ?? '';
  }

  bool _puedeSubir(EstadoApi api) =>
      !_subiendo &&
      _preparando == null &&
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
      elegidos = await widget.seleccionarArchivos(
        alAvanzar: (hechas, total) {
          if (mounted) setState(() => _preparando = (hechas, total));
        },
      );
    } catch (_) {
      if (mounted) _avisar('No se pudieron leer los archivos elegidos. Vuelva a intentarlo.');
      return;
    } finally {
      if (mounted) setState(() => _preparando = null);
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
    _consulta?.cancel();
    setState(() {
      _subiendo = true;
      _falla = null;
      _resultado = null;
      _lecturas = const {};
      _consulta = null;
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
      widget.alRecibirHojas?.call({
        for (final hoja in resultado.aceptadas)
          if (hoja.hojaId != null) hoja.hojaId!: hoja.nombreArchivo,
      });
      _consultarResultados();
    } on ExcepcionDeCarga catch (error) {
      if (!mounted) return;
      // Si algunas hojas pudieron entrar, invitar a reintentar las duplicaría: el detalle es el
      // mismo que el de una respuesta ilegible.
      setState(() => _falla = _Falla(
            titulo: 'No se pudo completar la carga',
            texto: error.mensaje,
            detalle: error.pudieronEntrar
                ? _detalleSiPudieronEntrar
                : 'Sus archivos siguen seleccionados para que pueda reintentar.',
          ));
    } catch (_) {
      // Una respuesta que no se pudo leer no es lo mismo que una que no llegó: el lote pudo
      // haber entrado. Por eso el aviso no invita a reintentar sin más.
      if (!mounted) return;
      setState(() => _falla = const _Falla(
            titulo: 'Sin confirmación del servidor',
            texto: 'La respuesta del servidor no se pudo leer, así que no se sabe qué hojas '
                'entraron.',
            detalle: _detalleSiPudieronEntrar,
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
            titulo: 'Cargar las hojas del examen',
            descripcion: 'Suba las fotos o los escaneos de un examen en JPG o PNG.',
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
        ComoTomarLasFotos(compacta: compacta),
        const SizedBox(height: QEspacios.md),
        TarjetaExamen(
          controlador: _examen,
          habilitada: !_subiendo,
          compacta: compacta,
          examenes: _examenes,
          cargando: _cargandoExamenes,
          alReintentar: _fallaExamenes ? _volverAPedirExamenes : null,
        ),
        const SizedBox(height: QEspacios.md),
        ZonaSeleccion(
          archivos: _seleccionados,
          habilitada: !_subiendo && _preparando == null,
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
    final conPocaResolucion = _seleccionados.where(tienePocaResolucion).length;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (estadoApi == EstadoApi.sinConexion) ...[
          const AvisoCarga(
            tono: QTono.advertencia,
            icono: Icons.cloud_off_outlined,
            titulo: 'Sin conexión con el servidor',
            texto: 'Sus archivos siguen seleccionados. Podrá subirlos cuando vuelva la conexión.',
          ),
          const SizedBox(height: QEspacios.md),
        ],
        if (conPocaResolucion > 0 && !_subiendo) ...[
          AvisoCarga(
            tono: QTono.advertencia,
            icono: Icons.photo_size_select_large_outlined,
            titulo: conPocaResolucion == 1
                ? 'Una foto tiene poca resolución'
                : '$conPocaResolucion fotos tienen poca resolución',
            texto: 'Pueden quedar ilegibles. Tómelas más cerca o use la foto original, no la '
                'de WhatsApp.',
            detalle: 'Puede subirlas igual.',
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
        if (_preparando case (final hechas, final total)) ...[
          const SizedBox(height: QEspacios.sm + 4),
          LinearProgressIndicator(
            value: total == 0 ? null : hechas / total,
            semanticsLabel: 'Preparando las fotos',
          ),
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
    if (_preparando case (final hechas, final total)) {
      return 'Preparando las fotos: $hechas de $total…';
    }
    if (_subiendo) return 'Subiendo $archivos a $_examenId…';
    // Sin conexión ya lo explica el aviso de arriba, y una lista vacía, el campo del examen.
    if (estadoApi == EstadoApi.sinConexion) return null;
    if (_examenes?.isEmpty ?? false) return null;
    final elegir = _examenes == null ? 'Escriba el examen' : 'Elija el examen';
    final faltaExamen = _examenId.isEmpty;
    final faltanArchivos = _seleccionados.isEmpty;
    if (faltaExamen && faltanArchivos) return '$elegir y seleccione los archivos.';
    if (faltaExamen) return '$elegir.';
    if (faltanArchivos) return 'Seleccione al menos un archivo.';
    return '${_seleccionados.length == 1 ? 'Se subirá' : 'Se subirán'} $archivos a $_examenId.';
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
                titulo: 'Subiendo las hojas',
                texto: 'En unos segundos verá aquí cada una.',
              )
            : const QEstadoVacio(
                icono: Icons.fact_check_outlined,
                titulo: 'Todavía no hay resultados',
                texto: 'Aquí verá cada hoja con su nota.',
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
        lecturas: widget.consultarResultados == null ? null : _lecturas,
        leyendo: _consulta != null,
        alConsultarDeNuevo: _consultarResultados,
        alRevisar: widget.alRevisar == null
            ? null
            : () => widget.alRevisar!(_examenDelReporte),
      ),
    );
  }
}
