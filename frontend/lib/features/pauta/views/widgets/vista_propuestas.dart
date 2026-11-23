import 'package:flutter/material.dart';

import '../../../../common/tema/tokens.dart';
import '../../../../common/widgets/q_chip_estado.dart';
import '../../../../common/widgets/q_estado_vacio.dart';
import '../../../../common/widgets/q_titulo_seccion.dart';
import '../../data/servicio_distractores.dart';
import 'aviso_tono.dart';
import 'seccion_descartadas.dart';
import 'tarjetas_propuesta.dart';

/// El resultado de una solicitud: la clave, los distractores con la decisión del docente sobre
/// cada uno, y los que la regla descartó.
///
/// Los guardados para la pregunta van primero, ya elegidos (ADR-0029); después, las propuestas
/// que no repiten a uno guardado. Si solo hay guardados, la vista se titula así.
///
/// Frente al diseño no hay «Frecuencia: 38 %»: la frecuencia con que los estudiantes eligen un
/// distractor solo existe después de aplicar el examen, y aquí todavía no se ha aplicado.
class VistaPropuestas extends StatelessWidget {
  const VistaPropuestas({
    super.key,
    required this.solicitud,
    required this.resultado,
    required this.distractores,
    required this.decisiones,
    required this.alDecidir,
    required this.alPedirOtras,
    required this.distractoresPorPregunta,
    this.guardadas = const [],
    this.regenerando = const {},
    this.avisos = const {},
    this.alRegenerar,
    this.ofreceGuardar = false,
    this.alGuardar,
    this.guardando = false,
    this.mensajeGuardado,
    this.errorGuardado,
  });

  final SolicitudDistractores solicitud;

  /// De aquí salen las descartadas por la regla; las tarjetas salen de [distractores].
  final ResultadoDistractores resultado;
  final List<DistractorPropuesto> distractores;
  final List<DecisionDocente> decisiones;
  final void Function(int indice, DecisionDocente decision) alDecidir;

  /// Nulo cuando no se puede volver a pedir (sin conexión).
  final VoidCallback? alPedirOtras;

  /// Cuántos distractores caben en una pregunta del examen.
  final int distractoresPorPregunta;

  /// Por tarjeta, si está guardada para esta pregunta.
  final List<bool> guardadas;

  /// Las tarjetas que esperan una propuesta nueva, y lo que pasó si no llegó.
  final Set<int> regenerando;
  final Map<int, String> avisos;

  /// Nulo cuando no se puede regenerar (sin conexión).
  final void Function(int indice)? alRegenerar;

  /// Si la pantalla puede guardar (ADR-0029). Sin eso, la nota dice que se copian al examen.
  final bool ofreceGuardar;

  /// Nulo mientras no haya nada que guardar: ninguna elegida, más de las que caben, o las
  /// elegidas ya son las guardadas.
  final VoidCallback? alGuardar;
  final bool guardando;
  final String? mensajeGuardado;
  final String? errorGuardado;

  /// La letra de cada distractor: la A es la respuesta correcta.
  static String letraPara(int indice) => String.fromCharCode('B'.codeUnitAt(0) + indice);

  bool _guardada(int i) => i < guardadas.length && guardadas[i];

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    final descartadas = resultado.descartados;
    final nGuardadas =
        [for (var i = 0; i < distractores.length; i++) _guardada(i)].where((g) => g).length;
    final usadas = decisiones.where((d) => d == DecisionDocente.usar).length;
    final elegidas = usadas - nGuardadas;
    final rechazadas = decisiones.where((d) => d == DecisionDocente.descartar).length;

    // Al elegir en la lista una pregunta con distractores guardados, llegan solo ellos.
    final soloGuardadas = nGuardadas > 0 &&
        nGuardadas == distractores.length &&
        descartadas.isEmpty &&
        regenerando.isEmpty;

    final resumen = [
      if (!soloGuardadas) _contar(distractores.length - nGuardadas, 'propuesta', 'propuestas'),
      if (nGuardadas > 0) _contar(nGuardadas, 'guardada', 'guardadas'),
      if (elegidas > 0) _contar(elegidas, 'elegida', 'elegidas'),
      if (rechazadas > 0) _contar(rechazadas, 'descartada por usted', 'descartadas por usted'),
    ].join(' · ');

    final anuncio = soloGuardadas
        ? 'Distractores guardados para esta pregunta: $nGuardadas.'
        : 'Llegaron ${_contar(distractores.length, 'propuesta', 'propuestas')}'
            '${descartadas.isEmpty ? '' : ' y ${_contar(descartadas.length, 'descartada', 'descartadas')} por el sistema'}.';

