import 'package:flutter/material.dart';

import '../../../../common/tema/tokens.dart';
import '../../../../common/widgets/q_tarjeta.dart';

/// Tarjeta del examen de destino: el identificador al que quedan asociadas las hojas.
///
/// Es un campo de texto y no una lista porque la API todavía no publica los exámenes: el módulo
/// que los registra (A-04) aún no existe, y un desplegable con opciones inventadas haría creer que
/// el sistema ya los conoce.
///
/// El diseño original traía aquí un interruptor de «validación estricta». No está, porque esa
/// validación no se puede apagar: el backend revisa los primeros bytes de cada archivo siempre.
/// Un interruptor que no hace nada enseña algo falso; una línea fija dice lo que sí ocurre.
class TarjetaExamen extends StatelessWidget {
  const TarjetaExamen({
    super.key,
    required this.controlador,
    required this.habilitada,
    required this.compacta,
    required this.alCambiar,
  });

  final TextEditingController controlador;

  /// Falso mientras se sube un lote: cambiar el examen a mitad de camino no cambiaría el destino
  /// de lo que ya va en camino, y solo confundiría.
  final bool habilitada;

  /// Menos relleno en columnas angostas, donde cada píxel de ancho cuenta.
  final bool compacta;

  final ValueChanged<String> alCambiar;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    return QTarjeta(
      padding: EdgeInsets.all(compacta ? QEspacios.md : QEspacios.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('Examen de destino', style: textos.titleMedium),
          const SizedBox(height: 2),
          Text(
            'Las hojas quedan asociadas a este examen.',
            style: textos.bodySmall,
          ),
          const SizedBox(height: QEspacios.md),
          TextField(
            controller: controlador,
            enabled: habilitada,
            onChanged: alCambiar,
            autocorrect: false,
            textInputAction: TextInputAction.done,
            decoration: const InputDecoration(
              labelText: 'Identificador del examen',
              helperText: 'Por ejemplo, CALC-2026-02',
              prefixIcon: Icon(Icons.assignment_outlined),
            ),
          ),
          const SizedBox(height: QEspacios.md),
          Container(
            padding: const EdgeInsets.all(QEspacios.sm + 4),
            decoration: BoxDecoration(
              color: QColores.superficieAzul,
              borderRadius: BorderRadius.circular(QRadios.control),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(
                  Icons.verified_user_outlined,
                  size: 20,
                  color: QColores.cobaltoOscuro,
                ),
                const SizedBox(width: QEspacios.sm + 4),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Se revisa el contenido de cada archivo, no solo su extensión.',
                        style: textos.labelLarge,
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'Un archivo que no sea un JPG, PNG o PDF real se rechaza, y el reporte '
                        'dice por qué.',
                        style: textos.bodySmall,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
