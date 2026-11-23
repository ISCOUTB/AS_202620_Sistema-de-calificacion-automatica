import 'package:flutter/material.dart';

import '../../../../common/tema/tema.dart';
import '../../../../common/tema/tokens.dart';
import '../../data/datos_ejemplo_pauta.dart';
import '../../data/servicio_distractores.dart';
import '../../data/servicio_preguntas.dart';

/// Una fila de la lista de preguntas: una del examen de ejemplo o una que agregó el docente
/// (ADR-0030), con los distractores que tenga guardados (ADR-0029).
class FilaDeLaLista {
  const FilaDeLaLista({
    required this.enunciado,
    required this.respuestaCorrecta,
    this.ejemplo,
    this.agregada,
    this.guardados,
  });

  final String enunciado;
  final String respuestaCorrecta;
  final PreguntaEjemplo? ejemplo;
  final PreguntaDelDocente? agregada;
  final DistractoresGuardados? guardados;

  String get forma => formaDeLaPregunta(enunciado, respuestaCorrecta);

  /// Con qué se reconoce la fila: el número de la de ejemplo, o la llave de la API.
  String get clave => switch (ejemplo) {
        final PreguntaEjemplo e => '${e.numero}',
        null => agregada?.llave ?? guardados!.llave,
      };
}

/// Las preguntas del examen. Elegir una lleva su enunciado y su respuesta al generador, para que
/// el docente no tenga que copiarlas a mano.
///
/// Arriba, la fila para agregar una ([filaNueva]) y las que el docente agregó, la última primero;
/// después, las de ejemplo por su número. Al final, aparte, las que tienen distractores guardados,
/// con ellos a la vista: ahí queda lo que se guarda. Al quitarlos, la pregunta vuelve a su lugar.
///
/// Es una sola tarjeta con filas y no una tarjeta por pregunta: diez sombras seguidas pesan más
/// que la información que separan.
class ListaPreguntas extends StatelessWidget {
  const ListaPreguntas({
    super.key,
    required this.pendientes,
    this.guardadas = const [],
    required this.seleccionada,
    required this.alElegir,
    this.alQuitar,
    this.alEliminar,
    this.ocupadas = const {},
    this.filaNueva,
  });

  final List<FilaDeLaLista> pendientes;
  final List<FilaDeLaLista> guardadas;

  /// La forma de la pregunta que llenó el formulario, si el docente no lo ha editado después.
  final String? seleccionada;
  final ValueChanged<FilaDeLaLista> alElegir;

  /// Quitar lo guardado de una pregunta, y eliminar una agregada. Nulos, la lista no los ofrece.
  final ValueChanged<FilaDeLaLista>? alQuitar;
  final ValueChanged<FilaDeLaLista>? alEliminar;

  /// Las formas de las preguntas con una operación en curso: sus botones esperan.
  final Set<String> ocupadas;
  final Widget? filaNueva;

  @override
  Widget build(BuildContext context) {
    final radio = BorderRadius.circular(QRadios.tarjeta);
    Widget fila(FilaDeLaLista fila) => _FilaPregunta(
          key: ValueKey('pregunta-${fila.clave}'),
          fila: fila,
          seleccionada: fila.forma == seleccionada,
          ocupada: ocupadas.contains(fila.forma),
          alElegir: () => alElegir(fila),
          alQuitar: alQuitar == null ? null : () => alQuitar!(fila),
          alEliminar: alEliminar == null ? null : () => alEliminar!(fila),
        );
    return DecoratedBox(
      decoration: BoxDecoration(
        color: QColores.superficie,
        borderRadius: radio,
        border: Border.all(color: QColores.borde.withValues(alpha: 0.8)),
        boxShadow: QSombras.nivel1,
      ),
      child: Material(
        type: MaterialType.transparency,
        borderRadius: radio,
        clipBehavior: Clip.antiAlias,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (filaNueva case final nueva?) ...[nueva, const Divider()],
            for (final (i, pendiente) in pendientes.indexed) ...[
              if (i > 0) const Divider(),
              fila(pendiente),
            ],
            if (guardadas.isNotEmpty) ...[
              const _CabeceraGuardadas(),
              for (final (i, guardada) in guardadas.indexed) ...[
                if (i > 0) const Divider(),
                fila(guardada),
              ],
            ],
          ],
        ),
      ),
    );
  }
}

class _CabeceraGuardadas extends StatelessWidget {
  const _CabeceraGuardadas();