    return Semantics(
      container: true,
      liveRegion: true,
      label: anuncio,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          QTituloSeccion(
            titulo: soloGuardadas ? 'Distractores guardados' : 'Propuestas del modelo',
            descripcion: resumen,
          ),
          const SizedBox(height: QEspacios.md),
          TarjetaClave(respuesta: solicitud.respuestaCorrecta, enunciado: solicitud.enunciado),
          for (final (i, distractor) in distractores.indexed) ...[
            const SizedBox(height: QEspacios.sm + 4),
            TarjetaDistractor(
              key: ValueKey('distractor-$i'),
              letra: letraPara(i),
              distractor: distractor,
              decision: decisiones[i],
              alDecidir: (decision) => alDecidir(i, decision),
              guardada: _guardada(i),
              alRegenerar: alRegenerar == null ? null : () => alRegenerar!(i),
              regenerando: regenerando.contains(i),
              aviso: avisos[i],
            ),
          ],
          if (distractores.isEmpty)
            const QEstadoVacio(
              icono: Icons.block_outlined,
              titulo: 'No quedó ninguna propuesta',
              texto: 'El sistema descartó todas las que llegaron; abajo está el motivo. Puede '
                  'pedir otras o escribir los distractores a mano.',
            ),
          if (usadas > distractoresPorPregunta) ...[
            const SizedBox(height: QEspacios.sm + 4),
            AvisoTono(
              tono: QTono.advertencia,
              icono: Icons.warning_amber_outlined,
              titulo: 'Eligió más de los que caben',
              mensaje: 'Cada pregunta tiene una respuesta correcta y '
                  '$distractoresPorPregunta distractores. Descarte '
                  '${usadas - distractoresPorPregunta} antes de '
                  '${ofreceGuardar ? 'guardarlos' : 'llevarlos al examen'}.',
              anunciar: true,
            ),
          ],
          const SizedBox(height: QEspacios.md),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(Icons.info_outlined, size: 18, color: QColores.textoSuave),
              const SizedBox(width: QEspacios.sm),
              Expanded(
                child: Text(
                  ofreceGuardar
                      ? 'Ninguna propuesta entra al examen sin su aprobación. Las que guarde '
                          'quedan con la pregunta, al final de la lista de preguntas.'
                      : 'Ninguna propuesta entra al examen sin su aprobación. Las que elija no '
                          'quedan guardadas aquí; cópielas a su examen.',
                  style: textos.bodySmall,
                ),
              ),
            ],
          ),
          if (descartadas.isNotEmpty) ...[
            const SizedBox(height: QEspacios.md),
            SeccionDescartadas(descartadas: descartadas),
          ],
          const SizedBox(height: QEspacios.md),
          Wrap(
            spacing: QEspacios.sm,
            runSpacing: QEspacios.sm,
            children: [
              if (ofreceGuardar)
                FilledButton.icon(
                  key: const Key('boton-guardar-distractores'),
                  onPressed: guardando ? null : alGuardar,
                  icon: guardando
                      ? const SizedBox.square(
                          dimension: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.bookmark_add_outlined, size: 20),
                  label: Text(guardando ? 'Guardando…' : 'Guardar distractores'),
                ),
              OutlinedButton.icon(
                key: const Key('boton-pedir-otras'),
                onPressed: alPedirOtras,
                icon: const Icon(Icons.refresh_outlined, size: 20),
                label: const Text('Pedir otras propuestas'),
              ),
            ],
          ),
          if (mensajeGuardado case final mensaje?) ...[
            const SizedBox(height: QEspacios.sm),
            Semantics(
              liveRegion: true,
              child: Row(
                children: [
                  Icon(Icons.check_circle_outlined, size: 18, color: QTono.exito.texto),
                  const SizedBox(width: QEspacios.xs + 2),
                  Expanded(
                    child: Text(
                      mensaje,
                      style: textos.bodyMedium?.copyWith(color: QTono.exito.texto),
                    ),
                  ),
                ],
              ),
            ),
          ],
          if (errorGuardado case final error?) ...[
            const SizedBox(height: QEspacios.sm),
            AvisoTono(
              key: const Key('aviso-guardar'),
              tono: QTono.error,
              icono: Icons.error_outline_outlined,
              titulo: 'No se pudieron guardar',
              mensaje: error,
              anunciar: true,
            ),
          ],
        ],
      ),
    );
  }

  static String _contar(int n, String uno, String varios) => n == 1 ? '1 $uno' : '$n $varios';
}
