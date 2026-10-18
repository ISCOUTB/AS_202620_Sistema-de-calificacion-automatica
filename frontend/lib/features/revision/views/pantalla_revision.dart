import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../../common/tema/tokens.dart';
import '../../../common/widgets/q_aviso_datos_ejemplo.dart';
import '../../../common/widgets/q_encabezado_pantalla.dart';
import '../../../common/widgets/q_estado_vacio.dart';
import '../../../common/widgets/q_pagina.dart';
import '../../../common/widgets/q_tarjeta.dart';
import '../../../common/widgets/q_titulo_seccion.dart';
import '../data/datos_ejemplo_revision.dart';
import 'formato_revision.dart';
import 'widgets/seccion_estudiantes.dart';
import 'widgets/tarjeta_caso.dart';

/// Filtros de la lista de estudiantes. Los conteos se calculan de los datos en cada cambio.
enum FiltroEstudiantes {
  todos('Todos', Icons.groups_outlined, QColores.textoSuave),
  revision('Requieren revisión', Icons.warning_amber_outlined, QColores.advertenciaTexto),
  calificados('Calificados', Icons.check_circle_outline, QColores.exitoTexto),
  doble('Doble marcación', Icons.content_copy_outlined, QColores.errorTexto);

  const FiltroEstudiantes(this.etiqueta, this.icono, this.colorIcono);

  final String etiqueta;
  final IconData icono;
  final Color colorIcono;

  bool incluye(FilaEstudiante fila) => switch (this) {
        FiltroEstudiantes.todos => true,
        FiltroEstudiantes.revision => fila.pendiente,
        FiltroEstudiantes.calificados => !fila.pendiente,
        FiltroEstudiantes.doble => fila.dobleMarcacion,
      };
}

enum OrdenNotas { mayor, menor }

/// Revisión manual y calificaciones (RF-03 y RF-08).
///
/// Toda marca con confianza menor al umbral llega aquí en vez de asignarse a ciegas; el docente
/// decide qué quiso marcar el estudiante y la nota se recalcula. Hoy no existen la detección de
/// marcas (A-02) ni la calificación (A-03), así que la vista corre sobre datos de ejemplo, lo
/// avisa arriba y no guarda ninguna decisión.
class PantallaRevision extends StatefulWidget {
  const PantallaRevision({super.key});

  @override
  State<PantallaRevision> createState() => _PantallaRevisionState();
}

class _PantallaRevisionState extends State<PantallaRevision> {
  /// Ancho de contenido desde el que el caso y la lista van lado a lado. Por debajo, el recorte
  /// OMR y los veredictos quedarían demasiado apretados junto a la lista.
  static const _anchoDosPaneles = 960.0;

  /// Estudiantes que se muestran antes de pedir la lista completa: 43 tarjetas seguidas alejan
  /// demasiado el final de la página en un teléfono.
  static const _limiteInicial = 8;

  var _sesion = SesionRevision.ejemplo();

  /// Posición del caso actual dentro de los pendientes.
  var _indice = 0;

  /// Sentido de la transición: el caso nuevo entra por la derecha al avanzar y por la izquierda
  /// al volver, para que el movimiento diga hacia dónde se fue.
  var _haciaAdelante = true;

  var _filtro = FiltroEstudiantes.todos;
  var _orden = OrdenNotas.mayor;
  var _verTodos = false;

  final _claveCaso = GlobalKey();

  int get _indiceActual {
    final n = _sesion.pendientes.length;
    return n == 0 ? 0 : _indice.clamp(0, n - 1);
  }

  void _irA(int indice) {
    setState(() {
      _haciaAdelante = indice > _indiceActual;
      _indice = indice;
    });
  }

  void _decidir(CasoRevision caso, Veredicto veredicto) {
    final posicion = _sesion.pendientes.indexWhere((c) => c.id == caso.id);
    final nueva = _sesion.decidir(caso, veredicto);
    final quedan = nueva.pendientes.length;
    setState(() {
      _sesion = nueva;
      _haciaAdelante = true;
      // El caso resuelto sale de la lista, así que en su posición queda el siguiente.
      _indice = quedan == 0 ? 0 : math.min(posicion, quedan - 1);
    });
    _avisarDecision(nueva.decisiones.last);
    _llevarAlCaso();
  }

