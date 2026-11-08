import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';

import '../../../common/tema/tokens.dart';
import '../../../common/widgets/q_chip_estado.dart';
import '../../../common/widgets/q_encabezado_pantalla.dart';
import '../../../common/widgets/q_estado_vacio.dart';
import '../../../common/widgets/q_pagina.dart';
import '../../../common/widgets/q_tarjeta.dart';
import '../../../common/widgets/q_titulo_seccion.dart';
import '../../carga/data/servicio_examenes.dart';
import '../../carga/data/servicio_resultados.dart';
import '../../carga/views/widgets/tarjeta_examen.dart';
import '../data/servicio_revision.dart';

/// La revisión manual (RF-08): las hojas de un examen con preguntas que la lectura no pudo
/// decidir, y en cada pregunta el recorte de su fila para que el docente diga qué marcó el
/// estudiante. El sistema decide con la clave si es correcto y recalcula la nota.
///
/// La pantalla no recibe la clave ni el código del estudiante: las rutas son públicas hasta A-05.
/// El nombre que escribe el docente queda con cada decisión (RF-10), sin verificar hasta entonces.
class PantallaRevision extends StatefulWidget {
  const PantallaRevision({
    super.key,
    this.listarExamenes,
    this.consultarRevision,
    this.guardarRevision,
    this.urlDelRecorte,
    this.nombresDeHojas,
    this.examenPedido,
    this.alGuardar,
  });

  final Future<List<ExamenConClave>> Function()? listarExamenes;
  final Future<RevisionDelExamen> Function(String examenId)? consultarRevision;
  final Future<ResultadoDeHoja> Function(
    String examenId,
    String hojaId,
    String por,
    Map<int, String?> opciones,
  )? guardarRevision;

  /// Dónde pedir el recorte de una pregunta. Sin él, la pregunta se muestra sin imagen.
  final String Function(String examenId, String hojaId, int numero)? urlDelRecorte;

  /// El nombre de archivo de cada hoja subida en esta sesión, por `hoja_id`.
  final ValueListenable<Map<String, String>>? nombresDeHojas;

  /// El examen que pidió revisar la pantalla de carga.
  final ValueListenable<String?>? examenPedido;

  /// Avisa que se guardó una revisión, para que el reporte de carga refresque las notas.
  final VoidCallback? alGuardar;

  @override
  State<PantallaRevision> createState() => _PantallaRevisionState();
}

/// «Ninguna» en el selector: el estudiante dejó la fila en blanco o marcó más de una.
const _ninguna = '-';

class _PantallaRevisionState extends State<PantallaRevision> {
  final _examen = TextEditingController();
  final _nombre = TextEditingController();

  List<ExamenConClave>? _examenes;
  bool _cargandoExamenes = false;
  bool _fallaExamenes = false;

  /// El examen cuya revisión está a la vista, o la que se está pidiendo.
  String? _examenVisto;
  RevisionDelExamen? _revision;
  bool _cargandoRevision = false;
  String? _errorRevision;
  Timer? _espera;

  String? _hojaElegida;

  /// Lo que el docente eligió y todavía no guardó, por hoja y por pregunta.
  final Map<String, Map<int, String>> _elecciones = {};
  bool _guardando = false;

