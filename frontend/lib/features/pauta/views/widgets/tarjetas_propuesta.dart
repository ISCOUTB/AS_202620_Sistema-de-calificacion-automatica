import 'package:flutter/material.dart';

import '../../../../common/tema/tema.dart';
import '../../../../common/tema/tokens.dart';
import '../../../../common/widgets/q_chip_estado.dart';
import '../../../../common/widgets/q_tarjeta.dart';
import '../../data/servicio_distractores.dart';
import 'letra_opcion.dart';

/// Lo que el docente decidió sobre una propuesta. Vive solo en esta vista: el modelo propone y
/// el docente decide (RF-07), pero todavía no hay banco de preguntas (A-04) donde guardarlo.
enum DecisionDocente { pendiente, usar, descartar }

/// La respuesta correcta que el docente escribió, como opción A.
///
/// Va primero para que cada distractor se lea contra ella: es la comparación que el sistema no
/// sabe hacer cuando la expresión es equivalente pero escrita distinto.
class TarjetaClave extends StatelessWidget {
  const TarjetaClave({super.key, required this.respuesta, required this.enunciado});

  final String respuesta;
  final String enunciado;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    const tono = QTono.exito;
    return Semantics(
      container: true,
      child: QTarjeta(
        riel: tono.acento,
        padding: const EdgeInsets.all(QEspacios.md),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const LetraOpcion(letra: 'A', tono: tono, resaltada: true),
            const SizedBox(width: QEspacios.sm + 4),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Text(
                          'Opción A · respuesta correcta',
                          style: textos.labelMedium?.copyWith(color: tono.texto),
                        ),
                      ),
                      const SizedBox(width: QEspacios.sm),
                      const QChipEstado(
                        texto: 'Clave',
                        tono: tono,
                        icono: Icons.check_circle_outlined,
                      ),
                    ],
                  ),
                  const SizedBox(height: QEspacios.xs),
                  Text(respuesta, style: QTexto.formula.copyWith(fontSize: 16)),
                  const SizedBox(height: QEspacios.xs),
                  Text(
                    enunciado,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: textos.bodySmall,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Un distractor propuesto por el modelo, con el error que representa y la decisión del
/// docente.
///
/// Mientras está pendiente lleva el riel y la insignia cian, que marcan lo que hizo la máquina.
/// Cuando el docente decide, el color pasa a ser el de su decisión: así se ve de un vistazo qué
/// falta revisar.
class TarjetaDistractor extends StatelessWidget {
  const TarjetaDistractor({
    super.key,
    required this.letra,
    required this.distractor,
    required this.decision,
    required this.alDecidir,
  });

  final String letra;
  final DistractorPropuesto distractor;
  final DecisionDocente decision;
  final ValueChanged<DecisionDocente> alDecidir;

  @override
  Widget build(BuildContext context) {
    final (tono, insignia, iconoInsignia) = switch (decision) {
      DecisionDocente.pendiente => (
          QTono.maquina,
          'Propuesta del modelo',
          Icons.auto_awesome_outlined,
        ),
      DecisionDocente.usar => (QTono.exito, 'Usted la eligió', Icons.check_circle_outlined),
      DecisionDocente.descartar => (QTono.neutro, 'Usted la descartó', Icons.block_outlined),
    };
    final descartada = decision == DecisionDocente.descartar;

    return Semantics(
      container: true,
      child: QTarjeta(
        riel: tono.acento,
        padding: const EdgeInsets.all(QEspacios.md),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                LetraOpcion(letra: letra, tono: tono),
                const SizedBox(width: QEspacios.sm + 4),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      QChipEstado(texto: insignia, tono: tono, icono: iconoInsignia),
                      const SizedBox(height: QEspacios.xs + 2),
                      Text(
                        distractor.expresion,
                        semanticsLabel: 'Opción $letra: ${distractor.expresion}',
                        style: QTexto.formula.copyWith(
                          fontSize: 16,
                          color: descartada ? QColores.textoSuave : QColores.texto,
                          decoration: descartada ? TextDecoration.lineThrough : null,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: QEspacios.sm + 4),
            _Diagnostico(error: distractor.error),
            const SizedBox(height: QEspacios.sm),
            Wrap(
              alignment: WrapAlignment.end,
              spacing: QEspacios.sm,
              runSpacing: QEspacios.xs,
              children: decision == DecisionDocente.pendiente
                  ? [
                      TextButton.icon(
                        onPressed: () => alDecidir(DecisionDocente.descartar),
                        style: TextButton.styleFrom(foregroundColor: QColores.textoSuave),
                        icon: const Icon(Icons.close_outlined, size: 18),
                        label: Text('Descartar', semanticsLabel: 'Descartar la opción $letra'),
                      ),
                      OutlinedButton.icon(
                        onPressed: () => alDecidir(DecisionDocente.usar),
                        icon: const Icon(Icons.check_outlined, size: 18),
                        label: Text('Usar', semanticsLabel: 'Usar la opción $letra'),
                      ),
                    ]
                  : [
                      TextButton.icon(
                        onPressed: () => alDecidir(DecisionDocente.pendiente),
                        icon: const Icon(Icons.undo_outlined, size: 18),
                        label: Text(
                          'Deshacer',
                          semanticsLabel: 'Deshacer la decisión sobre la opción $letra',
                        ),
                      ),
                    ],
            ),
          ],
        ),
      ),
    );
  }
}

/// El error de procedimiento que el distractor representa: es lo que lo vuelve diagnóstico y
/// no una opción incorrecta cualquiera.
class _Diagnostico extends StatelessWidget {
  const _Diagnostico({required this.error});

  final String error;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    return Container(
      padding: const EdgeInsets.all(QEspacios.sm + 4),
      decoration: BoxDecoration(
        color: QColores.superficieAzul,
        borderRadius: BorderRadius.circular(QRadios.control),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.lightbulb_outlined, size: 20, color: QColores.cianTexto),
          const SizedBox(width: QEspacios.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Diagnóstico: error que representa', style: textos.labelMedium),
                const SizedBox(height: 2),
                Text(error, style: textos.bodyMedium?.copyWith(color: QColores.textoSuave)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
