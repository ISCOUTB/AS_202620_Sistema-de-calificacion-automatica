import 'package:flutter/material.dart';

import '../tema/tokens.dart';

/// Título de una sección dentro de una pantalla, con una acción opcional alineada a la derecha.
class QTituloSeccion extends StatelessWidget {
  const QTituloSeccion({super.key, required this.titulo, this.descripcion, this.accion});

  final String titulo;
  final String? descripcion;
  final Widget? accion;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(titulo, style: textos.headlineSmall),
              if (descripcion != null) ...[
                const SizedBox(height: 2),
                Text(
                  descripcion!,
                  style: textos.bodyMedium?.copyWith(color: QColores.textoSuave),
                ),
              ],
            ],
          ),
        ),
        if (accion != null) accion!,
      ],
    );
  }
}
