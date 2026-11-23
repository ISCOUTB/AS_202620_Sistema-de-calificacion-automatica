import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../../common/api/servicio_salud.dart';
import '../../../common/tema/tokens.dart';
import '../../../common/widgets/q_aviso_datos_ejemplo.dart';
import '../../../common/widgets/q_chip_estado.dart';
import '../../../common/widgets/q_encabezado_pantalla.dart';
import '../../../common/widgets/q_estado_vacio.dart';
import '../../../common/widgets/q_pagina.dart';
import '../../../common/widgets/q_titulo_seccion.dart';
import '../data/datos_ejemplo_pauta.dart';
import '../../carga/data/servicio_examenes.dart';
import '../data/servicio_clave.dart';
import '../data/servicio_distractores.dart';
import '../data/servicio_preguntas.dart';
import 'widgets/aviso_tono.dart';
import 'widgets/cabecera_generador.dart';
import 'widgets/esqueleto_propuestas.dart';
import 'widgets/fila_nueva_pregunta.dart';
import 'widgets/formulario_distractores.dart';
import 'widgets/lista_preguntas.dart';
import 'widgets/tarjeta_clave.dart';
import 'widgets/tarjetas_propuesta.dart';
import 'widgets/vista_propuestas.dart';

/// En qué punto está la solicitud de distractores.
enum _Fase { inicial, cargando, resultado, error }

/// Pauta y distractores: la fase de autoría del examen.
///
/// Tiene dos partes con distinto grado de realidad, y la pantalla no las mezcla:
///
/// * La clave del examen es real desde ADR-0026: se registra y se habilita con [TarjetaClaveDelExamen].
/// * La lista de preguntas tiene las de ejemplo, numeradas y bajo [QAvisoDatosEjemplo], y las que
///   el docente agrega con «+», guardadas a su nombre ([agregarPregunta], ADR-0030). Al final van
///   las que tienen distractores guardados, con ellos a la vista.
/// * El generador de distractores diagnósticos es real: llama a `POST /distractores` con
///   [proponerDistractores] (RF-11). Es la única función del sistema con modelo de lenguaje
///   (ADR-0005), y es opcional: el modelo propone y el docente decide qué usa (RF-07). Con
///   [guardarDistractores], lo que elige queda guardado a su nombre y la pregunta pasa al final de
///   la lista; elegirla ahí lo muestra sin pedirle nada al modelo (ADR-0029).
class PantallaPauta extends StatefulWidget {
  const PantallaPauta({
    super.key,
    required this.proponerDistractores,
    required this.estadoApi,
    this.listarExamenes,
    this.consultarClave,
    this.guardarClave,
    this.habilitarClave,
    this.crearExamen,
    this.alCambiarLaClave,
    this.guardarDistractores,
    this.listarDistractoresGuardados,
    this.quitarDistractoresGuardados,
    this.listarPreguntas,
    this.agregarPregunta,
    this.eliminarPregunta,
  });

  final Future<ResultadoDistractores> Function(SolicitudDistractores) proponerDistractores;
  final ValueListenable<EstadoApi> estadoApi;

  /// La clave del examen (A-04). Sin [consultarClave], la pantalla no ofrece registrarla.
  final Future<List<ExamenConClave>> Function()? listarExamenes;
  final Future<ClaveDelExamen?> Function(String examenId)? consultarClave;
  final Future<ClaveDelExamen> Function(String examenId, List<String> respuestas)? guardarClave;
  final Future<ClaveDelExamen> Function(String examenId)? habilitarClave;

  /// Crea el examen con el nombre que escribe el docente (ADR-0028).
  final Future<ExamenCreado> Function(String nombre)? crearExamen;
  final VoidCallback? alCambiarLaClave;

  /// Los distractores que el docente aprueba (ADR-0029). Sin [guardarDistractores], la pantalla no
  /// ofrece guardar y se comporta como antes.
  final Future<DistractoresGuardados> Function(
    SolicitudDistractores pregunta,
    List<DistractorPropuesto> elegidos,
  )? guardarDistractores;
  final Future<List<DistractoresGuardados>> Function()? listarDistractoresGuardados;
  final Future<void> Function(String llave)? quitarDistractoresGuardados;

  /// Las preguntas que el docente agrega (ADR-0030). Sin [agregarPregunta], la lista no ofrece «+».
  final Future<List<PreguntaDelDocente>> Function()? listarPreguntas;
  final Future<PreguntaDelDocente> Function(String enunciado, String respuestaCorrecta)?
      agregarPregunta;
  final Future<void> Function(String llave)? eliminarPregunta;

  @override
  State<PantallaPauta> createState() => _PantallaPautaState();
}

class _PantallaPautaState extends State<PantallaPauta> {
  /// Desde este ancho de contenido, la lista de preguntas va a la izquierda del generador. Por
  /// debajo, el generador quedaría en menos de 520 px y el formulario se apretaría.
  static const _anchoDosColumnas = 900.0;

