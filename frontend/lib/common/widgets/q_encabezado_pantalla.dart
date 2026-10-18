import 'package:flutter/material.dart';

import '../tema/tema.dart';
import '../tema/tokens.dart';

/// Encabezado de cada pantalla: una etiqueta de contexto (la única etiqueta en mayúsculas de la
/// pantalla), el título y una línea que dice qué se hace aquí.
class QEncabezadoPantalla extends StatelessWidget {
  const QEncabezadoPantalla({
    super.key,
    required this.titulo,
    this.etiqueta,
    this.iconoEtiqueta,
    this.descripcion,
    this.extremo,
  });

  final String titulo;
  final String? etiqueta;
  final IconData? iconoEtiqueta;
  final String? descripcion;

  /// Algo pequeño a la derecha de la etiqueta, como el periodo académico.
  final Widget? extremo;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (etiqueta != null || extremo != null)
          Padding(
            padding: const EdgeInsetsDirectional.only(bottom: QEspacios.sm),
            child: Row(
              children: [
                if (iconoEtiqueta != null) ...[
                  Icon(iconoEtiqueta, size: 18, color: QColores.cobaltoOscuro),
                  const SizedBox(width: QEspacios.sm),
                ],
                if (etiqueta != null)
                  Expanded(
                    child: Text(
                      etiqueta!.toUpperCase(),
                      style: QTexto.etiqueta.copyWith(color: QColores.cobaltoOscuro),
                    ),
                  )
                else
                  const Spacer(),
                if (extremo != null) extremo!,
              ],
            ),
          ),
        Text(titulo, style: textos.displaySmall),
        if (descripcion != null) ...[
          const SizedBox(height: QEspacios.xs),
          Text(
            descripcion!,
            style: textos.bodyLarge?.copyWith(color: QColores.textoSuave),
          ),
        ],
      ],
    );
  }
}
