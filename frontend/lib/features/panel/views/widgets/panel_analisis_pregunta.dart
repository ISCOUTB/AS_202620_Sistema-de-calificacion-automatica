import 'package:flutter/material.dart';

import '../../../../common/tema/tema.dart';
import '../../../../common/tema/tokens.dart';
import '../../../../common/widgets/q_chip_estado.dart';
import '../../../../common/widgets/q_panel_navy.dart';
import '../../data/modelos_panel.dart';
import '../formato_cifras.dart';
import 'distribucion_respuestas.dart';

/// Panel navy con la estadística de la pregunta que más llama la atención del examen (RF-05):
/// el distractor más elegido frente a la respuesta correcta.
///
/// El diseño original cerraba con «Generar taller de refuerzo con IA». No está: el modelo de
/// lenguaje solo propone distractores a pedido del docente (RF-11, ADR-0005); no genera talleres
/// ni analiza resultados. En su lugar va la única lectura que el sistema puede respaldar: cuando
/// un distractor compite con la respuesta correcta, puede que la clave tenga dos opciones
/// equivalentes, algo que QuantIA no comprueba solo (ADR-0004).
class PanelAnalisisPregunta extends StatelessWidget {
  const PanelAnalisisPregunta({super.key, required this.analisis});

  final AnalisisPregunta analisis;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    final distractor = analisis.distractor;
    final correcta = analisis.correcta;
    final titulo = analisis.distractorSuperaACorrecta
        ? 'Pregunta ${analisis.numero}: el distractor ${distractor.letra} supera a la '
            'respuesta correcta'
        : 'Pregunta ${analisis.numero}: el distractor más elegido es la opción '
            '${distractor.letra}';

    return QPanelNavy(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: QColores.textoSobreNavy.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(QRadios.control),
                ),
                child: const Icon(Icons.insights_outlined, size: 20),
              ),
              const SizedBox(width: QEspacios.sm + 4),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'ANÁLISIS POR PREGUNTA',
                      style: QTexto.etiqueta.copyWith(color: QColores.textoSobreNavySuave),
                    ),
                    Text(
                      'Cómo se repartieron las marcas entre las opciones',
                      style: textos.bodySmall?.copyWith(color: QColores.textoSobreNavySuave),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: QEspacios.lg - 4),
          Semantics(
            header: true,
            child: Text(
              titulo,
              style: textos.headlineSmall?.copyWith(color: QColores.textoSobreNavy),
            ),
          ),
          const SizedBox(height: QEspacios.sm),
          Align(
            alignment: AlignmentDirectional.centerStart,
            child: _Formula(analisis.enunciado, semantica: 'Enunciado: ${analisis.enunciado}'),
          ),
          const SizedBox(height: QEspacios.md),
          Container(
            padding: const EdgeInsets.all(QEspacios.sm + 4),
            decoration: BoxDecoration(
              color: QColores.textoSobreNavy.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(QRadios.control),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _FilaOpcion(
                  icono: Icons.cancel_outlined,
                  colorIcono: QTono.error.acento,
                  rotulo: 'Distractor más elegido (opción ${distractor.letra})',
                  expresion: distractor.expresion,
                  porcentaje: formatearPorcentaje(analisis.porcentaje(distractor)),
                ),
                const SizedBox(height: QEspacios.sm),
                _FilaOpcion(
                  icono: Icons.check_circle_outline,
                  colorIcono: QTono.exito.acento,
                  rotulo: 'Respuesta correcta (opción ${correcta.letra})',
                  expresion: correcta.expresion,
                  porcentaje: formatearPorcentaje(analisis.porcentaje(correcta)),
                ),
                const SizedBox(height: QEspacios.sm + 4),
                Text.rich(
                  TextSpan(
                    children: [
                      const TextSpan(
                        text: 'Error que delata el distractor: ',
                        style: TextStyle(fontWeight: FontWeight.w600),
                      ),
                      TextSpan(text: '${analisis.errorDistractor}.'),
                    ],
                  ),
                  style: textos.bodySmall?.copyWith(color: QColores.textoSobreNavySuave),
                ),
              ],
            ),
          ),
          const SizedBox(height: QEspacios.lg - 4),
          DistribucionRespuestas(analisis: analisis),
          const SizedBox(height: QEspacios.lg - 4),
          const _NotaClaveEquivalente(),
        ],
      ),
    );
  }
}