  @override
  Widget build(BuildContext context) {
    return Semantics(
      header: true,
      child: Container(
        color: QColores.exitoFondo,
        padding: const EdgeInsets.symmetric(horizontal: QEspacios.md, vertical: QEspacios.sm),
        child: Row(
          children: [
            const Icon(Icons.bookmark_added_outlined, size: 18, color: QColores.exitoTexto),
            const SizedBox(width: QEspacios.sm),
            Expanded(
              child: Text(
                'Con distractores guardados',
                style: Theme.of(context)
                    .textTheme
                    .labelLarge
                    ?.copyWith(color: QColores.exitoTexto, letterSpacing: 0.2),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _FilaPregunta extends StatelessWidget {
  const _FilaPregunta({
    super.key,
    required this.fila,
    required this.seleccionada,
    required this.ocupada,
    required this.alElegir,
    this.alQuitar,
    this.alEliminar,
  });

  final FilaDeLaLista fila;
  final bool seleccionada;
  final bool ocupada;
  final VoidCallback alElegir;
  final VoidCallback? alQuitar;
  final VoidCallback? alEliminar;

  @override
  Widget build(BuildContext context) {
    final ejemplo = fila.ejemplo;
    final guardados = fila.guardados;
    final agregada = fila.agregada;
    final tema = ejemplo?.tema ?? 'Agregada por usted';
    final etiqueta = ejemplo == null ? 'Pregunta agregada' : 'Pregunta ${ejemplo.numero}';
    final distractores = guardados == null
        ? ''
        : 'Distractores guardados: '
            '${guardados.distractores.map((d) => d.expresion).join(', ')}. ';

    final Widget? accion = switch ((guardados, agregada)) {
      (final DistractoresGuardados g, _) when alQuitar != null => TextButton.icon(
          key: ValueKey('quitar-${g.llave}'),
          onPressed: ocupada ? null : alQuitar,
          icon: const Icon(Icons.bookmark_remove_outlined, size: 18),
          label: const Text('Quitar'),
        ),
      (null, final PreguntaDelDocente a) when alEliminar != null => IconButton(
          key: ValueKey('eliminar-${a.llave}'),
          tooltip: 'Eliminar pregunta',
          onPressed: ocupada ? null : alEliminar,
          icon: const Icon(Icons.delete_outline, size: 20),
        ),
      _ => null,
    };

    return Material(
      color: seleccionada ? QColores.superficieAzul : QColores.superficie,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Semantics(
              button: true,
              selected: seleccionada,
              label: '$etiqueta, $tema. ${fila.enunciado} '
                  'Respuesta correcta: ${fila.respuestaCorrecta}. ${distractores}Llevar al '
                  'generador.',
              excludeSemantics: true,
              child: InkWell(
                onTap: alElegir,
                child: ConstrainedBox(
                  constraints: const BoxConstraints(minHeight: 48),
                  child: Padding(
                    padding: EdgeInsets.fromLTRB(
                      QEspacios.md,
                      QEspacios.sm + 4,
                      accion == null ? QEspacios.md : QEspacios.xs,
                      QEspacios.sm + 4,
                    ),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _Insignia(ejemplo: ejemplo, seleccionada: seleccionada),
                        const SizedBox(width: QEspacios.sm + 4),
                        Expanded(child: _Contenido(fila: fila, tema: tema)),
                        const SizedBox(width: QEspacios.sm),
                        Padding(
                          padding: const EdgeInsets.only(top: 6),
                          child: Icon(
                            seleccionada
                                ? Icons.check_circle_outlined
                                : Icons.chevron_right_outlined,
                            size: 20,
                            color: seleccionada ? QColores.cobaltoOscuro : QColores.textoTenue,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
          if (accion != null)
            Padding(
              padding: const EdgeInsets.only(top: QEspacios.xs + 2, right: QEspacios.xs),
              child: accion,
            ),
        ],
      ),
    );
  }
}

/// El número de la pregunta de ejemplo, o una persona en la que agregó el docente.
class _Insignia extends StatelessWidget {
  const _Insignia({required this.ejemplo, required this.seleccionada});

  final PreguntaEjemplo? ejemplo;
  final bool seleccionada;

  @override
  Widget build(BuildContext context) {
    final color = seleccionada ? QColores.textoSobreNavy : QColores.navy;
    return Container(
      width: 32,
      height: 32,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: seleccionada ? QColores.cobaltoOscuro : QColores.superficieAzulMedia,
        borderRadius: BorderRadius.circular(QRadios.control),
      ),
      child: switch (ejemplo) {
        final PreguntaEjemplo e => Text(
            '${e.numero}',
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: color,
                  fontFeatures: const [FontFeature.tabularFigures()],
                ),
          ),
        null => Icon(Icons.person_outline, size: 18, color: color),
      },
    );
  }
}

class _Contenido extends StatelessWidget {
  const _Contenido({required this.fila, required this.tema});

  final FilaDeLaLista fila;
  final String tema;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    final ejemplo = fila.ejemplo;
    final guardados = fila.guardados;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(tema, style: textos.labelMedium?.copyWith(color: QColores.textoSuave)),
        const SizedBox(height: 2),
        if (ejemplo != null)
          Text.rich(
            TextSpan(
              children: [
                const TextSpan(text: 'Derivada de '),
                TextSpan(text: ejemplo.funcion, style: QTexto.formula),
              ],
            ),
            style: textos.bodyMedium,
          )
        else
          Text(fila.enunciado, style: textos.bodyMedium),
        const SizedBox(height: 2),
        Text.rich(
          TextSpan(
            children: [
              TextSpan(text: 'Respuesta: ', style: textos.bodySmall),
              TextSpan(
                text: fila.respuestaCorrecta,
                style: QTexto.formula.copyWith(color: QColores.exitoTexto),
              ),
            ],
          ),
        ),
        if (guardados != null) ...[
          const SizedBox(height: QEspacios.xs + 2),
          for (final distractor in guardados.distractores)
            Padding(
              padding: const EdgeInsets.only(top: 2),
              child: Row(
                children: [
                  const Icon(Icons.circle, size: 5, color: QColores.textoSuave),
                  const SizedBox(width: QEspacios.sm),
                  Flexible(child: Text(distractor.expresion, style: QTexto.formula)),
                ],
              ),
            ),
        ],
      ],
    );
  }
}