  @override
  void initState() {
    super.initState();
    final pedido = widget.examenPedido?.value;
    if (pedido != null) _examen.text = pedido;
    _examen.addListener(_alCambiarElExamen);
    _nombre.addListener(_redibujar);
    widget.examenPedido?.addListener(_alPedirExamen);
    widget.nombresDeHojas?.addListener(_redibujar);
    if (widget.listarExamenes != null) {
      _cargandoExamenes = true;
      _pedirExamenes();
    } else if (pedido != null) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _alCambiarElExamen());
    }
  }

  @override
  void dispose() {
    _espera?.cancel();
    widget.examenPedido?.removeListener(_alPedirExamen);
    widget.nombresDeHojas?.removeListener(_redibujar);
    _examen.dispose();
    _nombre.dispose();
    super.dispose();
  }

  void _redibujar() {
    if (mounted) setState(() {});
  }

  void _alPedirExamen() {
    final pedido = widget.examenPedido?.value;
    if (pedido != null && pedido != _examen.text) _examen.text = pedido;
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
    _alCambiarElExamen();
  }

  void _volverAPedirExamenes() {
    if (widget.listarExamenes == null || _cargandoExamenes) return;
    setState(() => _cargandoExamenes = true);
    _pedirExamenes();
  }

  /// El examen elegido: de la lista, con su nombre exacto, o el escrito si no hay lista.
  String get _examenId {
    final lista = _examenes;
    if (lista == null) return _examen.text.trim();
    return examenElegido(_examen.text, lista)?.examenId ?? '';
  }

  /// Pide la revisión del examen elegido, un momento después de que deja de cambiar: escrito a
  /// mano, cada letra sería una consulta.
  void _alCambiarElExamen() {
    if (!mounted) return;
    // El desplegable cambia el texto también mientras se construye la pantalla.
    if (SchedulerBinding.instance.schedulerPhase == SchedulerPhase.persistentCallbacks) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _alCambiarElExamen());
      return;
    }
    final examen = _examenId;
    if (examen == _examenVisto) {
      setState(() {});
      return;
    }
    _espera?.cancel();
    setState(() {
      _examenVisto = examen.isEmpty ? null : examen;
      _revision = null;
      _errorRevision = null;
      _hojaElegida = null;
      _elecciones.clear();
    });
    if (examen.isNotEmpty) {
      _espera = Timer(const Duration(milliseconds: 300), () => _cargarRevision(examen));
    }
  }

  Future<void> _cargarRevision(String examen) async {
    final consultar = widget.consultarRevision;
    if (consultar == null) return;
    setState(() {
      _cargandoRevision = true;
      _errorRevision = null;
    });
    try {
      final revision = await consultar(examen);
      if (!mounted || examen != _examenVisto) return;
      setState(() {
        _revision = revision;
        final elegida = _hojaElegida;
        final sigue = elegida != null && revision.hojas.any((h) => h.hojaId == elegida);
        _hojaElegida = sigue ? elegida : _primeraPorRevisar(revision)?.hojaId;
      });
    } catch (error) {
      if (!mounted || examen != _examenVisto) return;
      setState(() => _errorRevision = error is ExcepcionDeRevision
          ? error.mensaje
          : 'No se pudo pedir la revisión.');
    } finally {
      if (mounted) setState(() => _cargandoRevision = false);
    }
  }

  static HojaEnRevision? _primeraPorRevisar(RevisionDelExamen revision) {
    for (final hoja in revision.hojas) {
      if (hoja.pendientes > 0) return hoja;
    }
    return revision.hojas.isEmpty ? null : revision.hojas.first;
  }

  HojaEnRevision? get _hoja {
    final revision = _revision;
    if (revision == null) return null;
    for (final hoja in revision.hojas) {
      if (hoja.hojaId == _hojaElegida) return hoja;
    }
    return null;
  }

  String _nombreDe(HojaEnRevision hoja) {
    final nombre = widget.nombresDeHojas?.value[hoja.hojaId];
    if (nombre != null) return nombre;
    final indice = _revision?.hojas.indexOf(hoja) ?? 0;
    return 'Hoja ${indice + 1}';
  }

  Map<int, String> _eleccionesDe(HojaEnRevision hoja) =>
      _elecciones.putIfAbsent(hoja.hojaId, () => {});

  /// Lo elegido que cambia lo que ya estaba guardado.
  Map<int, String?> _cambios(HojaEnRevision hoja) {
    final elegidas = _eleccionesDe(hoja);
    return {
      for (final pregunta in hoja.preguntas)
        if (elegidas[pregunta.numero] case final elegida?)
          if (!pregunta.resuelta || elegida != (pregunta.opcionResuelta ?? _ninguna))
            pregunta.numero: elegida == _ninguna ? null : elegida,
    };
  }

  Future<void> _guardar(HojaEnRevision hoja) async {
    final guardar = widget.guardarRevision;
    final examen = _examenVisto;
    final cambios = _cambios(hoja);
    if (guardar == null || examen == null || cambios.isEmpty) return;
    setState(() => _guardando = true);
    try {
      final resultado = await guardar(examen, hoja.hojaId, _nombre.text.trim(), cambios);
      if (!mounted) return;
      _eleccionesDe(hoja).clear();
      final nota = resultado.notaEnDecimas == null ? '' : notaLegible(resultado.notaEnDecimas!);
      _avisar(resultado.provisional ? 'Guardado. Nota provisional $nota.' : 'Guardado. Nota $nota.');
      widget.alGuardar?.call();
      await _cargarRevision(examen);
      // Si en esta hoja no queda nada, se pasa a la siguiente con preguntas por revisar.
      final actual = _hoja;
      if (mounted && actual != null && actual.pendientes == 0 && _revision != null) {
        final siguiente = _primeraPorRevisar(_revision!);
        if (siguiente != null && siguiente.pendientes > 0) {
          setState(() => _hojaElegida = siguiente.hojaId);
        }
      }
    } catch (error) {
      if (mounted) {
        _avisar(error is ExcepcionDeRevision ? error.mensaje : 'No se guardó. Vuelva a intentarlo.');
      }
    } finally {
      if (mounted) setState(() => _guardando = false);
    }
  }

  void _avisar(String texto) =>
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(SnackBar(content: Text(texto)));

  @override
  Widget build(BuildContext context) {
    return QPagina(
      children: [
        const QEncabezadoPantalla(
          etiqueta: 'Revisión manual',
          iconoEtiqueta: Icons.rate_review_outlined,
          titulo: 'Revisar preguntas dudosas',
          descripcion: 'Elija lo que marcó el estudiante en las preguntas que el sistema no pudo '
              'leer con seguridad.',
        ),
        const SizedBox(height: QEspacios.lg),
        LayoutBuilder(
          builder: (context, restricciones) {
            final ancha = restricciones.maxWidth >= QAnchos.dosColumnas;
            final examen = TarjetaExamen(
              controlador: _examen,
              habilitada: !_guardando,
              compacta: !ancha,
              examenes: _examenes,
              cargando: _cargandoExamenes,
              alReintentar: _fallaExamenes ? _volverAPedirExamenes : null,
            );
            final nombre = QTarjeta(
              padding: EdgeInsets.all(ancha ? QEspacios.lg : QEspacios.md),
              child: TextField(
                controller: _nombre,
                enabled: !_guardando,
                textCapitalization: TextCapitalization.words,
                decoration: const InputDecoration(
                  labelText: 'Su nombre',
                  helperText: 'Queda registrado con cada decisión.',
                  prefixIcon: Icon(Icons.person_outline),
                ),
              ),
            );
            if (!ancha) {
              return Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [examen, const SizedBox(height: QEspacios.md), nombre],
              );
            }
            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(child: examen),
                const SizedBox(width: QEspacios.lg),
                Expanded(child: nombre),
              ],
            );
          },
        ),
        const SizedBox(height: QEspacios.xl),
        _contenido(),
      ],
    );
  }

  Widget _contenido() {
    final revision = _revision;
    if (_examenVisto == null) {
      return const QTarjeta(
        child: QEstadoVacio(
          icono: Icons.rate_review_outlined,
          titulo: 'Elija un examen',
          texto: 'Aquí verá las hojas con preguntas por revisar.',
        ),
      );
    }
    if (_errorRevision case final error?) {
      return QTarjeta(
        child: QEstadoVacio(
          icono: Icons.cloud_off_outlined,
          titulo: 'No se pudo pedir la revisión',
          texto: error,
          accion: OutlinedButton.icon(
            onPressed: () => _cargarRevision(_examenVisto!),
            icon: const Icon(Icons.refresh_outlined),
            label: const Text('Volver a intentar'),
          ),
        ),
      );
    }
    if (revision == null) {
      return const LinearProgressIndicator(semanticsLabel: 'Cargando la revisión');
    }
    if (revision.hojas.isEmpty) {
      return const QTarjeta(
        child: QEstadoVacio(
          icono: Icons.task_alt_outlined,
          titulo: 'No hay preguntas por revisar',
          texto: 'Las hojas leídas de este examen no tienen dudas.',
        ),
      );
    }

    return LayoutBuilder(
      builder: (context, restricciones) {
        final ancha = restricciones.maxWidth >= QAnchos.dosColumnas;
        final lista = _ListaDeHojas(
          hojas: revision.hojas,
          elegida: _hojaElegida,
          nombreDe: _nombreDe,
          alElegir: (hoja) => setState(() => _hojaElegida = hoja.hojaId),
        );
        final hoja = _hoja;
        final detalle = hoja == null ? const SizedBox.shrink() : _detalle(hoja, ancha: ancha);
        if (!ancha) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [lista, const SizedBox(height: QEspacios.xl), detalle],
          );
        }
        return Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(flex: 4, child: lista),
            const SizedBox(width: QEspacios.lg),
            Expanded(flex: 7, child: detalle),
          ],
        );
      },
    );
  }

  Widget _detalle(HojaEnRevision hoja, {required bool ancha}) {
    final textos = Theme.of(context).textTheme;
    final elegidas = _eleccionesDe(hoja);
    final cambios = _cambios(hoja);
    final sinNombre = _nombre.text.trim().isEmpty;
    final puedeGuardar = !_guardando && cambios.isNotEmpty && !sinNombre;
    final String indicacion;
    if (_guardando) {
      indicacion = 'Guardando…';
    } else if (cambios.isEmpty) {
      indicacion = 'Elija lo que marcó el estudiante.';
    } else if (sinNombre) {
      indicacion = 'Escriba su nombre para guardar.';
    } else {
      indicacion = cambios.length == 1
          ? 'Se guardará 1 pregunta.'
          : 'Se guardarán ${cambios.length} preguntas.';
    }
    final nota = notaLegible(hoja.notaEnDecimas);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        QTituloSeccion(
          titulo: _nombreDe(hoja),
          descripcion: hoja.provisional ? 'Nota provisional $nota' : 'Nota $nota',
        ),
        if (!hoja.codigoCompleto) ...[
          const SizedBox(height: QEspacios.sm),
          Text(
            'El código del estudiante quedó incompleto: la nota seguirá provisional.',
            style: textos.bodySmall?.copyWith(color: QColores.advertenciaTexto),
          ),
        ],
        const SizedBox(height: QEspacios.md),
        for (final pregunta in hoja.preguntas) ...[
          _TarjetaPregunta(
            pregunta: pregunta,
            elegida: elegidas[pregunta.numero] ??
                (pregunta.resuelta ? (pregunta.opcionResuelta ?? _ninguna) : null),
            recorte: pregunta.conRecorte && widget.urlDelRecorte != null && _examenVisto != null
                ? widget.urlDelRecorte!(_examenVisto!, hoja.hojaId, pregunta.numero)
                : null,
            habilitada: !_guardando,
            alElegir: (opcion) => setState(() => elegidas[pregunta.numero] = opcion),
          ),
          const SizedBox(height: QEspacios.sm + 4),
        ],
        const SizedBox(height: QEspacios.sm),
        Wrap(
          alignment: WrapAlignment.spaceBetween,
          crossAxisAlignment: WrapCrossAlignment.center,
          spacing: QEspacios.md,
          runSpacing: QEspacios.sm,
          children: [
            Text(indicacion, style: textos.bodyMedium?.copyWith(color: QColores.textoSuave)),
            FilledButton.icon(
              onPressed: puedeGuardar ? () => _guardar(hoja) : null,
              icon: const Icon(Icons.save_outlined),
              label: const Text('Guardar'),
            ),
          ],
        ),
        if (_guardando || _cargandoRevision) ...[
          const SizedBox(height: QEspacios.sm),
          const LinearProgressIndicator(semanticsLabel: 'Guardando'),
        ],
      ],
    );
  }
}

