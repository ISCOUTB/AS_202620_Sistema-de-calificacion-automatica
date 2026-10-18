import 'package:flutter/material.dart';

import '../../../../common/tema/tema.dart';
import '../../../../common/tema/tokens.dart';
import '../../data/datos_ejemplo_pauta.dart';

/// Las preguntas del examen de ejemplo. Elegir una lleva su enunciado y su respuesta al
/// generador, para que el docente no tenga que copiarlas a mano.
///
/// Es una sola tarjeta con filas y no una tarjeta por pregunta: diez sombras seguidas pesan más
/// que la información que separan.
class ListaPreguntas extends StatelessWidget {
  const ListaPreguntas({
    super.key,
    required this.preguntas,
    required this.seleccionada,
    required this.alElegir,
  });

  final List<PreguntaEjemplo> preguntas;

  /// El número de la pregunta que llenó el formulario, si el docente no lo ha editado después.
  final int? seleccionada;
  final ValueChanged<PreguntaEjemplo> alElegir;

  @override
  Widget build(BuildContext context) {
    final radio = BorderRadius.circular(QRadios.tarjeta);
    return DecoratedBox(
      decoration: BoxDecoration(
        color: QColores.superficie,
        borderRadius: radio,
        border: Border.all(color: QColores.borde.withValues(alpha: 0.8)),
        boxShadow: QSombras.nivel1,
      ),
      child: Material(
        type: MaterialType.transparency,
        borderRadius: radio,
        clipBehavior: Clip.antiAlias,
        child: Column(
          children: [
            for (final (i, pregunta) in preguntas.indexed) ...[
              if (i > 0) const Divider(),
              _FilaPregunta(
                key: ValueKey('pregunta-${pregunta.numero}'),
                pregunta: pregunta,
                seleccionada: pregunta.numero == seleccionada,
                alElegir: () => alElegir(pregunta),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _FilaPregunta extends StatelessWidget {
  const _FilaPregunta({
    super.key,
    required this.pregunta,
    required this.seleccionada,
    required this.alElegir,
  });

  final PreguntaEjemplo pregunta;
  final bool seleccionada;
  final VoidCallback alElegir;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    return Semantics(
      button: true,
      selected: seleccionada,
      label: 'Pregunta ${pregunta.numero}, ${pregunta.tema}. ${pregunta.enunciado} '
          'Respuesta correcta: ${pregunta.respuestaCorrecta}. Llevar al generador.',
      excludeSemantics: true,
      child: Material(
        color: seleccionada ? QColores.superficieAzul : QColores.superficie,
        child: InkWell(
          onTap: alElegir,
          child: ConstrainedBox(
            constraints: const BoxConstraints(minHeight: 48),
            child: Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: QEspacios.md,
                vertical: QEspacios.sm + 4,
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    width: 32,
                    height: 32,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: seleccionada ? QColores.cobaltoOscuro : QColores.superficieAzulMedia,
                      borderRadius: BorderRadius.circular(QRadios.control),
                    ),
                    child: Text(
                      '${pregunta.numero}',
                      style: textos.labelLarge?.copyWith(
                        color: seleccionada ? QColores.textoSobreNavy : QColores.navy,
                        fontFeatures: const [FontFeature.tabularFigures()],
                      ),
                    ),
                  ),
                  const SizedBox(width: QEspacios.sm + 4),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          pregunta.tema,
                          style: textos.labelMedium?.copyWith(color: QColores.textoSuave),
                        ),
                        const SizedBox(height: 2),
                        Text.rich(
                          TextSpan(
                            children: [
                              const TextSpan(text: 'Derivada de '),
                              TextSpan(text: pregunta.funcion, style: QTexto.formula),
                            ],
                          ),
                          style: textos.bodyMedium,
                        ),
                        const SizedBox(height: 2),
                        Text.rich(
                          TextSpan(
                            children: [
                              TextSpan(
                                text: 'Respuesta: ',
                                style: textos.bodySmall,
                              ),
                              TextSpan(
                                text: pregunta.respuestaCorrecta,
                                style: QTexto.formula.copyWith(color: QColores.exitoTexto),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: QEspacios.sm),
                  Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Icon(
                      seleccionada ? Icons.check_circle_outlined : Icons.chevron_right_outlined,
                      size: 20,
                      color: seleccionada ? QColores.cobaltoOscuro : QColores.textoTenue,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