  /// Deshace [decision] solo si sigue siendo la última. Así el «Deshacer» de un aviso viejo no
  /// borra una decisión posterior.
  void _deshacer(DecisionRevision decision) {
    if (_sesion.decisiones.isEmpty || !identical(_sesion.decisiones.last, decision)) return;
    final nueva = _sesion.deshacer();
    setState(() {
      _sesion = nueva;
      _haciaAdelante = false;
      _indice = math.max(0, nueva.pendientes.indexWhere((c) => c.id == decision.caso.id));
    });
    final nombre = _sesion.estudianteDe(decision.caso).nombreCompleto;
    _mostrarAviso(
      'Decisión deshecha: la pregunta ${decision.caso.pregunta} de $nombre vuelve a revisión.',
    );
    _llevarAlCaso();
  }

  void _restablecer() {
    ScaffoldMessenger.of(context).clearSnackBars();
    setState(() {
      _sesion = SesionRevision.ejemplo();
      _indice = 0;
      _haciaAdelante = false;
    });
  }

  void _avisarDecision(DecisionRevision d) {
    final nombre = _sesion.estudianteDe(d.caso).nombreCompleto;
    final opcion = d.veredicto.opcion;
    final que = switch (d.veredicto.tipo) {
      TipoVeredicto.correcta => '$opcion cuenta como correcta',
      TipoVeredicto.incorrecta => '$opcion queda como incorrecta',
      TipoVeredicto.anulada => 'la pregunta queda anulada',
    };
    final nota = d.notaAntes == d.notaDespues
        ? 'la nota se mantiene en ${formatearNota(d.notaAntes)}'
        : 'la nota pasa de ${formatearNota(d.notaAntes)} a ${formatearNota(d.notaDespues)}';
    _mostrarAviso(
      '$nombre, pregunta ${d.caso.pregunta}: $que y $nota. '
      'Es una vista de ejemplo: la decisión no se guarda.',
      alDeshacer: () => _deshacer(d),
    );
  }

  void _mostrarAviso(String texto, {VoidCallback? alDeshacer}) {
    final mensajero = ScaffoldMessenger.of(context);
    // Un aviso por decisión: si se acumularan en cola, el docente leería el de hace tres casos.
    mensajero.clearSnackBars();
    mensajero.showSnackBar(
      SnackBar(
        content: Text(texto),
        duration: const Duration(seconds: 6),
        persist: false,
        action: alDeshacer == null
            ? null
            : SnackBarAction(label: 'Deshacer', onPressed: alDeshacer),
      ),
    );
  }

