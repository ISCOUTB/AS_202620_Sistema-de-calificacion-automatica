import 'dart:async';

import 'package:flutter/material.dart';

import '../../../../common/tema/tokens.dart';
import '../../../../common/widgets/q_tarjeta.dart';
import '../../../../common/widgets/q_titulo_seccion.dart';
import '../../../carga/data/servicio_examenes.dart';
import '../../../revision/data/servicio_revision.dart' show fechaLegible;
import '../../data/servicio_clave.dart';

/// La clave de un examen (A-04, ADR-0026): escribirla en la cuadrícula o pegar las respuestas,
/// guardarla y habilitarla. Mientras ninguna hoja del examen tenga nota se puede cambiar; después
/// queda fija, porque las notas no se recalculan solas.
class TarjetaClaveDelExamen extends StatefulWidget {
  const TarjetaClaveDelExamen({
    super.key,
    required this.consultarClave,
    required this.guardarClave,
    required this.habilitarClave,
    this.listarExamenes,
    this.alCambiar,
  });

  final Future<ClaveDelExamen?> Function(String examenId) consultarClave;
  final Future<ClaveDelExamen> Function(String examenId, List<String> respuestas) guardarClave;
  final Future<ClaveDelExamen> Function(String examenId) habilitarClave;
  final Future<List<ExamenConClave>> Function()? listarExamenes;

  /// Avisa que se guardó o se habilitó una clave, para que la carga refresque su lista.
  final VoidCallback? alCambiar;

  @override
  State<TarjetaClaveDelExamen> createState() => _TarjetaClaveDelExamenState();
}

class _TarjetaClaveDelExamenState extends State<TarjetaClaveDelExamen> {
  final _examen = TextEditingController();
  final _numero = TextEditingController(text: '$maximoDePreguntas');
  final _pegado = TextEditingController();
  Timer? _espera;

  List<ExamenConClave> _examenes = const [];
  String? _examenVisto;
  ClaveDelExamen? _guardada;
  bool _cargando = false;
  bool _ocupado = false;
  String? _errorPegado;
  final List<String?> _respuestas = List.filled(maximoDePreguntas, null);

  int get _preguntas {
    final valor = int.tryParse(_numero.text.trim());
    if (valor == null) return maximoDePreguntas;
    return valor.clamp(1, maximoDePreguntas);
  }

  List<String?> get _visibles => _respuestas.sublist(0, _preguntas);

  bool get _cambiable => _guardada?.sePuedeCambiar ?? true;

  bool get _cambio {
    final guardada = _guardada;
    if (guardada == null) return _visibles.any((r) => r != null);
    return _visibles.length != guardada.respuestas.length ||
        [for (final (i, r) in _visibles.indexed) r != guardada.respuestas[i]].any((x) => x);
  }

  int? get _primeraFaltante {
    for (final (i, r) in _visibles.indexed) {
      if (r == null) return i + 1;
    }
    return null;
  }

  @override
  void initState() {
    super.initState();
    _examen.addListener(_alCambiarElExamen);
    _numero.addListener(() => setState(() {}));
    widget.listarExamenes?.call().then((lista) {
      if (mounted) setState(() => _examenes = lista);
    }, onError: (_) {});
  }

  @override
  void dispose() {
    _espera?.cancel();
    _examen.dispose();
    _numero.dispose();
    _pegado.dispose();
    super.dispose();
  }

  void _alCambiarElExamen() {
    final examen = _examen.text.trim();
    if (examen == _examenVisto) return;
    _espera?.cancel();
    setState(() {
      _examenVisto = null;
      _guardada = null;
    });
    if (identificadorValido(examen)) {
      _espera = Timer(const Duration(milliseconds: 400), () => _cargar(examen));
    }
  }

