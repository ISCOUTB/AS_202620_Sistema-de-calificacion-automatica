import 'package:flutter/material.dart';

import '../tema/tema.dart';
import '../tema/tokens.dart';

/// Los tonos semánticos del sistema de diseño.
enum QTono {
  /// Validado, recibido, confianza alta.
  exito(QColores.exitoTexto, QColores.exitoFondo, QColores.exito),

  /// Requiere revisión humana: confianza baja, marca dudosa.
  advertencia(QColores.advertenciaTexto, QColores.advertenciaFondo, QColores.advertencia),

  /// Rechazado, ilegible, incorrecto.
  error(QColores.errorTexto, QColores.errorFondo, QColores.error),

  /// Información e interacción.
  info(QColores.cobaltoOscuro, QColores.superficieAzulFuerte, QColores.cobalto),

  /// Lo que hizo la máquina: lectura OMR o una propuesta del modelo.
  maquina(QColores.cianTexto, Color(0xFFE6FAFF), QColores.cian),

  /// Sin estado particular.
  neutro(QColores.textoSuave, QColores.superficieSuave, QColores.textoTenue);

  const QTono(this.texto, this.fondo, this.acento);

  final Color texto;
  final Color fondo;

  /// Color pleno, para íconos, rieles y barras (no para texto pequeño).
  final Color acento;
}

/// Insignia de estado. Siempre lleva texto, y casi siempre un ícono: el color solo no basta
/// para quien no distingue el verde del rojo.
class QChipEstado extends StatelessWidget {
  const QChipEstado({
    super.key,
    required this.texto,
    this.tono = QTono.neutro,
    this.icono,
    this.pildora = false,
  });

  final String texto;
  final QTono tono;
  final IconData? icono;

  /// Las píldoras se reservan para la confianza OMR y los filtros; el resto va con radio 8.
  final bool pildora;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: tono.fondo,
        borderRadius: BorderRadius.circular(pildora ? QRadios.pildora : QRadios.control),
        border: Border.all(color: tono.acento.withValues(alpha: 0.25)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icono != null) ...[
            Icon(icono, size: 14, color: tono.texto),
            const SizedBox(width: QEspacios.xs),
          ],
          Flexible(
            child: Text(
              texto,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: tono.texto,
                    fontFeatures: const [FontFeature.tabularFigures()],
                    fontFamily: familiaTexto,
                  ),
            ),
          ),
        ],
      ),
    );
  }
}
