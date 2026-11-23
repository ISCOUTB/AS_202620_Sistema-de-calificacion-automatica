import 'package:flutter/material.dart';

import '../../../../common/tema/tokens.dart';

/// La fila que abre «+» arriba en la lista de preguntas (ADR-0030): el enunciado, la respuesta
/// correcta y «Agregar». Después de agregar queda abierta y vacía, para seguir con otra.
class FilaNuevaPregunta extends StatefulWidget {
  const FilaNuevaPregunta({super.key, required this.alAgregar, required this.alCerrar});

  /// Agrega la pregunta y devuelve el motivo si no se pudo, o nulo si quedó en la lista.
  final Future<String?> Function(String enunciado, String respuestaCorrecta) alAgregar;
  final VoidCallback alCerrar;

  @override
  State<FilaNuevaPregunta> createState() => _FilaNuevaPreguntaState();
}

class _FilaNuevaPreguntaState extends State<FilaNuevaPregunta> {
  final _enunciado = TextEditingController();
  final _respuesta = TextEditingController();
  final _focoEnunciado = FocusNode();
  bool _agregando = false;
  String? _error;

  @override
  void dispose() {
    _enunciado.dispose();
    _respuesta.dispose();
    _focoEnunciado.dispose();
    super.dispose();
  }

  Future<void> _agregar() async {
    final enunciado = _enunciado.text.trim();
    final respuesta = _respuesta.text.trim();
    if (enunciado.isEmpty || respuesta.isEmpty) {
      setState(() => _error = 'Escriba el enunciado y la respuesta correcta.');
      return;
    }
    setState(() {
      _agregando = true;
      _error = null;
    });
    final error = await widget.alAgregar(enunciado, respuesta);
    if (!mounted) return;
    setState(() {
      _agregando = false;
      _error = error;
      if (error == null) {
        _enunciado.clear();
        _respuesta.clear();
      }
    });
    if (error == null) _focoEnunciado.requestFocus();
  }

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    return Padding(
      padding: const EdgeInsets.fromLTRB(QEspacios.md, QEspacios.sm, QEspacios.xs, QEspacios.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(child: Text('Pregunta nueva', style: textos.titleSmall)),
              IconButton(
                key: const Key('boton-cerrar-nueva-pregunta'),
                tooltip: 'Cerrar',
                onPressed: widget.alCerrar,
                icon: const Icon(Icons.close, size: 20),
              ),
            ],
          ),
          Padding(
            padding: const EdgeInsets.only(right: QEspacios.sm + 4),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                TextField(
                  key: const Key('campo-nueva-enunciado'),
                  controller: _enunciado,
                  focusNode: _focoEnunciado,
                  autofocus: true,
                  minLines: 1,
                  maxLines: 3,
                  textInputAction: TextInputAction.next,
                  decoration: const InputDecoration(
                    labelText: 'Enunciado',
                    hintText: 'Calcule la derivada de f(x) = x·ln(x).',
                  ),
                ),
                const SizedBox(height: QEspacios.sm),
                TextField(
                  key: const Key('campo-nueva-respuesta'),
                  controller: _respuesta,
                  textInputAction: TextInputAction.done,
                  onSubmitted: (_) => _agregando ? null : _agregar(),
                  decoration: const InputDecoration(
                    labelText: 'Respuesta correcta',
                    hintText: 'ln(x) + 1',
                  ),
                ),
                if (_error case final error?) ...[
                  const SizedBox(height: QEspacios.sm),
                  Semantics(
                    liveRegion: true,
                    child: Text(
                      error,
                      style: textos.bodySmall?.copyWith(color: QColores.errorTexto),
                    ),
                  ),
                ],
                const SizedBox(height: QEspacios.sm + 4),
                Align(
                  alignment: Alignment.centerLeft,
                  child: FilledButton.icon(
                    key: const Key('boton-agregar-pregunta'),
                    onPressed: _agregando ? null : _agregar,
                    icon: const Icon(Icons.add, size: 20),
                    label: Text(_agregando ? 'Agregando…' : 'Agregar'),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
