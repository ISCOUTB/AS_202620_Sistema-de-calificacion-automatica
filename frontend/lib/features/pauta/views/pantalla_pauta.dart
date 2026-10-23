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
import '../data/servicio_distractores.dart';
import 'widgets/aviso_tono.dart';
import 'widgets/cabecera_generador.dart';
import 'widgets/esqueleto_propuestas.dart';
import 'widgets/formulario_distractores.dart';
import 'widgets/lista_preguntas.dart';
import 'widgets/tarjeta_examen.dart';
import 'widgets/tarjetas_propuesta.dart';
import 'widgets/vista_propuestas.dart';

/// En qué punto está la solicitud de distractores.
enum _Fase { inicial, cargando, resultado, error }

/// Pauta y distractores: la fase de autoría del examen.
///
/// Tiene dos partes con distinto grado de realidad, y la pantalla no las mezcla:
///
/// * El examen, su clave y su banco de preguntas son de ejemplo, porque el backend todavía no
///   los tiene (A-04). Van bajo [QAvisoDatosEjemplo].
/// * El generador de distractores diagnósticos es real: llama a `POST /distractores` con
///   [proponerDistractores] (RF-11). Es la única función del sistema con modelo de lenguaje
///   (ADR-0005), y es opcional: el modelo propone y el docente decide qué usa (RF-07).
class PantallaPauta extends StatefulWidget {
  const PantallaPauta({
    super.key,
    required this.proponerDistractores,
    required this.estadoApi,
  });

  final Future<ResultadoDistractores> Function(SolicitudDistractores) proponerDistractores;
  final ValueListenable<EstadoApi> estadoApi;

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
  List<DecisionDocente> _decisiones = const [];
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

  void _elegir(PreguntaEjemplo pregunta, {required bool desplazar}) {
    setState(() {
      _pregunta = pregunta;
      _enunciado.text = pregunta.enunciado;
      _respuesta.text = pregunta.respuestaCorrecta;
      _tocoEnunciado = false;
      _tocoRespuesta = false;
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

  // Si el docente edita lo que trajo de la lista, el formulario ya no es esa pregunta.
  void _editoEnunciado() => setState(() {
        _tocoEnunciado = true;
        _pregunta = null;
      });

  void _editoRespuesta() => setState(() {
        _tocoRespuesta = true;
        _pregunta = null;
      });

  void _proponerDesdeFormulario() {
    _pedir(SolicitudDistractores(
      enunciado: _enunciado.text.trim(),
      respuestaCorrecta: _respuesta.text.trim(),
      cantidad: _cantidad,
    ));
  }

  /// «Pedir otras propuestas» y «Volver a pedir» repiten la última solicitud tal cual, aunque
  /// el docente haya cambiado el formulario mientras tanto: las propuestas en pantalla son de
  /// esa pregunta, y las nuevas deben serlo también.
  void _repetir() {
    final solicitud = _solicitud;
    if (solicitud != null) _pedir(solicitud);
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
      setState(() {
        _fase = _Fase.resultado;
        _resultado = resultado;
        _decisiones = List.filled(resultado.distractores.length, DecisionDocente.pendiente);
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
        _mensajeError = 'La API respondió algo que esta pantalla no sabe leer. Vuelva a '
            'intentarlo más tarde o escriba los distractores a mano.';
        _proveedorNoDisponible = false;
        _presupuestoAgotado = false;
      });
    }
  }

  void _decidir(int indice, DecisionDocente decision) {
    setState(() {
      _decisiones = [..._decisiones]..[indice] = decision;
    });
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
        const QAvisoDatosEjemplo(
          detalle: 'El banco de preguntas, la clave y la habilitación (A-04) todavía no están '
              'construidos: esta parte es de ejemplo. El generador de distractores sí usa la '
              'API.',
        ),
        const SizedBox(height: QEspacios.md),
        const TarjetaExamen(examen: _examen),
        const SizedBox(height: QEspacios.lg),
        const QTituloSeccion(
          titulo: 'Preguntas del examen',
          descripcion: 'Elija una para llevarla al generador de distractores.',
        ),
        const SizedBox(height: QEspacios.sm + 4),
        ListaPreguntas(
          preguntas: _examen.preguntas,
          seleccionada: _pregunta?.numero,
          alElegir: (pregunta) => _elegir(pregunta, desplazar: desplazar),
        ),
      ],
    );
  }

  Widget _bloqueGenerador({required bool sinConexion}) {
    final cargando = _fase == _Fase.cargando;
    // Mientras corre la cuenta del 429, o mientras dura el límite diario, pedir de nuevo solo
    // traería otro 429: el aviso de abajo dice cuánto falta.
    final esperandoCupo = _fase == _Fase.error &&
        _presupuestoAgotado &&
        (_segundosParaReintentar > 0 || _cupoDiarioAgotado);
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
        return VistaPropuestas(
          solicitud: _solicitud!,
          resultado: _resultado!,
          decisiones: _decisiones,
          alDecidir: _decidir,
          alPedirOtras: sinConexion ? null : _repetir,
          distractoresPorPregunta: _examen.distractoresPorPregunta,
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
