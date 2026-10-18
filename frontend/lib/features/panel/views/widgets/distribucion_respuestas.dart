import 'package:flutter/material.dart';

import '../../../../common/tema/tokens.dart';
import '../../../../common/widgets/q_chip_estado.dart';
import '../../data/modelos_panel.dart';
import '../formato_cifras.dart';

/// Barra apilada con el reparto de las marcas entre las opciones de una pregunta, y su leyenda
/// en texto. Va sobre el panel navy.
///
/// El color distingue la respuesta correcta (verde) y el distractor más elegido (rojo), pero no
/// es la única pista: la leyenda dice la letra, el porcentaje y el papel de cada opción, y la
/// barra se lee con un rótulo de accesibilidad que repite lo mismo.
class DistribucionRespuestas extends StatelessWidget {
  const DistribucionRespuestas({super.key, required this.analisis});

  final AnalisisPregunta analisis;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    final opciones = analisis.opciones;
    final total = analisis.totalMarcas;
    final enBlanco = analisis.enBlanco;

    final conteo = StringBuffer('$total marcas');
    if (enBlanco == 1) conteo.write(' · 1 hoja en blanco');
    if (enBlanco > 1) conteo.write(' · $enBlanco hojas en blanco');

    final rotulo = 'Distribución de las marcas en la pregunta ${analisis.numero}: '
        '${opciones.map(_textoLeyenda).join('; ')}.';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Wrap(
          alignment: WrapAlignment.spaceBetween,
          spacing: QEspacios.sm,
          runSpacing: QEspacios.xs,
          children: [
            Text(
              'Distribución de las marcas (${opciones.map((o) => o.letra).join(' | ')})',
              style: textos.labelMedium?.copyWith(color: QColores.textoSobreNavySuave),
            ),
            Text(
              conteo.toString(),
              style: textos.labelMedium?.copyWith(
                color: QColores.textoSobreNavySuave,
                fontFeatures: const [FontFeature.tabularFigures()],
              ),
            ),
          ],
        ),
        const SizedBox(height: QEspacios.sm),
        Semantics(
          container: true,
          label: rotulo,
          child: ExcludeSemantics(
            child: Container(
              height: 14,
              padding: const EdgeInsets.all(2),
              decoration: BoxDecoration(
                color: QColores.textoSobreNavy.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(QRadios.control / 2),
              ),
              // Estirar en el eje cruzado: un DecoratedBox sin hijo mide cero de alto si la
              // fila no le impone el suyo.
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  for (final (indice, opcion) in opciones.where((o) => o.marcas > 0).indexed) ...[
                    if (indice > 0) const SizedBox(width: 2),
                    Expanded(
                      flex: opcion.marcas,
                      child: DecoratedBox(
                        decoration: BoxDecoration(
                          color: _colorDe(opcion),
                          borderRadius: BorderRadius.circular(2),
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
        const SizedBox(height: QEspacios.sm + 4),
        ExcludeSemantics(
          child: Wrap(
            spacing: QEspacios.md,
            runSpacing: QEspacios.sm,
            children: [
              for (final opcion in opciones)
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 10,
                      height: 10,
                      decoration: BoxDecoration(
                        color: _colorDe(opcion),
                        borderRadius: BorderRadius.circular(2),
                      ),
                    ),
                    const SizedBox(width: QEspacios.xs + 2),
                    Flexible(
                      child: Text(
                        _textoLeyenda(opcion),
                        style: textos.labelMedium?.copyWith(
                          color: _esDestacada(opcion)
                              ? QColores.textoSobreNavy
                              : QColores.textoSobreNavySuave,
                          fontFeatures: const [FontFeature.tabularFigures()],
                        ),
                      ),
                    ),
                  ],
                ),
            ],
          ),
        ),
      ],
    );
  }

  bool _esDestacada(OpcionRespuesta opcion) =>
      opcion.correcta || opcion.letra == analisis.letraDistractor;

  /// «B · 38 % · correcta»: letra, porcentaje y papel, sin depender del color.
  String _textoLeyenda(OpcionRespuesta opcion) {
    final base = '${opcion.letra} · ${formatearPorcentaje(analisis.porcentaje(opcion))}';
    if (opcion.correcta) return '$base · correcta';
    if (opcion.letra == analisis.letraDistractor) return '$base · distractor más elegido';
    return base;
  }

  Color _colorDe(OpcionRespuesta opcion) {
    if (opcion.correcta) return QTono.exito.acento;
    if (opcion.letra == analisis.letraDistractor) return QTono.error.acento;
    return QColores.textoSobreNavySuave.withValues(alpha: 0.45);
  }
}
