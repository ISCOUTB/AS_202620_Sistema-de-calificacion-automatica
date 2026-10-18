import 'package:flutter/material.dart';

import '../tema/tokens.dart';

/// Superficie de nivel 1: tarjeta blanca con borde fino y sombra teñida de navy.
///
/// [riel] dibuja la franja de 4 px a la izquierda que el sistema de diseño usa para el estado de
/// un ítem (verde validado, naranja por revisar, navy sin asignar). Si [alPresionar] no es nulo,
/// la tarjeta entera es un objetivo táctil y sube a nivel 2 mientras se presiona.
class QTarjeta extends StatelessWidget {
  const QTarjeta({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(QEspacios.lg),
    this.riel,
    this.color = QColores.superficie,
    this.alPresionar,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final Color? riel;
  final Color color;
  final VoidCallback? alPresionar;

  @override
  Widget build(BuildContext context) {
    final radio = BorderRadius.circular(QRadios.tarjeta);
    Widget contenido = Padding(padding: padding, child: child);

    if (riel != null) {
      contenido = IntrinsicHeight(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Container(width: 4, color: riel),
            Expanded(child: contenido),
          ],
        ),
      );
    }

    return DecoratedBox(
      decoration: BoxDecoration(
        color: color,
        borderRadius: radio,
        border: Border.all(color: QColores.borde.withValues(alpha: 0.8)),
        boxShadow: QSombras.nivel1,
      ),
      child: Material(
        type: MaterialType.transparency,
        borderRadius: radio,
        clipBehavior: Clip.antiAlias,
        child: alPresionar == null
            ? contenido
            : InkWell(onTap: alPresionar, child: contenido),
      ),
    );
  }
}
