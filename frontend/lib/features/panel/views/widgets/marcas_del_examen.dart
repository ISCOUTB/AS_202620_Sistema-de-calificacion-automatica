import 'package:flutter/material.dart';

import '../../../../common/tema/tokens.dart';
import '../../../../common/widgets/q_tarjeta.dart';
import '../../../../common/widgets/q_titulo_seccion.dart';
import '../../data/modelos_panel.dart';
import '../colores_graficos.dart';
import '../formato_cifras.dart';

/// Una parte de la barra: qué es, cuántas y de qué color.
class _Parte {
  const _Parte(this.nombre, this.cantidad, this.color);

  final String nombre;
  final int cantidad;
  final Color color;
}

/// Cómo se marcaron las respuestas (RF-05, ADR-0028): cada pregunta de cada hoja con nota, en una
/// sola categoría. Una marca clara es correcta o incorrecta; las tenues o dudosas, las dobles y las
/// en blanco van aparte, aunque el docente ya las haya resuelto, porque lo que se describe es cómo
/// se marcó la hoja.
///
/// La barra es una sola pieza dividida en partes, con 2 px de superficie entre ellas. Cada parte
/// tiene su tooltip, y debajo va la leyenda con el nombre, la cifra y el porcentaje de cada una:
/// el color nunca es la única pista.
class MarcasDelExamenVista extends StatelessWidget {
  const MarcasDelExamenVista({super.key, required this.marcas, required this.hojasConNota});

  final MarcasDelExamen marcas;
  final int hojasConNota;

  List<_Parte> get _partes => [
        _Parte('Correctas', marcas.correctas, ColoresGraficos.correcta),
        _Parte('Incorrectas', marcas.incorrectas, ColoresGraficos.incorrecta),
        _Parte('Marca doble', marcas.dobles, ColoresGraficos.doble),
        _Parte('Tenue o dudosa', marcas.tenuesODudosas, ColoresGraficos.tenue),
        _Parte('En blanco', marcas.enBlanco, ColoresGraficos.enBlanco),
      ];

  String _porcentaje(int cantidad) =>
      formatearPorcentaje(marcas.total == 0 ? 0 : cantidad * 100 / marcas.total, decimales: 1);

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    final total = marcas.total;
    final partes = _partes;
    final hojas = hojasConNota == 1 ? 'la hoja con nota' : 'las $hojasConNota hojas con nota';

    return QTarjeta(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          QTituloSeccion(
            titulo: 'Cómo se marcaron las respuestas',
            descripcion: total == 0
                ? 'Cuando haya hojas con nota, aquí verá cuántas respuestas se marcaron bien, '
                    'con marca tenue, doble o en blanco'
                : '$total respuestas de $hojas, según lo que vio la lectura',
          ),
          if (total > 0) ...[
            const SizedBox(height: QEspacios.md),
            Semantics(
              container: true,
              label: 'Cómo se marcaron las respuestas: '
                  '${partes.map((p) => '${p.nombre}, ${p.cantidad}').join('; ')}.',
              child: ExcludeSemantics(
                child: SizedBox(
                  height: 16,
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      for (final (indice, parte) in partes.where((p) => p.cantidad > 0).indexed) ...[
                        if (indice > 0) const SizedBox(width: 2),
                        Expanded(
                          flex: parte.cantidad,
                          child: Tooltip(
                            message: '${parte.nombre}: ${parte.cantidad} '
                                '(${_porcentaje(parte.cantidad)})',
                            child: DecoratedBox(
                              decoration: BoxDecoration(
                                color: parte.color,
                                borderRadius: BorderRadius.circular(4),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: QEspacios.md),
            ExcludeSemantics(
              child: Wrap(
                spacing: QEspacios.lg,
                runSpacing: QEspacios.sm,
                children: [
                  for (final parte in partes)
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        MuestraDeColor(parte.color),
                        const SizedBox(width: QEspacios.xs + 2),
                        Flexible(child: Text(parte.nombre, style: textos.bodyMedium)),
                        const SizedBox(width: QEspacios.xs + 2),
                        Text(
                          '${parte.cantidad} · ${_porcentaje(parte.cantidad)}',
                          style: textos.bodyMedium?.copyWith(
                            color: QColores.textoSuave,
                            fontFeatures: const [FontFeature.tabularFigures()],
                          ),
                        ),
                      ],
                    ),
                ],
              ),
            ),
            if (marcas.pendientes > 0) ...[
              const SizedBox(height: QEspacios.md),
              Text(
                marcas.pendientes == 1
                    ? '1 de las tenues o dobles espera su revisión: mientras tanto suma cero.'
                    : '${marcas.pendientes} de las tenues o dobles esperan su revisión: mientras '
                        'tanto suman cero.',
                style: textos.bodySmall?.copyWith(color: QColores.advertenciaTexto),
              ),
            ],
          ],
        ],
      ),
    );
  }
}