  Future<void> _cargar(String examen) async {
    setState(() {
      _cargando = true;
      _examenVisto = examen;
    });
    try {
      final clave = await widget.consultarClave(examen);
      if (!mounted || _examenVisto != examen) return;
      setState(() => _mostrar(clave));
    } on ExcepcionDeClave catch (error) {
      if (mounted) _avisar(error.mensaje);
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  void _mostrar(ClaveDelExamen? clave) {
    _guardada = clave;
    _respuestas.fillRange(0, maximoDePreguntas, null);
    final respuestas = clave?.respuestas ?? const [];
    for (final (i, r) in respuestas.indexed) {
      _respuestas[i] = r;
    }
    _numero.text = '${respuestas.isEmpty ? maximoDePreguntas : respuestas.length}';
  }

  Future<void> _llenar() async {
    final List<String> respuestas;
    try {
      respuestas = respuestasDesdeTexto(_pegado.text);
    } on FormatException catch (error) {
      setState(() => _errorPegado = error.message);
      return;
    }
    setState(() => _errorPegado = null);
    final confirmado = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('¿Son estas las respuestas?'),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('Asegúrese de que estas son las respuestas correctas de cada pregunta:'),
              const SizedBox(height: QEspacios.md),
              Wrap(
                spacing: QEspacios.md,
                runSpacing: QEspacios.xs,
                children: [
                  for (final (i, r) in respuestas.indexed) Text('${i + 1}. $r'),
                ],
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Corregir'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Llenar la cuadrícula'),
          ),
        ],
      ),
    );
    if (confirmado != true || !mounted) return;
    setState(() {
      _respuestas.fillRange(0, maximoDePreguntas, null);
      for (final (i, r) in respuestas.indexed) {
        _respuestas[i] = r;
      }
      _numero.text = '${respuestas.length}';
      _pegado.clear();
    });
  }

  Future<void> _guardar() async {
    final examen = _examenVisto!;
    setState(() => _ocupado = true);
    try {
      final guardada = await widget.guardarClave(examen, [for (final r in _visibles) r!]);
      if (!mounted) return;
      setState(() => _guardada = guardada);
      _avisar('Clave guardada. Habilítela para calificar con ella.');
      widget.alCambiar?.call();
    } on ExcepcionDeClave catch (error) {
      if (mounted) _avisar(error.mensaje);
    } finally {
      if (mounted) setState(() => _ocupado = false);
    }
  }

  Future<void> _habilitar() async {
    final examen = _examenVisto!;
    final confirmado = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('¿Habilitar la clave de $examen?'),
        content: const Text(
          'Las hojas que se lean de aquí en adelante se califican con ella, y la habilitación queda '
          'a su nombre. Las que ya se leyeron no reciben nota.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Habilitar'),
          ),
        ],
      ),
    );
    if (confirmado != true || !mounted) return;
    setState(() => _ocupado = true);
    try {
      final habilitada = await widget.habilitarClave(examen);
      if (!mounted) return;
      setState(() => _guardada = habilitada);
      _avisar('Clave habilitada.');
      widget.alCambiar?.call();
    } on ExcepcionDeClave catch (error) {
      if (mounted) _avisar(error.mensaje);
    } finally {
      if (mounted) setState(() => _ocupado = false);
    }
  }

  void _avisar(String texto) =>
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(SnackBar(content: Text(texto)));

  String? get _estado {
    if (_cargando) return 'Buscando la clave…';
    if (_examenVisto == null) return null;
    final guardada = _guardada;
    if (guardada == null) return 'Sin clave registrada.';
    final base = guardada.habilitada
        ? 'Habilitada por ${guardada.habilitadaPor} el ${fechaLegible(guardada.habilitadaEn!)}.'
        : 'Guardada, sin habilitar.';
    return guardada.sePuedeCambiar
        ? base
        : '$base Ya hay hojas calificadas con ella: no se puede cambiar.';
  }

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    final examen = _examen.text.trim();
    final invalido = examen.isNotEmpty && !identificadorValido(examen);
    final lista = _examenVisto != null && !_cargando;
    final editable = lista && _cambiable && !_ocupado;
    final faltante = _primeraFaltante;
    final puedeGuardar = editable && faltante == null && _cambio;
    final guardada = _guardada;
    final puedeHabilitar =
        lista && !_ocupado && guardada != null && !guardada.habilitada && !_cambio;
    final estado = _estado;

    return QTarjeta(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const QTituloSeccion(titulo: 'Clave del examen'),
          const SizedBox(height: QEspacios.md),
          Wrap(
            spacing: QEspacios.md,
            runSpacing: QEspacios.md,
            children: [
              SizedBox(
                width: 280,
                child: TextField(
                  controller: _examen,
                  decoration: InputDecoration(
                    labelText: 'Examen',
                    hintText: 'Por ejemplo, CALC-2026-03',
                    prefixIcon: const Icon(Icons.assignment_outlined),
                    errorText: invalido
                        ? 'Solo letras sin acento, dígitos, guiones y guiones bajos.'
                        : null,
                    errorMaxLines: 2,
                  ),
                ),
              ),
              SizedBox(
                width: 120,
                child: TextField(
                  controller: _numero,
                  enabled: editable,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: 'Preguntas'),
                ),
              ),
            ],
          ),
          if (_examenes.isNotEmpty) ...[
            const SizedBox(height: QEspacios.sm),
            Wrap(
              spacing: QEspacios.sm,
              runSpacing: QEspacios.xs,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                Text('Con clave:', style: textos.bodySmall),
                for (final e in _examenes)
                  ActionChip(
                    label: Text(e.examenId),
                    onPressed: () => _examen.text = e.examenId,
                  ),
              ],
            ),
          ],
          if (estado != null) ...[
            const SizedBox(height: QEspacios.md),
            Text(estado, key: const Key('estado-clave'), style: textos.bodyMedium),
          ],
          if (lista) ...[
            const SizedBox(height: QEspacios.md),
            Wrap(
              spacing: QEspacios.sm,
              runSpacing: QEspacios.sm,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                SizedBox(
                  width: 280,
                  child: TextField(
                    controller: _pegado,
                    enabled: editable,
                    decoration: InputDecoration(
                      labelText: 'Pegar las respuestas',
                      hintText: 'ABCDABCD…',
                      errorText: _errorPegado,
                      errorMaxLines: 2,
                    ),
                  ),
                ),
                OutlinedButton(onPressed: editable ? _llenar : null, child: const Text('Llenar')),
              ],
            ),
            const SizedBox(height: QEspacios.md),
            Wrap(
              spacing: QEspacios.md,
              runSpacing: QEspacios.sm,
              children: [
                for (var n = 1; n <= _preguntas; n++)
                  SizedBox(
                    width: 232,
                    child: Row(
                      children: [
                        SizedBox(width: 28, child: Text('$n', style: textos.labelLarge)),
                        Expanded(
                          child: SegmentedButton<String>(
                            key: ValueKey('respuesta-$n'),
                            segments: [
                              for (final o in opcionesDeLaHoja)
                                ButtonSegment(value: o, label: Text(o)),
                            ],
                            selected: {if (_respuestas[n - 1] case final r?) r},
                            emptySelectionAllowed: true,
                            showSelectedIcon: false,
                            style: const ButtonStyle(visualDensity: VisualDensity.compact),
                            onSelectionChanged: editable
                                ? (elegidas) => setState(
                                      () => _respuestas[n - 1] =
                                          elegidas.isEmpty ? null : elegidas.first,
                                    )
                                : null,
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
            if (faltante != null && _visibles.any((r) => r != null)) ...[
              const SizedBox(height: QEspacios.sm),
              Text(
                'Falta la respuesta de la pregunta $faltante.',
                style: textos.bodySmall?.copyWith(color: QColores.advertenciaTexto),
              ),
            ],
            const SizedBox(height: QEspacios.md),
            Wrap(
              spacing: QEspacios.sm,
              runSpacing: QEspacios.sm,
              children: [
                FilledButton(
                  onPressed: puedeGuardar ? _guardar : null,
                  child: const Text('Guardar clave'),
                ),
                OutlinedButton(
                  onPressed: puedeHabilitar ? _habilitar : null,
                  child: const Text('Habilitar'),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}