  static const _examen = examenEjemplo;

  final _enunciado = TextEditingController();
  final _respuesta = TextEditingController();

  /// Para llevar la vista al generador cuando, en teléfono, el docente elige una pregunta que
  /// está diez filas más arriba.
  final _claveGenerador = GlobalKey();

  int _cantidad = 3;
  PreguntaEjemplo? _pregunta;

  /// La forma de la pregunta de la lista que llenó el formulario, si no se editó después.
  String? _seleccionada;

  /// Lo que la lista trae del servidor: las preguntas agregadas, la última primero, y lo guardado,
  /// lo último al final.
  List<PreguntaDelDocente> _agregadas = const [];
  List<DistractoresGuardados> _guardados = const [];
  bool _cargandoLista = false;
  String? _errorLista;
  String? _avisoLista;
  Set<String> _ocupadas = const {};
  bool _nuevaAbierta = false;

  /// Los errores de campo vacío solo aparecen después de que el docente tocó el campo: un
  /// formulario recién abierto no tiene por qué estar en rojo.
  bool _tocoEnunciado = false;
  bool _tocoRespuesta = false;

  _Fase _fase = _Fase.inicial;

  /// Sube con cada solicitud. Sirve para descartar una respuesta que llegue tarde y para que
  /// cada resultado nuevo vuelva a aparecer con su transición.
  int _version = 0;
  SolicitudDistractores? _solicitud;
  ResultadoDistractores? _resultado;

  /// Las tarjetas: primero lo guardado para la pregunta, después las propuestas que no lo repiten.
  /// «Regenerar» cambia una sola.
  List<DistractorPropuesto> _distractores = const [];
  List<DecisionDocente> _decisiones = const [];

  /// Lo guardado para la pregunta, en la forma con que se comparan dos expresiones.
  Set<String> _guardadas = const {};
  Set<int> _regenerando = const {};
  Map<int, String> _avisos = const {};
  bool _guardando = false;
  String? _mensajeGuardado;
  String? _errorGuardado;
  String _mensajeError = '';
  bool _proveedorNoDisponible = false;

  /// El 429 del presupuesto (ADR-0015). Con el límite por minuto, [_segundosParaReintentar]
  /// cuenta hacia atrás desde lo que dijo `Retry-After`. Con el diario no se ofrece repetir, y el
  /// botón principal tampoco se puede usar hasta que pase esa espera: cada clic sería otro 429
  /// que no llega al proveedor, pero que suma en los rechazos que publica `/metricas` (EC-09).
  bool _presupuestoAgotado = false;
  bool _cupoDiarioAgotado = false;
  int _segundosParaReintentar = 0;
  Timer? _cuentaRegresiva;

  bool get _camposCompletos =>
      _enunciado.text.trim().isNotEmpty && _respuesta.text.trim().isNotEmpty;

  bool get _conLista =>
      widget.listarPreguntas != null || widget.listarDistractoresGuardados != null;

  @override
  void initState() {
    super.initState();
    if (_conLista) {
      _cargandoLista = true;
      _traerLaLista();
    }
  }

  void _recargarLaLista() {
    setState(() {
      _cargandoLista = true;
      _errorLista = null;
    });
    _traerLaLista();
  }

  Future<void> _traerLaLista() async {
    try {
      final (agregadas, guardados) = await (
        widget.listarPreguntas?.call() ?? Future.value(const <PreguntaDelDocente>[]),
        widget.listarDistractoresGuardados?.call() ??
            Future.value(const <DistractoresGuardados>[]),
      ).wait;
      if (!mounted) return;
      setState(() {
        _agregadas = agregadas;
        _guardados = guardados;
        _cargandoLista = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _cargandoLista = false;
        _errorLista = 'No se pudieron cargar sus preguntas ni sus distractores guardados.';
      });
    }
  }

  static String _formaDe(DistractoresGuardados g) =>
      formaDeLaPregunta(g.enunciado, g.respuestaCorrecta);

  DistractoresGuardados? _guardadosDe(String forma) =>
      _guardados.where((g) => _formaDe(g) == forma).firstOrNull;

  PreguntaEjemplo? _ejemploDe(String forma) => _examen.preguntas
      .where((p) => formaDeLaPregunta(p.enunciado, p.respuestaCorrecta) == forma)
      .firstOrNull;

  PreguntaDelDocente? _agregadaDe(String forma) => _agregadas
      .where((p) => formaDeLaPregunta(p.enunciado, p.respuestaCorrecta) == forma)
      .firstOrNull;

