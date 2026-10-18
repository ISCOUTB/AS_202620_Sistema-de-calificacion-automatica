import 'package:flutter/material.dart';

import '../../../../common/tema/tema.dart';
import '../../../../common/tema/tokens.dart';

/// Nota fija sobre el límite conocido del generador (R-11).
///
/// La API descarta las propuestas que repiten la respuesta correcta letra por letra, pero no
/// sabe que `sin(2x)` y `2·sin(x)·cos(x)` son la misma derivada. Un distractor así sería una
/// segunda respuesta correcta en la hoja, y solo el docente puede detectarlo. Por eso la nota
/// está siempre a la vista, y no solo cuando llega un resultado.
///
/// Va en gris y no en naranja a propósito: no es una alerta de algo que acaba de pasar, sino
/// una regla de uso, y no debe competir con los avisos de conexión o de error.
class NotaEquivalencias extends StatelessWidget {
  const NotaEquivalencias({super.key});

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    return Container(
      padding: const EdgeInsets.all(QEspacios.sm + 4),
      decoration: BoxDecoration(
        color: QColores.superficieSuave,
        borderRadius: BorderRadius.circular(QRadios.control),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.rule_outlined, size: 20, color: QColores.advertenciaTexto),
          const SizedBox(width: QEspacios.sm + 4),
          Expanded(
            child: Text.rich(
              TextSpan(
                children: [
                  TextSpan(
                    text: 'Revise las propuestas antes de usarlas. ',
                    style: textos.labelLarge?.copyWith(color: QColores.texto),
                  ),
                  const TextSpan(
                    text: 'El sistema descarta las que repiten la respuesta correcta, pero no '
                        'detecta una expresión equivalente escrita distinto, como ',
                  ),
                  TextSpan(text: 'sin(2x)', style: QTexto.formula.copyWith(fontSize: 13)),
                  const TextSpan(text: ' frente a '),
                  TextSpan(
                    text: '2·sin(x)·cos(x)',
                    style: QTexto.formula.copyWith(fontSize: 13),
                  ),
                  const TextSpan(text: '.'),
                ],
              ),
              style: textos.bodyMedium?.copyWith(color: QColores.textoSuave),
            ),
          ),
        ],
      ),
    );
  }
}