/// Una opción destacada: qué es, su expresión y qué parte de las marcas se llevó.
class _FilaOpcion extends StatelessWidget {
  const _FilaOpcion({
    required this.icono,
    required this.colorIcono,
    required this.rotulo,
    required this.expresion,
    required this.porcentaje,
  });

  final IconData icono;
  final Color colorIcono;
  final String rotulo;
  final String expresion;
  final String porcentaje;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    return MergeSemantics(
      child: Wrap(
        alignment: WrapAlignment.spaceBetween,
        crossAxisAlignment: WrapCrossAlignment.center,
        spacing: QEspacios.sm,
        runSpacing: QEspacios.xs,
        children: [
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icono, size: 18, color: colorIcono),
              const SizedBox(width: QEspacios.sm),
              Flexible(
                child: Text(
                  rotulo,
                  style: textos.bodyMedium?.copyWith(color: QColores.textoSobreNavy),
                ),
              ),
            ],
          ),
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Flexible(child: _Formula(expresion)),
              const SizedBox(width: QEspacios.sm),
              Text(
                porcentaje,
                style: textos.titleSmall?.copyWith(
                  color: QColores.textoSobreNavy,
                  fontFeatures: const [FontFeature.tabularFigures()],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// Una expresión matemática en monoespaciada, sobre un fondo apenas más claro que el navy.
class _Formula extends StatelessWidget {
  const _Formula(this.expresion, {this.semantica});

  final String expresion;
  final String? semantica;

  @override
  Widget build(BuildContext context) {
    final caja = Container(
      padding: const EdgeInsetsDirectional.symmetric(horizontal: QEspacios.sm, vertical: 2),
      decoration: BoxDecoration(
        color: QColores.textoSobreNavy.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(QRadios.control / 2),
      ),
      child: Text(
        expresion,
        style: QTexto.formula.copyWith(color: QColores.textoSobreNavy),
      ),
    );
    if (semantica == null) return caja;
    return Semantics(label: semantica, child: ExcludeSemantics(child: caja));
  }
}

/// La nota que reemplaza al botón de IA del diseño: qué revisar cuando un distractor compite con
/// la respuesta correcta.
class _NotaClaveEquivalente extends StatelessWidget {
  const _NotaClaveEquivalente();

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    final formula = QTexto.formula.copyWith(color: QColores.textoSobreNavy, height: 1.5);
    return Container(
      padding: const EdgeInsets.all(QEspacios.md),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(QRadios.control),
        border: Border.all(color: QColores.textoSobreNavy.withValues(alpha: 0.18)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.rule_outlined, size: 20, color: QColores.textoSobreNavySuave),
          const SizedBox(width: QEspacios.sm + 4),
          Expanded(
            child: Text.rich(
              TextSpan(
                children: [
                  const TextSpan(
                    text: 'Un distractor muy elegido no siempre es un error de concepto. ',
                    style: TextStyle(
                      fontWeight: FontWeight.w600,
                      color: QColores.textoSobreNavy,
                    ),
                  ),
                  const TextSpan(
                    text: 'Si se lleva casi tantas marcas como la respuesta correcta, conviene '
                        'revisar si la clave admite dos respuestas equivalentes, como ',
                  ),
                  TextSpan(text: '1 − cos²(x)', style: formula),
                  const TextSpan(text: ' y '),
                  TextSpan(text: 'sen²(x)', style: formula),
                  const TextSpan(
                    text: '. QuantIA no lo comprueba por su cuenta: una equivalencia solo '
                        'cuenta si se habilita de forma explícita en la clave.',
                  ),
                ],
              ),
              style: textos.bodyMedium?.copyWith(
                color: QColores.textoSobreNavySuave,
                height: 1.5,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