/// Las hojas del examen, primero las que tienen preguntas por revisar.
class _ListaDeHojas extends StatelessWidget {
  const _ListaDeHojas({
    required this.hojas,
    required this.elegida,
    required this.nombreDe,
    required this.alElegir,
  });

  final List<HojaEnRevision> hojas;
  final String? elegida;
  final String Function(HojaEnRevision) nombreDe;
  final ValueChanged<HojaEnRevision> alElegir;

  @override
  Widget build(BuildContext context) {
    final ordenadas = [
      ...hojas.where((h) => h.pendientes > 0),
      ...hojas.where((h) => h.pendientes == 0),
    ];
    final porRevisar = hojas.where((h) => h.pendientes > 0).length;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        QTituloSeccion(
          titulo: 'Hojas',
          descripcion: porRevisar == 0
              ? 'Todas revisadas'
              : porRevisar == 1
                  ? '1 por revisar'
                  : '$porRevisar por revisar',
        ),
        const SizedBox(height: QEspacios.sm + 4),
        QTarjeta(
          padding: EdgeInsets.zero,
          child: Column(
            children: [
              for (var i = 0; i < ordenadas.length; i++) ...[
                if (i > 0) const Divider(height: 1),
                _FilaDeHoja(
                  hoja: ordenadas[i],
                  nombre: nombreDe(ordenadas[i]),
                  elegida: ordenadas[i].hojaId == elegida,
                  alElegir: () => alElegir(ordenadas[i]),
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }
}

class _FilaDeHoja extends StatelessWidget {
  const _FilaDeHoja({
    required this.hoja,
    required this.nombre,
    required this.elegida,
    required this.alElegir,
  });

  final HojaEnRevision hoja;
  final String nombre;
  final bool elegida;
  final VoidCallback alElegir;

  @override
  Widget build(BuildContext context) {
    final pendientes = hoja.pendientes;
    final nota = notaLegible(hoja.notaEnDecimas);
    return ListTile(
      selected: elegida,
      selectedTileColor: QColores.superficieAzul,
      onTap: alElegir,
      leading: Icon(
        pendientes > 0 ? Icons.rate_review_outlined : Icons.task_alt_outlined,
        color: pendientes > 0 ? QColores.advertenciaTexto : QColores.exitoTexto,
      ),
      title: Text(nombre, maxLines: 2, overflow: TextOverflow.ellipsis),
      subtitle: Text(
        pendientes == 0
            ? 'Revisada'
            : pendientes == 1
                ? '1 pregunta por revisar'
                : '$pendientes preguntas por revisar',
      ),
      trailing: QChipEstado(
        texto: nota,
        tono: hoja.provisional ? QTono.advertencia : QTono.exito,
      ),
    );
  }
}

/// Una pregunta en revisión: el recorte de su fila, lo que se midió y la elección del docente.
class _TarjetaPregunta extends StatelessWidget {
  const _TarjetaPregunta({
    required this.pregunta,
    required this.elegida,
    required this.recorte,
    required this.habilitada,
    required this.alElegir,
  });

  final PreguntaEnRevision pregunta;
  final String? elegida;
  final String? recorte;
  final bool habilitada;
  final ValueChanged<String> alElegir;

  static const _opciones = ['A', 'B', 'C', 'D'];

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    final recorte = this.recorte;
    // Sin el riel de color de otras tarjetas: el riel mide la altura antes de tiempo, y en un
    // teléfono el selector de opciones no cabía.
    return QTarjeta(
      padding: const EdgeInsets.all(QEspacios.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(child: Text('Pregunta ${pregunta.numero}', style: textos.titleSmall)),
              if (pregunta.resuelta)
                const QChipEstado(
                  texto: 'Resuelta',
                  tono: QTono.exito,
                  icono: Icons.check_circle_outlined,
                ),
            ],
          ),
          if (recorte != null) ...[
            const SizedBox(height: QEspacios.sm),
            ClipRRect(
              borderRadius: BorderRadius.circular(QRadios.control),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxHeight: 96),
                child: Image.network(
                  recorte,
                  fit: BoxFit.contain,
                  alignment: Alignment.centerLeft,
                  semanticLabel: 'La fila de la pregunta ${pregunta.numero} en la hoja',
                  errorBuilder: (context, error, pila) => const SizedBox.shrink(),
                ),
              ),
            ),
          ],
          const SizedBox(height: QEspacios.sm),
          Text(_lectura(pregunta), style: textos.bodySmall),
          const SizedBox(height: QEspacios.sm + 4),
          SegmentedButton<String>(
            segments: [
              for (final opcion in _opciones)
                ButtonSegment(value: opcion, label: Text(opcion)),
              // En un teléfono cada opción tiene unos 65 px: «Ninguna» se achica un poco en vez
              // de partirse en dos líneas.
              const ButtonSegment(
                value: _ninguna,
                label: FittedBox(fit: BoxFit.scaleDown, child: Text('Ninguna', maxLines: 1)),
              ),
            ],
            selected: {if (elegida != null) elegida!},
            emptySelectionAllowed: true,
            showSelectedIcon: false,
            style: SegmentedButton.styleFrom(
              padding: const EdgeInsets.symmetric(horizontal: QEspacios.xs),
            ),
            onSelectionChanged: habilitada
                ? (seleccion) {
                    if (seleccion.isNotEmpty) alElegir(seleccion.first);
                  }
                : null,
          ),
          if (pregunta.resuelta && pregunta.resueltaPor != null) ...[
            const SizedBox(height: QEspacios.xs),
            Text('Resuelta por ${pregunta.resueltaPor}.', style: textos.bodySmall),
          ],
        ],
      ),
    );
  }

  /// «Se ve: C tenue (58 %)». Las vacías no se nombran.
  static String _lectura(PreguntaEnRevision pregunta) {
    final marcadas = [
      for (final burbuja in pregunta.burbujas)
        if (burbuja.tipo != 'vacia')
          '${burbuja.opcion} ${_tipo(burbuja.tipo)} (${burbuja.confianza} %)',
    ];
    return marcadas.isEmpty ? 'Se ven todas vacías.' : 'Se ve: ${marcadas.join(', ')}.';
  }

  static String _tipo(String tipo) => switch (tipo) {
        'tenue' => 'tenue',
        'borron' => 'borrón',
        'completa' => 'llena',
        _ => tipo,
      };
}
