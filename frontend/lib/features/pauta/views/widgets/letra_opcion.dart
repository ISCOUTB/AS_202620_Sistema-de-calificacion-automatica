import 'package:flutter/material.dart';

import '../../../../common/tema/tokens.dart';
import '../../../../common/widgets/q_chip_estado.dart';

/// La letra de una opción (A, B, C...), como la burbuja de la hoja OMR.
///
/// Va con radio de control (8) y no en círculo: el sistema de diseño reserva la píldora para la
/// confianza OMR y los filtros. [resaltada] la rellena con el color de texto del tono, que
/// conserva 4,5:1 con la letra blanca; los acentos plenos (verde, cian) no llegan.
class LetraOpcion extends StatelessWidget {
  const LetraOpcion({
    super.key,
    required this.letra,
    this.tono = QTono.neutro,
    this.resaltada = false,
  });

  final String letra;
  final QTono tono;
  final bool resaltada;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 36,
      height: 36,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: resaltada ? tono.texto : tono.fondo,
        borderRadius: BorderRadius.circular(QRadios.control),
        border: resaltada ? null : Border.all(color: tono.acento.withValues(alpha: 0.35)),
      ),
      child: Text(
        letra,
        style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: resaltada ? QColores.textoSobreNavy : tono.texto,
              fontWeight: FontWeight.w700,
            ),
      ),
    );
  }
}
