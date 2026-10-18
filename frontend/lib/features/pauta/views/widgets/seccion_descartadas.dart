import 'package:flutter/material.dart';

import '../../../../common/tema/tema.dart';
import '../../../../common/tema/tokens.dart';
import '../../data/servicio_distractores.dart';

/// Las propuestas que la regla del dominio no dejó pasar, con el motivo que da la API.
///
/// Empieza plegada: lo que el docente tiene que revisar son las que sí pasaron. Pero se muestra
/// siempre que haya alguna, porque ocultarlas haría parecer que el modelo propuso menos de lo
/// que propuso, y el motivo explica por qué falta una opción.
class SeccionDescartadas extends StatefulWidget {
  const SeccionDescartadas({super.key, required this.descartadas});

  final List<PropuestaDescartada> descartadas;

  @override
  State<SeccionDescartadas> createState() => _SeccionDescartadasState();
}

class _SeccionDescartadasState extends State<SeccionDescartadas> {
  bool _abierta = false;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    final sinAnimacion = MediaQuery.disableAnimationsOf(context);
    final duracion = sinAnimacion ? Duration.zero : QDuraciones.media;
    final n = widget.descartadas.length;
    final titulo = n == 1 ? '1 propuesta descartada' : '$n propuestas descartadas';
    final radio = BorderRadius.circular(QRadios.tarjeta);

    return DecoratedBox(
      decoration: BoxDecoration(
        color: QColores.superficie,
        borderRadius: radio,
        border: Border.all(color: QColores.borde),
      ),
      child: Material(
        type: MaterialType.transparency,
        borderRadius: radio,
        clipBehavior: Clip.antiAlias,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Semantics(
              button: true,
              expanded: _abierta,
              child: InkWell(
                key: const Key('cabecera-descartadas'),
                onTap: () => setState(() => _abierta = !_abierta),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(minHeight: 56),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: QEspacios.md,
                      vertical: QEspacios.sm + 4,
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.block_outlined, size: 20, color: QColores.textoSuave),
                        const SizedBox(width: QEspacios.sm + 4),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(titulo, style: textos.titleSmall),
                              Text(
                                'El sistema no las dejó pasar. Vea el motivo de cada una.',
                                style: textos.bodySmall,
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: QEspacios.sm),
                        AnimatedRotation(
                          turns: _abierta ? 0.5 : 0,
                          duration: duracion,
                          child: const Icon(
                            Icons.expand_more_outlined,
                            color: QColores.textoSuave,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
            AnimatedSize(
              duration: duracion,
              curve: Curves.easeOutCubic,
              alignment: Alignment.topCenter,
              child: _abierta
                  ? Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        for (final d in widget.descartadas) ...[
                          const Divider(),
                          _FilaDescartada(descartada: d),
                        ],
                      ],
                    )
                  : const SizedBox(width: double.infinity),
            ),
          ],
        ),
      ),
    );
  }
}

class _FilaDescartada extends StatelessWidget {
  const _FilaDescartada({required this.descartada});

  final PropuestaDescartada descartada;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        QEspacios.md + 20 + QEspacios.sm + 4,
        QEspacios.sm + 4,
        QEspacios.md,
        QEspacios.sm + 4,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            descartada.expresion,
            style: QTexto.formula.copyWith(color: QColores.textoSuave),
          ),
          const SizedBox(height: 2),
          Text.rich(
            TextSpan(
              children: [
                TextSpan(text: 'Motivo: ', style: textos.labelMedium),
                TextSpan(text: descartada.motivo),
              ],
            ),
            style: textos.bodyMedium?.copyWith(color: QColores.texto),
          ),
        ],
      ),
    );
  }
}
