import 'package:flutter/material.dart';

import '../tema/tokens.dart';

/// Panel oscuro de autoridad: el bloque navy que el diseño usa para el análisis por pregunta, el
/// reporte de recepción y el generador de distractores. Uno por pantalla como mucho, para que
/// conserve su peso.
class QPanelNavy extends StatelessWidget {
  const QPanelNavy({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(QEspacios.lg),
  });

  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(QRadios.tarjeta),
        gradient: const LinearGradient(
          begin: AlignmentDirectional.topStart,
          end: AlignmentDirectional.bottomEnd,
          colors: [Color(0xFF13294B), QColores.navy],
        ),
        boxShadow: QSombras.nivel3,
      ),
      child: DefaultTextStyle.merge(
        style: const TextStyle(color: QColores.textoSobreNavy),
        child: IconTheme.merge(
          data: const IconThemeData(color: QColores.textoSobreNavy),
          child: child,
        ),
      ),
    );
  }
}
