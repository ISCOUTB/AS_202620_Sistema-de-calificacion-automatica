import 'package:flutter/material.dart';

import '../../../../common/tema/tokens.dart';
import '../../../../common/widgets/q_panel_navy.dart';

/// Cabecera del generador de distractores, el único bloque navy de la pantalla.
///
/// El ícono va en cian y no en cobalto: el cobalto es el color de lo que el docente puede
/// presionar, y esto no es un botón; el cian marca lo que hace la máquina, y el generador es la
/// única parte del sistema con modelo de lenguaje (ADR-0005).
class CabeceraGenerador extends StatelessWidget {
  const CabeceraGenerador({super.key});

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    return QPanelNavy(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              color: QColores.navyMedio,
              borderRadius: BorderRadius.circular(QRadios.control),
              border: Border.all(color: QColores.cian.withValues(alpha: 0.45)),
            ),
            child: const Icon(Icons.auto_awesome_outlined, color: QColores.cian, size: 22),
          ),
          const SizedBox(width: QEspacios.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Semantics(
                  header: true,
                  child: Text(
                    'Generador de distractores diagnósticos',
                    style: textos.titleLarge?.copyWith(color: QColores.textoSobreNavy),
                  ),
                ),
                const SizedBox(height: QEspacios.xs),
                Text(
                  'Propone opciones incorrectas ligadas a un error de procedimiento. Usted '
                  'decide cuáles usar.',
                  style: textos.bodyMedium?.copyWith(color: QColores.textoSobreNavySuave),
                ),
                const SizedBox(height: QEspacios.sm),
                // A-06 es opcional: el sistema califica igual sin esta ayuda, y el docente
                // debe saberlo antes de depender de ella.
                Text(
                  'Es opcional: el examen funciona igual si usted escribe los distractores a '
                  'mano.',
                  style: textos.bodySmall?.copyWith(color: QColores.textoSobreNavySuave),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