  /// Arriba las agregadas sin distractores guardados; después, las de ejemplo sin ellos.
  List<FilaDeLaLista> get _filasPendientes {
    final conGuardados = {for (final g in _guardados) _formaDe(g)};
    final filas = [
      for (final a in _agregadas)
        FilaDeLaLista(enunciado: a.enunciado, respuestaCorrecta: a.respuestaCorrecta, agregada: a),
      for (final e in _examen.preguntas)
        FilaDeLaLista(enunciado: e.enunciado, respuestaCorrecta: e.respuestaCorrecta, ejemplo: e),
    ];
    final vistas = <String>{};
    return [
      for (final fila in filas)
        if (!conGuardados.contains(fila.forma) && vistas.add(fila.forma)) fila,
    ];
  }

  /// Las que tienen distractores guardados, lo último al final.
  List<FilaDeLaLista> get _filasGuardadas => [for (final g in _guardados) _filaGuardada(g)];

  FilaDeLaLista _filaGuardada(DistractoresGuardados guardados) {
    final forma = _formaDe(guardados);
    final ejemplo = _ejemploDe(forma);
    return FilaDeLaLista(
      enunciado: ejemplo?.enunciado ?? guardados.enunciado,
      respuestaCorrecta: ejemplo?.respuestaCorrecta ?? guardados.respuestaCorrecta,
      ejemplo: ejemplo,
      agregada: _agregadaDe(forma),
      guardados: guardados,
    );
  }

  @override
  void dispose() {
    _cuentaRegresiva?.cancel();
    _enunciado.dispose();
    _respuesta.dispose();
    super.dispose();
  }

  void _contarHastaReintentar(Duration espera) {
    _segundosParaReintentar = espera.inSeconds;
    _cuentaRegresiva = Timer.periodic(const Duration(seconds: 1), (temporizador) {
      if (!mounted) return;
      setState(() => _segundosParaReintentar--);
      if (_segundosParaReintentar <= 0) temporizador.cancel();
    });
  }

  /// La espera del límite diario dura horas: no hace falta contarla de a un segundo, basta con
  /// volver a habilitar el botón cuando termine.
  void _esperarCupoDiario(Duration espera) {
    _cuentaRegresiva = Timer(espera, () {
      if (mounted) setState(() => _cupoDiarioAgotado = false);
    });
  }

