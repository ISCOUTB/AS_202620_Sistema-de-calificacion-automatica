import 'package:flutter/material.dart';

import '../../../../common/tema/tokens.dart';
import '../../../../common/widgets/q_chip_estado.dart';
import '../../../../common/widgets/q_tarjeta.dart';
import '../../../../common/widgets/q_titulo_seccion.dart';
import '../../data/modelos_panel.dart';
import '../formato_cifras.dart';
import 'cuadricula_adaptable.dart';

/// Aciertos del grupo por competencia: una barra corta por cada una, con el porcentaje y el
/// nivel escritos al lado para que la barra no sea la única forma de leerlo.
class RendimientoCompetencias extends StatelessWidget {
  const RendimientoCompetencias({
    super.key,
    required this.competencias,
    required this.columnas,
  });

  final List<RendimientoCompetencia> competencias;
  final int columnas;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const QTituloSeccion(
          titulo: 'Rendimiento por competencias',
          descripcion: 'Porcentaje de aciertos del grupo en las preguntas de cada competencia',
        ),
        const SizedBox(height: QEspacios.md),
        CuadriculaAdaptable(
          columnas: columnas,
          espacio: QEspacios.sm + 4,
          children: [
            for (final competencia in competencias) _TarjetaCompetencia(competencia),
          ],
        ),
      ],
    );
  }
}

class _TarjetaCompetencia extends StatelessWidget {
  const _TarjetaCompetencia(this.competencia);

  final RendimientoCompetencia competencia;

  static QTono _tonoDe(NivelCompetencia nivel) => switch (nivel) {
        NivelCompetencia.alto => QTono.exito,
        NivelCompetencia.medio => QTono.neutro,
        NivelCompetencia.bajo => QTono.advertencia,
      };

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    final nivel = competencia.nivel;
    final tono = _tonoDe(nivel);
    final porcentaje = formatearPorcentaje(competencia.porcentajeAciertos);
    final preguntas =
        competencia.preguntas == 1 ? '1 pregunta' : '${competencia.preguntas} preguntas';
    final detalle = competencia.nota == null ? preguntas : '$preguntas · ${competencia.nota}';

    return Semantics(
      container: true,
      label: '${competencia.nombre}: $porcentaje de aciertos en $detalle. '
          'Nivel ${nivel.texto.toLowerCase()}.',
      child: ExcludeSemantics(
        child: QTarjeta(
          padding: const EdgeInsets.all(QEspacios.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(child: Text(competencia.nombre, style: textos.titleSmall)),
                  const SizedBox(width: QEspacios.sm),
                  Text(
                    porcentaje,
                    style: textos.titleSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                      color: nivel == NivelCompetencia.bajo ? tono.texto : QColores.texto,
                      fontFeatures: const [FontFeature.tabularFigures()],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: QEspacios.sm),
              _Barra(fraccion: competencia.porcentajeAciertos / 100, color: tono.acento),
              const SizedBox(height: QEspacios.sm),
              Row(
                children: [
                  Expanded(child: Text(detalle, style: textos.bodySmall)),
                  const SizedBox(width: QEspacios.sm),
                  QChipEstado(
                    texto: nivel.texto,
                    tono: tono,
                    icono: nivel == NivelCompetencia.bajo ? Icons.warning_amber_outlined : null,
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Barra horizontal de 8 px con su riel.
class _Barra extends StatelessWidget {
  const _Barra({required this.fraccion, required this.color});

  final double fraccion;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final radio = BorderRadius.circular(QRadios.control);
    return Container(
      height: 8,
      decoration: BoxDecoration(color: QColores.superficieAzulMedia, borderRadius: radio),
      alignment: AlignmentDirectional.centerStart,
      child: FractionallySizedBox(
        widthFactor: fraccion.clamp(0.0, 1.0),
        heightFactor: 1,
        child: DecoratedBox(decoration: BoxDecoration(color: color, borderRadius: radio)),
      ),
    );
  }
}
