import 'package:flutter/material.dart';

import '../tema/tokens.dart';

/// Aviso de que la vista muestra datos de ejemplo.
///
/// Las pantallas cuyo backend todavía no existe (A-02 a A-04) se muestran con datos inventados
/// para enseñar el flujo. Nada de lo que se vea ahí puede confundirse con una calificación real:
/// este aviso va arriba, a la vista, y dice qué aspecto lo va a alimentar.
class QAvisoDatosEjemplo extends StatelessWidget {
  const QAvisoDatosEjemplo({super.key, required this.detalle});

  /// Qué falta para que la vista use datos reales, por ejemplo «la detección de marcas (A-02)».
  final String detalle;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    return Semantics(
      container: true,
      label: 'Vista con datos de ejemplo. $detalle',
      child: ExcludeSemantics(
        child: Container(
          padding: const EdgeInsets.all(QEspacios.md),
          decoration: BoxDecoration(
            color: QColores.superficieAzul,
            borderRadius: BorderRadius.circular(QRadios.control),
            border: Border.all(color: QColores.superficieAzulFuerte),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(Icons.science_outlined, size: 20, color: QColores.cobaltoOscuro),
              const SizedBox(width: QEspacios.sm + 4),
              Expanded(
                child: Text.rich(
                  TextSpan(
                    children: [
                      TextSpan(
                        text: 'Vista con datos de ejemplo. ',
                        style: textos.labelLarge?.copyWith(color: QColores.navy),
                      ),
                      TextSpan(
                        text: detalle,
                        style: textos.bodyMedium?.copyWith(color: QColores.textoSuave),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