  /// Tras decidir, el docente queda a la altura de los botones y el caso nuevo empieza más
  /// arriba. Se sube hasta su encabezado para que no resuelva el siguiente sin haberlo visto.
  void _llevarAlCaso() {
    final animar = !MediaQuery.disableAnimationsOf(context);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final destino = _claveCaso.currentContext;
      if (!mounted || destino == null) return;
      Scrollable.ensureVisible(
        destino,
        duration: animar ? QDuraciones.media : Duration.zero,
        curve: Curves.easeOutCubic,
        alignmentPolicy: ScrollPositionAlignmentPolicy.keepVisibleAtStart,
      );
    });
  }

  String _descripcion() {
    final n = _sesion.pendientes.length;
    final dudosas = switch (n) {
      0 => 'sin marcas dudosas por revisar',
      1 => '1 marca dudosa por revisar',
      _ => '$n marcas dudosas por revisar',
    };
    return '${_sesion.examen.nombre} · ${_sesion.estudiantes.length} estudiantes · $dudosas';
  }

  @override
  Widget build(BuildContext context) {
    return QPagina(
      children: [
        const QAvisoDatosEjemplo(
          detalle: 'La revisión se alimenta de la detección de marcas (A-02) y del recálculo de '
              'notas (A-03), que todavía no están construidos. Lo que decida aquí no se guarda.',
        ),
        const SizedBox(height: QEspacios.lg),
        QEncabezadoPantalla(
          etiqueta: 'Revisión manual',
          iconoEtiqueta: Icons.fact_check_outlined,
          titulo: 'Revisión manual y calificaciones',
          descripcion: _descripcion(),
        ),
        const SizedBox(height: QEspacios.xl),
        LayoutBuilder(
          builder: (context, restricciones) {
            final ancho = restricciones.maxWidth;
            if (ancho >= _anchoDosPaneles) {
              const flexCaso = 11;
              const flexLista = 9;
              final anchoCaso = (ancho - QEspacios.lg) * flexCaso / (flexCaso + flexLista);
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(flex: flexCaso, child: _seccionCaso(anchoCaso)),
                  const SizedBox(width: QEspacios.lg),
                  Expanded(flex: flexLista, child: _seccionEstudiantes(compacta: false)),
                ],
              );
            }
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _seccionCaso(ancho),
                const SizedBox(height: QEspacios.xxl),
                _seccionEstudiantes(compacta: ancho < 600),
              ],
            );
          },
        ),
      ],
    );
  }

  Widget _seccionCaso(double ancho) {
    final pendientes = _sesion.pendientes;
    final indice = _indiceActual;
    final animar = !MediaQuery.disableAnimationsOf(context);

    final Widget contenido;
    if (pendientes.isEmpty) {
      contenido = KeyedSubtree(key: const ValueKey('sin-casos'), child: _sinCasos());
    } else {
      final caso = pendientes[indice];
      final estudiante = _sesion.estudianteDe(caso);
      final correcto = caso.veredictoCorrecto;
      contenido = TarjetaCaso(
        key: ValueKey(caso.id),
        caso: caso,
        estudiante: estudiante,
        notaTentativa: _sesion.notaDe(estudiante),
        notaSiCorrecta: correcto == null ? null : _sesion.notaCon(caso, correcto),
        compacta: ancho < 600,
        botonesEnFila: ancho >= 720,
        alDecidir: (veredicto) => _decidir(caso, veredicto),
      );
    }

    final posicion = switch (pendientes.length) {
      0 => 'No quedan casos pendientes',
      1 => '1 de 1 pendiente',
      final n => '${indice + 1} de $n pendientes',
    };

    return Column(
      key: _claveCaso,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        QTituloSeccion(
          titulo: 'Marcas con confianza menor al $umbralConfianza %',
          descripcion: posicion,
          accion: pendientes.length > 1
              ? Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    IconButton(
                      tooltip: 'Caso anterior',
                      onPressed: indice > 0 ? () => _irA(indice - 1) : null,
                      icon: const Icon(Icons.chevron_left_outlined),
                    ),
                    IconButton(
                      tooltip: 'Caso siguiente',
                      onPressed: indice < pendientes.length - 1 ? () => _irA(indice + 1) : null,
                      icon: const Icon(Icons.chevron_right_outlined),
                    ),
                  ],
                )
              : null,
        ),
        const SizedBox(height: QEspacios.md),
        AnimatedSwitcher(
          duration: animar ? QDuraciones.media : Duration.zero,
          // Solo el caso nuevo ocupa lugar: si el saliente siguiera montado, la tarjeta tomaría
          // la altura del más alto de los dos y daría un salto al terminar.
          layoutBuilder: (actual, anteriores) => actual ?? const SizedBox.shrink(),
          transitionBuilder: (hijo, animacion) => _TransicionCaso(
            animacion: animacion,
            desplazamiento: _haciaAdelante ? 24 : -24,
            child: hijo,
          ),
          child: contenido,
        ),
        if (_sesion.decisiones.isNotEmpty) ...[
          const SizedBox(height: QEspacios.md),
          RegistroDecisiones(
            decisiones: _sesion.decisiones,
            nombreDe: (caso) => _sesion.estudianteDe(caso).nombreCompleto,
            alDeshacer: () => _deshacer(_sesion.decisiones.last),
          ),
        ],
      ],
    );
  }

  Widget _sinCasos() {
    final resueltos = _sesion.decisiones.length;
    final cuales = resueltos == 1 ? 'la marca dudosa' : 'las $resueltos marcas dudosas';
    return QTarjeta(
      child: QEstadoVacio(
        icono: Icons.task_alt_outlined,
        colorIcono: QColores.exitoTexto,
        titulo: 'No quedan marcas por revisar',
        texto: 'Usted resolvió $cuales de este parcial y las notas ya están recalculadas. '
            'Como es una vista de ejemplo, nada de esto se guarda.',
        accion: OutlinedButton.icon(
          onPressed: _restablecer,
          icon: const Icon(Icons.restart_alt_outlined),
          label: const Text('Restablecer el ejemplo'),
        ),
      ),
    );
  }

  int _comparar(FilaEstudiante a, FilaEstudiante b) {
    final porNota = _orden == OrdenNotas.mayor
        ? b.notaDecimas.compareTo(a.notaDecimas)
        : a.notaDecimas.compareTo(b.notaDecimas);
    return porNota != 0 ? porNota : a.estudiante.apellidos.compareTo(b.estudiante.apellidos);
  }

  Widget _seccionEstudiantes({required bool compacta}) {
    final textos = Theme.of(context).textTheme;
    final filas = _sesion.filas;
    final resumen = _sesion.resumen;
    final pendientes = filas.where((f) => f.pendiente).length;
    final filtradas = filas.where(_filtro.incluye).toList()..sort(_comparar);
    final visibles = _verTodos ? filtradas : filtradas.take(_limiteInicial).toList();
    final cuantos = filtradas.length == 1 ? '1 estudiante' : '${filtradas.length} estudiantes';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        QTituloSeccion(
          titulo: 'Estudiantes calificados',
          descripcion: '${resumen.calificados} listos · $pendientes por revisar',
        ),
        const SizedBox(height: QEspacios.md),
        ResumenGrupo(resumen: resumen, pendientes: pendientes, compacto: compacta),
        const SizedBox(height: QEspacios.lg),
        // Los filtros van junto a la lista que filtran: arriba de la página, en un teléfono,
        // quedarían a una pantalla de distancia de su efecto.
        Wrap(
          spacing: QEspacios.sm,
          runSpacing: QEspacios.sm,
          children: [
            for (final f in FiltroEstudiantes.values)
              FiltroPildora(
                etiqueta: f.etiqueta,
                icono: f.icono,
                colorIcono: f.colorIcono,
                conteo: filas.where(f.incluye).length,
                seleccionado: f == _filtro,
                alPresionar: () => setState(() => _filtro = f),
              ),
          ],
        ),
        const SizedBox(height: QEspacios.md),
        Wrap(
          alignment: WrapAlignment.spaceBetween,
          crossAxisAlignment: WrapCrossAlignment.center,
          spacing: QEspacios.md,
          runSpacing: QEspacios.sm,
          children: [
            Text(
              '${_filtro.etiqueta} · $cuantos',
              style: textos.labelLarge?.copyWith(color: QColores.textoSuave),
            ),
            SegmentedButton<OrdenNotas>(
              segments: const [
                ButtonSegment(
                  value: OrdenNotas.mayor,
                  label: Text('Mayor nota'),
                  icon: Icon(Icons.arrow_downward_outlined),
                ),
                ButtonSegment(
                  value: OrdenNotas.menor,
                  label: Text('Menor nota'),
                  icon: Icon(Icons.arrow_upward_outlined),
                ),
              ],
              selected: {_orden},
              onSelectionChanged: (seleccion) => setState(() => _orden = seleccion.first),
              showSelectedIcon: false,
              style: SegmentedButton.styleFrom(
                minimumSize: const Size(48, 48),
                tapTargetSize: MaterialTapTargetSize.padded,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(QRadios.control),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: QEspacios.sm + 4),
        if (filtradas.isEmpty)
          QTarjeta(
            child: QEstadoVacio(
              icono: Icons.filter_alt_off_outlined,
              titulo: 'Nadie en este filtro',
              texto: 'Por ahora no hay estudiantes en «${_filtro.etiqueta}».',
            ),
          )
        else
          for (var i = 0; i < visibles.length; i++) ...[
            if (i > 0) const SizedBox(height: QEspacios.sm),
            TarjetaEstudiante(
              key: ValueKey(visibles[i].estudiante.codigo),
              fila: visibles[i],
            ),
          ],
        if (filtradas.length > _limiteInicial) ...[
          const SizedBox(height: QEspacios.sm),
          Align(
            alignment: AlignmentDirectional.centerStart,
            child: TextButton.icon(
              onPressed: () => setState(() => _verTodos = !_verTodos),
              icon: Icon(
                _verTodos ? Icons.expand_less_outlined : Icons.expand_more_outlined,
              ),
              label: Text(_verTodos ? 'Ver menos' : 'Ver los ${filtradas.length} estudiantes'),
            ),
          ),
        ],
      ],
    );
  }
}

/// Entrada del caso nuevo: aparece y se desliza 24 px en 220 ms. Mientras entra no recibe
/// toques, para que un doble clic no resuelva el caso siguiente sin haberlo visto.
class _TransicionCaso extends AnimatedWidget {
  const _TransicionCaso({
    required Animation<double> animacion,
    required this.desplazamiento,
    required this.child,
  }) : super(listenable: animacion);

  final double desplazamiento;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final valor = (listenable as Animation<double>).value;
    final t = Curves.easeOutCubic.transform(valor);
    return IgnorePointer(
      ignoring: valor < 1,
      child: Opacity(
        opacity: t,
        child: Transform.translate(offset: Offset((1 - t) * desplazamiento, 0), child: child),
      ),
    );
  }
}
