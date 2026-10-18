import 'package:flutter/material.dart';

import '../../../../common/tema/tokens.dart';
import '../../../../common/widgets/q_chip_estado.dart';
import '../../../../common/widgets/q_estado_vacio.dart';
import '../../../../common/widgets/q_titulo_seccion.dart';
import '../../data/servicio_distractores.dart';
import 'aviso_tono.dart';
import 'seccion_descartadas.dart';
import 'tarjetas_propuesta.dart';

/// El resultado de una solicitud: la clave, los distractores que pasaron la regla con la
/// decisión del docente sobre cada uno, y los que la regla descartó.
///
/// Frente al diseño no hay «Frecuencia: 38 %»: la frecuencia con que los estudiantes eligen un
/// distractor solo existe después de aplicar el examen, y aquí todavía no se ha aplicado.
class VistaPropuestas extends StatelessWidget {
  const VistaPropuestas({
    super.key,
    required this.solicitud,
    required this.resultado,
    required this.decisiones,
    required this.alDecidir,
    required this.alPedirOtras,
    required this.distractoresPorPregunta,
  });

  final SolicitudDistractores solicitud;
  final ResultadoDistractores resultado;
  final List<DecisionDocente> decisiones;
  final void Function(int indice, DecisionDocente decision) alDecidir;

  /// Nulo cuando no se puede volver a pedir (sin conexión).
  final VoidCallback? alPedirOtras;

  /// Cuántos distractores caben en una pregunta del examen.
  final int distractoresPorPregunta;

  /// La letra de cada distractor: la A es la respuesta correcta.
  static String letraPara(int indice) => String.fromCharCode('B'.codeUnitAt(0) + indice);

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    final distractores = resultado.distractores;
    final descartadas = resultado.descartados;
    final elegidas = decisiones.where((d) => d == DecisionDocente.usar).length;
    final rechazadas = decisiones.where((d) => d == DecisionDocente.descartar).length;

    final resumen = [
      _contar(distractores.length, 'propuesta', 'propuestas'),
      if (elegidas > 0) _contar(elegidas, 'elegida', 'elegidas'),
      if (rechazadas > 0) _contar(rechazadas, 'descartada por usted', 'descartadas por usted'),
    ].join(' · ');

    final anuncio = 'Llegaron ${_contar(distractores.length, 'propuesta', 'propuestas')}'
        '${descartadas.isEmpty ? '' : ' y ${_contar(descartadas.length, 'descartada', 'descartadas')} por el sistema'}.';

    return Semantics(
      container: true,
      liveRegion: true,
      label: anuncio,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          QTituloSeccion(titulo: 'Propuestas del modelo', descripcion: resumen),
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
            ),
          ],
          if (distractores.isEmpty)
            const QEstadoVacio(
              icono: Icons.block_outlined,
              titulo: 'No quedó ninguna propuesta',
              texto: 'El sistema descartó todas las que llegaron; abajo está el motivo. Puede '
                  'pedir otras o escribir los distractores a mano.',
            ),
          if (elegidas > distractoresPorPregunta) ...[
            const SizedBox(height: QEspacios.sm + 4),
            AvisoTono(
              tono: QTono.advertencia,
              icono: Icons.warning_amber_outlined,
              titulo: 'Eligió más de los que caben',
              mensaje: 'Cada pregunta tiene una respuesta correcta y '
                  '$distractoresPorPregunta distractores. Descarte '
                  '${elegidas - distractoresPorPregunta} antes de llevarlos al examen.',
              anunciar: true,
            ),
          ],
          const SizedBox(height: QEspacios.md),
          // La decisión es del docente (RF-07) y por ahora solo vive en esta vista.
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(Icons.info_outlined, size: 18, color: QColores.textoSuave),
              const SizedBox(width: QEspacios.sm),
              Expanded(
                child: Text(
                  'Usar y Descartar son su decisión: ninguna propuesta entra al examen hasta '
                  'que usted la acepte y habilite la clave. Por ahora la decisión no se guarda, '
                  'porque el banco de preguntas (A-04) todavía no existe.',
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
          Align(
            alignment: AlignmentDirectional.centerStart,
            child: OutlinedButton.icon(
              key: const Key('boton-pedir-otras'),
              onPressed: alPedirOtras,
              icon: const Icon(Icons.refresh_outlined, size: 20),
              label: const Text('Pedir otras propuestas'),
            ),
          ),
        ],
      ),
    );
  }

  static String _contar(int n, String uno, String varios) => n == 1 ? '1 $uno' : '$n $varios';
}
