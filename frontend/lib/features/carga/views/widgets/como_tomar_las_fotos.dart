import 'package:flutter/material.dart';

import '../../../../common/tema/tokens.dart';
import '../../../../common/widgets/q_tarjeta.dart';

/// Cómo tomar las fotos para que se lean, arriba de todo en la pantalla de carga: el docente la ve
/// antes de elegir los archivos y, desde el celular, antes de tomar la foto con la cámara que
/// ofrece el selector.
///
/// Cada punto sale de lo que mostraron las fotos del prototipo (R-05, ADR-0023): la lectura pide
/// 7,5 px/mm, así que la hoja tiene que ocupar casi toda la foto; el grafito refleja la luz directa
/// y la marca se pierde; la orientación no importa, porque la lectura la encuentra sola; y una foto
/// recomprimida, como las que pasan por WhatsApp, pierde la resolución que hace falta.
class ComoTomarLasFotos extends StatelessWidget {
  const ComoTomarLasFotos({super.key, required this.compacta});

  /// Menos relleno en columnas angostas.
  final bool compacta;

  static const _puntos = [
    (Icons.crop_free_outlined, 'La hoja entera, con las cuatro marcas negras de las esquinas'),
    (Icons.wb_sunny_outlined, 'Con luz de día, sin flash ni luz directa encima'),
    (Icons.center_focus_strong_outlined, 'Enfocada. La posición da igual'),
    (Icons.image_outlined, 'La foto original, no la que pasó por WhatsApp'),
  ];

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    return QTarjeta(
      padding: EdgeInsets.all(compacta ? QEspacios.md : QEspacios.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              const Icon(Icons.photo_camera_outlined, size: 20, color: QColores.cobaltoOscuro),
              const SizedBox(width: QEspacios.sm),
              Expanded(child: Text('Cómo tomar las fotos', style: textos.titleMedium)),
            ],
          ),
          const SizedBox(height: 2),
          Text('Con la cámara normal del celular, sin cambiar nada.', style: textos.bodySmall),
          const SizedBox(height: QEspacios.md),
          for (final (icono, texto) in _puntos) ...[
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(icono, size: 18, color: QColores.textoSuave),
                const SizedBox(width: QEspacios.sm + 4),
                Expanded(child: Text(texto, style: textos.bodyMedium)),
              ],
            ),
            if ((icono, texto) != _puntos.last) const SizedBox(height: QEspacios.sm),
          ],
        ],
      ),
    );
  }
}
