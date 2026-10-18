import 'package:flutter/material.dart';

import '../tema/tokens.dart';

/// Estado vacío: qué falta y cómo llenarlo. Se usa también para errores que dejan la vista sin
/// contenido, con [tono] de error.
class QEstadoVacio extends StatelessWidget {
  const QEstadoVacio({
    super.key,
    required this.icono,
    required this.titulo,
    required this.texto,
    this.accion,
    this.colorIcono = QColores.cobaltoOscuro,
  });

  final IconData icono;
  final String titulo;
  final String texto;
  final Widget? accion;
  final Color colorIcono;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: QEspacios.xl, horizontal: QEspacios.md),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 56,
            height: 56,
            decoration: const BoxDecoration(
              color: QColores.superficieAzulMedia,
              shape: BoxShape.circle,
            ),
            child: Icon(icono, color: colorIcono, size: 28),
          ),
          const SizedBox(height: QEspacios.md),
          Text(titulo, style: textos.titleMedium, textAlign: TextAlign.center),
          const SizedBox(height: QEspacios.xs),
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Text(
              texto,
              style: textos.bodyMedium?.copyWith(color: QColores.textoSuave),
              textAlign: TextAlign.center,
            ),
          ),
          if (accion != null) ...[
            const SizedBox(height: QEspacios.md),
            accion!,
          ],
        ],
      ),
    );
  }
}
