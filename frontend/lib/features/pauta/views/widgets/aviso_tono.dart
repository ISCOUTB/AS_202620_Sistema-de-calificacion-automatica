import 'package:flutter/material.dart';

import '../../../../common/tema/tokens.dart';
import '../../../../common/widgets/q_chip_estado.dart';

/// Aviso en línea con un tono semántico: sin conexión, proveedor caído, error de la solicitud.
///
/// Lleva título, ícono y texto, porque el color solo no dice qué pasó a quien no distingue el
/// naranja del rojo. Con [anunciar], el lector de pantalla lo lee en cuanto aparece: el docente
/// pidió algo y tiene que enterarse de que no llegó aunque no esté mirando ese rincón.
class AvisoTono extends StatelessWidget {
  const AvisoTono({
    super.key,
    required this.tono,
    required this.icono,
    required this.titulo,
    this.mensaje,
    this.accion,
    this.anunciar = false,
  });

  final QTono tono;
  final IconData icono;
  final String titulo;
  final String? mensaje;
  final Widget? accion;
  final bool anunciar;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    return Semantics(
      container: true,
      liveRegion: anunciar,
      child: Container(
        padding: const EdgeInsets.all(QEspacios.md),
        decoration: BoxDecoration(
          color: tono.fondo,
          borderRadius: BorderRadius.circular(QRadios.control),
          border: Border.all(color: tono.acento.withValues(alpha: 0.35)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icono, size: 20, color: tono.texto),
            const SizedBox(width: QEspacios.sm + 4),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(titulo, style: textos.labelLarge?.copyWith(color: tono.texto)),
                  if (mensaje != null) ...[
                    const SizedBox(height: QEspacios.xs),
                    Text(mensaje!, style: textos.bodyMedium?.copyWith(color: QColores.texto)),
                  ],
                  if (accion != null) ...[
                    const SizedBox(height: QEspacios.sm + 4),
                    accion!,
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
