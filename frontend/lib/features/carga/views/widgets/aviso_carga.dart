import 'package:flutter/material.dart';

import '../../../../common/tema/tokens.dart';
import '../../../../common/widgets/q_chip_estado.dart';

/// Aviso en línea de la pantalla de carga: la falta de conexión, una carga que no se completó o
/// un reporte que no cuadra con el lote.
///
/// Es una región viva para los lectores de pantalla: aparece como consecuencia de algo que el
/// docente hizo (o de la API que se cayó), y nadie va a ir a buscarlo si no se anuncia. El título
/// usa la variante oscura del tono, porque el color pleno no alcanza 4,5:1 sobre su fondo.
class AvisoCarga extends StatelessWidget {
  const AvisoCarga({
    super.key,
    required this.tono,
    required this.icono,
    required this.titulo,
    required this.texto,
    this.detalle,
  });

  final QTono tono;
  final IconData icono;
  final String titulo;
  final String texto;

  /// Qué pasa con los archivos o qué puede hacer el docente, en letra más pequeña.
  final String? detalle;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    return Semantics(
      container: true,
      liveRegion: true,
      label: [titulo, texto, if (detalle != null) detalle!].join('. '),
      child: ExcludeSemantics(
        child: Container(
          padding: const EdgeInsets.all(QEspacios.md),
          decoration: BoxDecoration(
            color: tono.fondo,
            borderRadius: BorderRadius.circular(QRadios.control),
            border: Border.all(color: tono.acento.withValues(alpha: 0.4)),
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
                    const SizedBox(height: 2),
                    Text(texto, style: textos.bodyMedium),
                    if (detalle != null) ...[
                      const SizedBox(height: QEspacios.xs),
                      Text(detalle!, style: textos.bodySmall),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