  /// Elegir una fila llena el formulario. Si es otra pregunta, el generador deja lo de la
  /// anterior: muestra sus distractores guardados, sin pedirle nada al modelo, o queda vacío.
  /// Volver a elegir la misma no lo toca.
  void _elegir(FilaDeLaLista fila, {required bool desplazar}) {
    final solicitud = _solicitud;
    final otra = solicitud == null ||
        formaDeLaPregunta(solicitud.enunciado, solicitud.respuestaCorrecta) != fila.forma;
    setState(() {
      _pregunta = fila.ejemplo;
      _seleccionada = fila.forma;
      _enunciado.text = fila.enunciado;
      _respuesta.text = fila.respuestaCorrecta;
      _tocoEnunciado = false;
      _tocoRespuesta = false;
      if (otra) {
        if (fila.guardados case final guardados?) {
          _mostrarGuardados(fila, guardados);
        } else if (!_esperandoCupo) {
          _vaciarGenerador();
        }
      }
    });
    if (!desplazar) return;
    final instantaneo = MediaQuery.disableAnimationsOf(context);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final destino = _claveGenerador.currentContext;
      if (destino == null || !destino.mounted) return;
      Scrollable.ensureVisible(
        destino,
        duration: instantaneo ? Duration.zero : QDuraciones.media,
        curve: Curves.easeOutCubic,
      );
    });
  }

  /// Mientras corre la espera del 429 el aviso se queda, aunque cambie la pregunta: el límite es
  /// de todas, y pedir de nuevo solo traería otro 429.
  bool get _esperandoCupo =>
      _fase == _Fase.error &&
      _presupuestoAgotado &&
      (_segundosParaReintentar > 0 || _cupoDiarioAgotado);

  /// El generador como al abrir la pantalla. Sube la versión, así que una respuesta que llegue
  /// tarde para la pregunta anterior se descarta.
  void _vaciarGenerador() {
    _version++;
    _cuentaRegresiva?.cancel();
    _fase = _Fase.inicial;
    _solicitud = null;
    _resultado = null;
    _distractores = const [];
    _decisiones = const [];
    _guardadas = const {};
    _regenerando = const {};
    _avisos = const {};
    _guardando = false;
    _mensajeGuardado = null;
    _errorGuardado = null;
    _presupuestoAgotado = false;
    _cupoDiarioAgotado = false;
    _segundosParaReintentar = 0;
  }

  /// Lo guardado como si acabara de llegar: elegido y marcado, listo para pedir otras o cambiar.
  void _mostrarGuardados(FilaDeLaLista fila, DistractoresGuardados guardados) {
    _version++;
    _cuentaRegresiva?.cancel();
    _fase = _Fase.resultado;
    _solicitud = SolicitudDistractores(
      enunciado: fila.enunciado,
      respuestaCorrecta: fila.respuestaCorrecta,
      cantidad: _cantidad,
    );
    _resultado = const ResultadoDistractores(distractores: [], descartados: []);
    _distractores = guardados.distractores;
    _decisiones = [for (final _ in guardados.distractores) DecisionDocente.usar];
    _guardadas = {for (final d in guardados.distractores) _forma(d.expresion)};
    _regenerando = const {};
    _avisos = const {};
    _guardando = false;
    _mensajeGuardado = null;
    _errorGuardado = null;
  }

  // Si el docente edita lo que trajo de la lista, el formulario ya no es esa pregunta.
  void _editoEnunciado() => setState(() {
        _tocoEnunciado = true;
        _pregunta = null;
        _seleccionada = null;
      });

  void _editoRespuesta() => setState(() {
        _tocoRespuesta = true;
        _pregunta = null;
        _seleccionada = null;
      });

  void _proponerDesdeFormulario() {
    _pedir(SolicitudDistractores(
      enunciado: _enunciado.text.trim(),
      respuestaCorrecta: _respuesta.text.trim(),
      cantidad: _cantidad,
    ));
  }

  /// «Volver a pedir» repite la última solicitud tal cual, aunque el docente haya cambiado el
  /// formulario mientras tanto: las propuestas en pantalla son de esa pregunta, y las nuevas deben
  /// serlo también. «Pedir otras propuestas» hace lo mismo con `otras: true` (`_pedirOtras`).
  void _repetir() {
    final solicitud = _solicitud;
    if (solicitud != null) _pedir(solicitud);
  }

  /// «Pedir otras propuestas» repite la pregunta pidiendo propuestas nuevas: sin `otras`, la API
  /// respondería con las mismas que ya están en pantalla, guardadas en su caché (ADR-0019).
  void _pedirOtras() {
    final solicitud = _solicitud;
    if (solicitud != null) _pedir(solicitud.paraPedirOtras());
  }

  Future<void> _pedir(SolicitudDistractores solicitud) async {
    final version = ++_version;
    _cuentaRegresiva?.cancel();
    setState(() {
      _fase = _Fase.cargando;
      _solicitud = solicitud;
    });
    try {
      final resultado = await widget.proponerDistractores(solicitud);
      if (!mounted || version != _version) return;
      final anteriores = _guardadosDe(
            formaDeLaPregunta(solicitud.enunciado, solicitud.respuestaCorrecta),
          )?.distractores ??
          const <DistractorPropuesto>[];
      final formas = {for (final d in anteriores) _forma(d.expresion)};
      final nuevas = resultado.distractores.where((d) => !formas.contains(_forma(d.expresion)));
      setState(() {
        _fase = _Fase.resultado;
        _resultado = resultado;
        _distractores = [...anteriores, ...nuevas];
        _decisiones = [
          for (final _ in anteriores) DecisionDocente.usar,
          for (final _ in nuevas) DecisionDocente.pendiente,
        ];
        _guardadas = formas;
        _regenerando = const {};
        _avisos = const {};
        _guardando = false;
        _mensajeGuardado = null;
        _errorGuardado = null;
      });
    } on ExcepcionDistractores catch (e) {
      if (!mounted || version != _version) return;
      setState(() {
        _fase = _Fase.error;
        _mensajeError = e.mensaje;
        _proveedorNoDisponible = e.proveedorNoDisponible;
        _presupuestoAgotado = e.presupuestoAgotado;
        _cupoDiarioAgotado = e.cupoDiarioAgotado;
        _segundosParaReintentar = 0;
        final espera = e.reintentarEn;
        if (e.presupuestoAgotado && espera != null) {
          if (e.cupoDiarioAgotado) {
            _esperarCupoDiario(espera);
          } else {
            _contarHastaReintentar(espera);
          }
        }
      });
    } catch (_) {
      // Una respuesta 200 con un cuerpo que no se puede leer: no es culpa del docente ni del
      // proveedor, y reintentar de inmediato no la arregla.
      if (!mounted || version != _version) return;
      setState(() {
        _fase = _Fase.error;
        _mensajeError = 'La respuesta del servidor no se pudo leer. Vuelva a intentarlo más '
            'tarde o escriba los distractores a mano.';
        _proveedorNoDisponible = false;
        _presupuestoAgotado = false;
      });
    }
  }

  /// Cómo se comparan dos expresiones aquí: sin espacios y en minúsculas. La API aplica además
  /// la regla completa al guardar (`autoria.distractores.normalizar`).
  static String _forma(String expresion) =>
      expresion.replaceAll(RegExp(r'\s+'), '').toLowerCase();

  void _decidir(int indice, DecisionDocente decision) {
    setState(() {
      _decisiones = [..._decisiones]..[indice] = decision;
      _mensajeGuardado = null;
      _errorGuardado = null;
    });
  }

  /// Las tarjetas que cuentan como guardadas: elegidas y con la forma de una guardada.
  List<bool> get _marcasDeGuardada => [
        for (final (i, d) in _distractores.indexed)
          _decisiones[i] == DecisionDocente.usar && _guardadas.contains(_forma(d.expresion)),
      ];

  List<DistractorPropuesto> get _elegidos => [
        for (final (i, d) in _distractores.indexed)
          if (_decisiones[i] == DecisionDocente.usar) d,
      ];

  /// Hay algo que guardar: entre una y las que caben, y distinto de lo que ya está guardado.
  bool get _puedeGuardar {
    final elegidos = _elegidos;
    if (elegidos.isEmpty || elegidos.length > _examen.distractoresPorPregunta) return false;
    final formas = {for (final d in elegidos) _forma(d.expresion)};
    return formas.length != _guardadas.length || !formas.containsAll(_guardadas);
  }

  /// «Regenerar» en una tarjeta descartada: pide una sola propuesta nueva y reemplaza solo esa.
  /// Si la nueva repite a otra tarjeta, o no llega, la tarjeta queda como estaba y dice por qué.
  Future<void> _regenerar(int indice) async {
    final solicitud = _solicitud;
    if (solicitud == null) return;
    final version = _version;
    setState(() {
      _regenerando = {..._regenerando, indice};
      _avisos = {..._avisos}..remove(indice);
    });
    DistractorPropuesto? nueva;
    String? aviso;
    try {
      final resultado = await widget.proponerDistractores(solicitud.paraRegenerarUna());
      if (resultado.distractores.isEmpty) {
        final motivo = resultado.descartados.isEmpty ? null : resultado.descartados.first.motivo;
        aviso = motivo == null
            ? 'No llegó ninguna propuesta nueva. Vuelva a intentarlo.'
            : 'La propuesta nueva se descartó: '
                '${motivo[0].toLowerCase()}${motivo.substring(1)}. Vuelva a intentarlo.';
      } else {
        final candidata = resultado.distractores.first;
        final repetida = _distractores.any((d) => _forma(d.expresion) == _forma(candidata.expresion));
        if (repetida) {
          aviso = 'El modelo volvió a proponer «${candidata.expresion}», que ya está. Vuelva a '
              'intentarlo.';
        } else {
          nueva = candidata;
        }
      }
    } on ExcepcionDistractores catch (e) {
      aviso = e.mensaje;
    } catch (_) {
      aviso = 'La respuesta del servidor no se pudo leer. Vuelva a intentarlo.';
    }
    if (!mounted || version != _version) return;
    setState(() {
      _regenerando = {..._regenerando}..remove(indice);
      if (nueva != null) {
        _distractores = [..._distractores]..[indice] = nueva;
        _decisiones = [..._decisiones]..[indice] = DecisionDocente.pendiente;
        _mensajeGuardado = null;
      }
      if (aviso != null) _avisos = {..._avisos, indice: aviso};
    });
  }

  Future<void> _guardar() async {
    final guardar = widget.guardarDistractores;
    final solicitud = _solicitud;
    if (guardar == null || solicitud == null) return;
    final version = _version;
    setState(() {
      _guardando = true;
      _mensajeGuardado = null;
      _errorGuardado = null;
    });
    try {
      await _ponerEnLaLista(solicitud.enunciado, solicitud.respuestaCorrecta);
      final guardados = await guardar(solicitud, _elegidos);
      if (!mounted) return;
      final forma = _formaDe(guardados);
      // La pregunta pasa al final de la lista aunque el docente ya esté en otra.
      setState(() => _guardados = [..._guardados.where((g) => _formaDe(g) != forma), guardados]);
      if (version != _version) return;
      final n = guardados.distractores.length;
      setState(() {
        _guardando = false;
        _guardadas = {for (final d in guardados.distractores) _forma(d.expresion)};
        _mensajeGuardado = n == 1
            ? 'Se guardó 1 distractor. La pregunta quedó al final de la lista.'
            : 'Se guardaron $n distractores. La pregunta quedó al final de la lista.';
      });
    } on ExcepcionPreguntas catch (e) {
      if (!mounted || version != _version) return;
      setState(() {
        _guardando = false;
        _errorGuardado = e.mensaje;
      });
    } on ExcepcionDistractores catch (e) {
      if (!mounted || version != _version) return;
      setState(() {
        _guardando = false;
        _errorGuardado = e.mensaje;
      });
    } catch (_) {
      if (!mounted || version != _version) return;
      setState(() {
        _guardando = false;
        _errorGuardado = 'No se pudieron guardar. Vuelva a intentarlo.';
      });
    }
  }

  /// Una pregunta que no es de ejemplo ni está agregada se agrega antes de guardarle o quitarle
  /// distractores: así queda en la lista, y al quitárselos vuelve arriba en vez de desaparecer.
  Future<void> _ponerEnLaLista(String enunciado, String respuestaCorrecta) async {
    final agregar = widget.agregarPregunta;
    final forma = formaDeLaPregunta(enunciado, respuestaCorrecta);
    if (agregar == null || _ejemploDe(forma) != null || _agregadaDe(forma) != null) return;
    try {
      final agregada = await agregar(enunciado, respuestaCorrecta);
      if (mounted) setState(() => _agregadas = [agregada, ..._agregadas]);
    } on ExcepcionPreguntas catch (e) {
      // Ya la tenía en el servidor aunque la lista no la mostrara: sigue igual.
      if (!e.yaEstaba) rethrow;
    }
  }

  Future<void> _quitar(FilaDeLaLista fila) async {
    final quitar = widget.quitarDistractoresGuardados;
    final guardados = fila.guardados;
    if (quitar == null || guardados == null) return;
    setState(() {
      _ocupadas = {..._ocupadas, fila.forma};
      _avisoLista = null;
    });
    try {
      await _ponerEnLaLista(fila.enunciado, fila.respuestaCorrecta);
      await quitar(guardados.llave);
      if (!mounted) return;
      setState(() {
        _guardados = [for (final g in _guardados) if (g.llave != guardados.llave) g];
        final solicitud = _solicitud;
        final abierta = solicitud != null &&
            formaDeLaPregunta(solicitud.enunciado, solicitud.respuestaCorrecta) == fila.forma;
        if (abierta) {
          _guardadas = const {};
          _mensajeGuardado = null;
        }
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _avisoLista = 'No se pudieron quitar los distractores guardados. Vuelva a '
          'intentarlo.');
    } finally {
      if (mounted) setState(() => _ocupadas = {..._ocupadas}..remove(fila.forma));
    }
  }

  Future<void> _eliminar(FilaDeLaLista fila) async {
    final eliminar = widget.eliminarPregunta;
    final agregada = fila.agregada;
    if (eliminar == null || agregada == null) return;
    setState(() {
      _ocupadas = {..._ocupadas, fila.forma};
      _avisoLista = null;
    });
    try {
      await eliminar(agregada.llave);
      if (!mounted) return;
      setState(() {
        _agregadas = [for (final a in _agregadas) if (a.llave != agregada.llave) a];
        if (_seleccionada == fila.forma) _seleccionada = null;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _avisoLista = 'No se pudo eliminar la pregunta. Vuelva a intentarlo.');
    } finally {
      if (mounted) setState(() => _ocupadas = {..._ocupadas}..remove(fila.forma));
    }
  }

  /// Lo que hace «Agregar» en la fila nueva. Devuelve el motivo si no se agregó.
  Future<String?> _agregar(String enunciado, String respuestaCorrecta) async {
    final agregar = widget.agregarPregunta;
    if (agregar == null) return null;
    final forma = formaDeLaPregunta(enunciado, respuestaCorrecta);
    if (_ejemploDe(forma) != null || _agregadaDe(forma) != null || _guardadosDe(forma) != null) {
      return 'Esa pregunta ya está en la lista.';
    }
    try {
      final agregada = await agregar(enunciado, respuestaCorrecta);
      if (mounted) setState(() => _agregadas = [agregada, ..._agregadas]);
      return null;
    } on ExcepcionPreguntas catch (e) {
      return e.mensaje;
    } catch (_) {
      return 'No se pudo agregar la pregunta. Vuelva a intentarlo.';
    }
  }

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<EstadoApi>(
      valueListenable: widget.estadoApi,
      builder: (context, estadoApi, _) {
        final sinConexion = estadoApi == EstadoApi.sinConexion;
        return QPagina(
          children: [
            const QEncabezadoPantalla(
              etiqueta: 'Preparación del examen',
              iconoEtiqueta: Icons.edit_note_outlined,
              titulo: 'Pauta y distractores',
              descripcion: 'La clave del examen y propuestas de distractores diagnósticos '
                  'para sus preguntas.',
              extremo: QChipEstado(
                texto: 'Periodo 2026-2',
                icono: Icons.calendar_today_outlined,
              ),
            ),
            const SizedBox(height: QEspacios.lg),
            if (widget.consultarClave case final consultar?) ...[
              TarjetaClaveDelExamen(
                listarExamenes: widget.listarExamenes,
                consultarClave: consultar,
                guardarClave: widget.guardarClave!,
                habilitarClave: widget.habilitarClave!,
                crearExamen: widget.crearExamen,
                alCambiar: widget.alCambiarLaClave,
              ),
              const SizedBox(height: QEspacios.xl),
            ],
            LayoutBuilder(
              builder: (context, restricciones) {
                final ancha = restricciones.maxWidth >= _anchoDosColumnas;
                final examen = _bloqueExamen(desplazar: !ancha);
                final generador = KeyedSubtree(
                  key: _claveGenerador,
                  child: _bloqueGenerador(sinConexion: sinConexion),
                );
                if (!ancha) {
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [examen, const SizedBox(height: QEspacios.xl), generador],
                  );
                }
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(flex: 5, child: examen),
                    const SizedBox(width: QEspacios.lg),
                    Expanded(flex: 7, child: generador),
                  ],
                );
              },
            ),
          ],
        );
      },
    );
  }

  Widget _bloqueExamen({required bool desplazar}) {
    return Column(
      key: const Key('bloque-examen'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        QAvisoDatosEjemplo(
          detalle: widget.agregarPregunta == null
              ? 'Estas preguntas son de ejemplo.'
              : 'Las preguntas numeradas son de ejemplo. Las que agregue con «+» se guardan a '
                  'su nombre.',
        ),
        const SizedBox(height: QEspacios.lg),
        QTituloSeccion(
          titulo: 'Preguntas del examen',
          descripcion: 'Elija una para llevarla al generador de distractores.',
          accion: widget.agregarPregunta == null
              ? null
              : IconButton.filledTonal(
                  key: const Key('boton-nueva-pregunta'),
                  tooltip: 'Agregar una pregunta',
                  onPressed: () => setState(() => _nuevaAbierta = !_nuevaAbierta),
                  icon: const Icon(Icons.add),
                ),
        ),
        const SizedBox(height: QEspacios.sm + 4),
        if (_errorLista case final error?) ...[
          Row(
            children: [
              Expanded(
                child: Text(
                  error,
                  style: Theme.of(context)
                      .textTheme
                      .bodySmall
                      ?.copyWith(color: QColores.errorTexto),
                ),
              ),
              TextButton(
                key: const Key('boton-reintentar-lista'),
                onPressed: _recargarLaLista,
                child: const Text('Reintentar'),
              ),
            ],
          ),
          const SizedBox(height: QEspacios.sm),
        ],
        if (_avisoLista case final aviso?) ...[
          Text(
            aviso,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: QColores.errorTexto),
          ),
          const SizedBox(height: QEspacios.sm),
        ],
        if (_cargandoLista) ...[
          Text(
            'Cargando sus preguntas…',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(color: QColores.textoSuave),
          ),
          const SizedBox(height: QEspacios.sm),
        ],
        ListaPreguntas(
          pendientes: _filasPendientes,
          guardadas: _filasGuardadas,
          seleccionada: _seleccionada,
          alElegir: (fila) => _elegir(fila, desplazar: desplazar),
          alQuitar: widget.quitarDistractoresGuardados == null ? null : _quitar,
          alEliminar: widget.eliminarPregunta == null ? null : _eliminar,
          ocupadas: _ocupadas,
          filaNueva: _nuevaAbierta
              ? FilaNuevaPregunta(
                  alAgregar: _agregar,
                  alCerrar: () => setState(() => _nuevaAbierta = false),
                )
              : null,
        ),
      ],
    );
  }

  Widget _bloqueGenerador({required bool sinConexion}) {
    final cargando = _fase == _Fase.cargando;
    // Mientras corre la cuenta del 429, o mientras dura el límite diario, pedir de nuevo solo
    // traería otro 429: el aviso de abajo dice cuánto falta.
    final esperandoCupo = _esperandoCupo;
    final puedeProponer = _camposCompletos && !cargando && !sinConexion && !esperandoCupo;
    final sinAnimacion = MediaQuery.disableAnimationsOf(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const CabeceraGenerador(),
        const SizedBox(height: QEspacios.md),
        FormularioDistractores(
          enunciado: _enunciado,
          respuesta: _respuesta,
          errorEnunciado: _tocoEnunciado && _enunciado.text.trim().isEmpty
              ? 'Escriba el enunciado de la pregunta.'
              : null,
          errorRespuesta: _tocoRespuesta && _respuesta.text.trim().isEmpty
              ? 'Escriba la respuesta correcta.'
              : null,
          alEditarEnunciado: _editoEnunciado,
          alEditarRespuesta: _editoRespuesta,
          cantidad: _cantidad,
          alCambiarCantidad: (n) => setState(() => _cantidad = n),
          pregunta: _pregunta,
          examen: _examen,
          camposCompletos: _camposCompletos,
          sinConexion: sinConexion,
          cargando: cargando,
          alProponer: puedeProponer ? _proponerDesdeFormulario : null,
        ),
        const SizedBox(height: QEspacios.lg),
        // Los resultados aparecen con un fundido corto y un desplazamiento mínimo: marca que el
        // contenido cambió sin distraer. La salida es instantánea para que la vista anterior y
        // la nueva no se encimen, y todo se omite si el sistema pide reducir el movimiento.
        AnimatedSwitcher(
          duration: sinAnimacion ? Duration.zero : QDuraciones.media,
          reverseDuration: Duration.zero,
          switchInCurve: Curves.easeOutCubic,
          // `passthrough` les da el ancho completo de la columna; el `Stack` por omisión lo
          // aflojaría y el estado vacío quedaría encogido al centro.
          layoutBuilder: (actual, anteriores) => Stack(
            alignment: Alignment.topCenter,
            fit: StackFit.passthrough,
            children: [...anteriores, if (actual != null) actual],
          ),
          transitionBuilder: (hijo, animacion) => FadeTransition(
            opacity: animacion,
            child: SlideTransition(
              position: Tween(begin: const Offset(0, 0.02), end: Offset.zero).animate(animacion),
              child: hijo,
            ),
          ),
          child: KeyedSubtree(
            key: ValueKey('${_fase.name}-$_version'),
            child: _vistaSegunFase(sinConexion: sinConexion),
          ),
        ),
      ],
    );
  }

  Widget _vistaSegunFase({required bool sinConexion}) {
    switch (_fase) {
      case _Fase.inicial:
        return const _SinPropuestas();
      case _Fase.cargando:
        return EsqueletoPropuestas(cantidad: _solicitud!.cantidad);
      case _Fase.resultado:
        final ofreceGuardar = widget.guardarDistractores != null;
        return VistaPropuestas(
          solicitud: _solicitud!,
          resultado: _resultado!,
          distractores: _distractores,
          decisiones: _decisiones,
          alDecidir: _decidir,
          alPedirOtras: sinConexion ? null : _pedirOtras,
          distractoresPorPregunta: _examen.distractoresPorPregunta,
          guardadas: _marcasDeGuardada,
          regenerando: _regenerando,
          avisos: _avisos,
          alRegenerar: sinConexion ? null : _regenerar,
          ofreceGuardar: ofreceGuardar,
          alGuardar: ofreceGuardar && !sinConexion && _puedeGuardar ? _guardar : null,
          guardando: _guardando,
          mensajeGuardado: _mensajeGuardado,
          errorGuardado: _errorGuardado,
        );
      case _Fase.error:
        // El 503 y el 429 no son errores del docente ni definitivos: el proveedor falló o
        // tardó más de 20 s, o se acabó el cupo de solicitudes. Van con tono de advertencia;
        // cualquier otra falla va en rojo, porque reintentar igual no la resuelve.
        if (_presupuestoAgotado) {
          final esperando = _segundosParaReintentar > 0;
          return AvisoTono(
            key: const Key('aviso-presupuesto'),
            tono: QTono.advertencia,
            icono: Icons.timer_outlined,
            titulo: 'Se llegó al límite de solicitudes de IA',
            mensaje: _mensajeError,
            anunciar: true,
            // Con el límite diario el mensaje de la API ya dice en cuántas horas vuelve el
            // cupo y que mientras tanto se escriben a mano: un botón ahí sería una promesa falsa.
            accion: _cupoDiarioAgotado
                ? null
                : OutlinedButton.icon(
                    key: const Key('boton-volver-a-pedir'),
                    onPressed: sinConexion || esperando ? null : _repetir,
                    icon: const Icon(Icons.refresh_outlined, size: 20),
                    // El lector de pantalla oye siempre «Volver a pedir»: el aviso es una región
                    // viva, y con la cuenta en la etiqueta lo repetiría cada segundo.
                    label: Semantics(
                      label: 'Volver a pedir',
                      excludeSemantics: true,
                      child: Text(esperando
                          ? 'Volver a pedir en $_segundosParaReintentar s'
                          : 'Volver a pedir'),
                    ),
                  ),
          );
        }
        if (_proveedorNoDisponible) {
          return AvisoTono(
            key: const Key('aviso-proveedor'),
            tono: QTono.advertencia,
            icono: Icons.hourglass_empty_outlined,
            titulo: 'El proveedor de IA no respondió',
            mensaje: _mensajeError,
            anunciar: true,
            accion: OutlinedButton.icon(
              key: const Key('boton-volver-a-pedir'),
              onPressed: sinConexion ? null : _repetir,
              icon: const Icon(Icons.refresh_outlined, size: 20),
              label: const Text('Volver a pedir'),
            ),
          );
        }
        return AvisoTono(
          key: const Key('aviso-error'),
          tono: QTono.error,
          icono: Icons.error_outline_outlined,
          titulo: 'No se pudieron pedir las propuestas',
          mensaje: _mensajeError,
          anunciar: true,
        );
    }
  }
}

/// Antes de la primera solicitud: qué se puede hacer aquí, y que no es obligatorio.
class _SinPropuestas extends StatelessWidget {
  const _SinPropuestas();

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(QRadios.tarjeta),
        border: Border.all(color: QColores.borde),
      ),
      child: const QEstadoVacio(
        icono: Icons.lightbulb_outlined,
        titulo: 'Todavía no hay propuestas',
        texto: 'Elija una pregunta del examen o escriba una, y pida distractores. Es opcional: '
            'también puede escribirlos a mano.',
      ),
    );
  }
}
