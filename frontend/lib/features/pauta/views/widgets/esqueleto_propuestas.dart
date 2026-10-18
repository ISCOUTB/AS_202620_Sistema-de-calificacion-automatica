import 'package:flutter/material.dart';

import '../../../../common/tema/tokens.dart';
import '../../../../common/widgets/q_tarjeta.dart';

/// Lo que se ve mientras el modelo responde: la forma de las tarjetas que van a llegar.
///
/// Un círculo girando no dice qué viene ni cuánto puede tardar. Las siluetas anticipan la
/// clave y una tarjeta por distractor pedido, y la línea de arriba da la expectativa real
/// (medido: 2 a 3 s; el backend corta a los 20 s). Son estáticas: el sistema de diseño no anima
/// nada en bucle.
class EsqueletoPropuestas extends StatelessWidget {
  const EsqueletoPropuestas({super.key, required this.cantidad});

  final int cantidad;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    return Column(
      key: const Key('esqueleto-propuestas'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Semantics(
          liveRegion: true,
          container: true,
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(Icons.hourglass_top_outlined, size: 20, color: QColores.cianTexto),
              const SizedBox(width: QEspacios.sm),
              Expanded(
                child: Text(
                  'Pidiendo propuestas al modelo. Suele tardar unos segundos; si el proveedor '
                  'no responde en 20 s, la solicitud se cancela.',
                  style: textos.bodyMedium?.copyWith(color: QColores.textoSuave),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: QEspacios.md),
        ExcludeSemantics(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const _Silueta(clave: true),
              for (var i = 0; i < cantidad; i++) ...[
                const SizedBox(height: QEspacios.sm + 4),
                const _Silueta(clave: false),
              ],
            ],
          ),
        ),
      ],
    );
  }
}

/// La silueta de una tarjeta de resultado: letra, expresión y, en los distractores, el cuadro
/// del diagnóstico y las dos acciones.
class _Silueta extends StatelessWidget {
  const _Silueta({required this.clave});

  final bool clave;

  @override
  Widget build(BuildContext context) {
    return QTarjeta(
      riel: QColores.borde,
      padding: const EdgeInsets.all(QEspacios.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              const _Bloque(ancho: 36, alto: 36),
              const SizedBox(width: QEspacios.sm + 4),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _Barra(fraccion: clave ? 0.4 : 0.3, alto: 10),
                    const SizedBox(height: QEspacios.sm),
                    _Barra(fraccion: clave ? 0.55 : 0.65, alto: 14),
                  ],
                ),
              ),
            ],
          ),
          if (!clave) ...[
            const SizedBox(height: QEspacios.sm + 4),
            Container(
              padding: const EdgeInsets.all(QEspacios.sm + 4),
              decoration: BoxDecoration(
                color: QColores.superficieAzul,
                borderRadius: BorderRadius.circular(QRadios.control),
              ),
              child: const Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _Barra(fraccion: 0.45, alto: 10),
                  SizedBox(height: QEspacios.sm),
                  _Barra(fraccion: 0.9, alto: 10),
                  SizedBox(height: 6),
                  _Barra(fraccion: 0.7, alto: 10),
                ],
              ),
            ),
            const SizedBox(height: QEspacios.sm + 4),
            const Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                _Bloque(ancho: 96, alto: 40),
                SizedBox(width: QEspacios.sm),
                _Bloque(ancho: 80, alto: 40),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _Barra extends StatelessWidget {
  const _Barra({required this.fraccion, required this.alto});

  final double fraccion;
  final double alto;

  @override
  Widget build(BuildContext context) {
    return FractionallySizedBox(
      widthFactor: fraccion,
      alignment: AlignmentDirectional.centerStart,
      child: _Bloque(alto: alto),
    );
  }
}

class _Bloque extends StatelessWidget {
  const _Bloque({this.ancho, required this.alto});

  final double? ancho;
  final double alto;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: ancho,
      height: alto,
      decoration: BoxDecoration(
        color: QColores.superficieAzulMedia,
        borderRadius: BorderRadius.circular(QRadios.control),
      ),
    );
  }
}
