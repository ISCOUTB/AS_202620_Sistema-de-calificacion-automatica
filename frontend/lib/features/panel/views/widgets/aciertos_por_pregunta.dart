import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../../../common/tema/tokens.dart';
import '../../../../common/widgets/q_tarjeta.dart';
import '../../../../common/widgets/q_titulo_seccion.dart';
import '../../data/modelos_panel.dart';
import '../colores_graficos.dart';
import '../formato_cifras.dart';

/// El porcentaje de aciertos de cada pregunta (RF-05, ADR-0028): una columna por pregunta, en
/// ámbar las que acertó menos de la mitad del grupo. Debajo, la pregunta más difícil con la opción
/// incorrecta que más se marcó, que es la que suele delatar un error de concepto, y la tabla con
/// las cifras de todas.
class AciertosPorPregunta extends StatelessWidget {
  const AciertosPorPregunta({super.key, required this.preguntas});

  final List<PreguntaDelPanel> preguntas;

  static const _alto = 180.0;
  static const _corte = 50.0;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    final conHojas = preguntas.where((p) => p.hojas > 0).toList();
    final dificil = conHojas.isEmpty
        ? null
        : conHojas.reduce((a, b) => b.porcentajeAciertos < a.porcentajeAciertos ? b : a);

    return QTarjeta(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          QTituloSeccion(
            titulo: 'Aciertos por pregunta',
            descripcion: conHojas.isEmpty
                ? 'Cuando haya hojas con nota, aquí verá qué preguntas costaron más'
                : 'Porcentaje del grupo que acertó cada pregunta',
          ),
          if (conHojas.isNotEmpty) ...[
            const SizedBox(height: QEspacios.md),
            Semantics(
              container: true,
              label: 'Aciertos por pregunta. '
                  '${conHojas.map((p) => 'Pregunta ${p.numero}: '
                      '${formatearPorcentaje(p.porcentajeAciertos)}').join('; ')}.',
              child: ExcludeSemantics(
                child: SizedBox(height: _alto, child: _Columnas(preguntas: preguntas)),
              ),
            ),
            const SizedBox(height: QEspacios.md),
            ExcludeSemantics(
              child: Wrap(
                spacing: QEspacios.lg,
                runSpacing: QEspacios.sm,
                children: [
                  _leyenda(context, ColoresGraficos.aprobado, '50 % o más acertó'),
                  _leyenda(context, ColoresGraficos.noAprobado, 'Menos de la mitad acertó'),
                ],
              ),
            ),
            if (dificil != null) ...[
              const SizedBox(height: QEspacios.md),
              Text(
                _fraseDeLaMasDificil(dificil),
                key: const Key('pregunta-mas-dificil'),
                style: textos.bodyMedium,
              ),
            ],
            const SizedBox(height: QEspacios.sm),
            Theme(
              data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
              child: ExpansionTile(
                tilePadding: EdgeInsets.zero,
                title: Text('Ver como tabla', style: textos.labelLarge),
                children: [_Tabla(preguntas: conHojas)],
              ),
            ),
          ],
        ],
      ),
    );
  }

  static Widget _leyenda(BuildContext context, Color color, String texto) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          MuestraDeColor(color),
          const SizedBox(width: QEspacios.xs + 2),
          Flexible(child: Text(texto, style: Theme.of(context).textTheme.bodyMedium)),
        ],
      );

  static String _fraseDeLaMasDificil(PreguntaDelPanel pregunta) {
    final base = 'La que más costó fue la pregunta ${pregunta.numero}: acertó el '
        '${formatearPorcentaje(pregunta.porcentajeAciertos)} '
        '(${pregunta.aciertos} de ${pregunta.hojas}). La correcta es la ${pregunta.correcta}';
    final distractor = pregunta.distractorMasMarcado;
    if (distractor == null) return '$base.';
    final veces = pregunta.marcadas[distractor] ?? 0;
    return '$base, y la incorrecta más marcada fue la $distractor '
        '(${veces == 1 ? '1 vez' : '$veces veces'}).';
  }
}

class _Columnas extends StatelessWidget {
  const _Columnas({required this.preguntas});

  final List<PreguntaDelPanel> preguntas;

  static const _margenIzquierdo = 36.0;
  static const _margenInferior = 20.0;
  static const _margenSuperior = 6.0;

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Positioned.fill(
          child: CustomPaint(
            painter: _Reticula(
              numeros: [for (final p in preguntas) p.numero],
              margenIzquierdo: _margenIzquierdo,
              margenInferior: _margenInferior,
              margenSuperior: _margenSuperior,
            ),
          ),
        ),
        Positioned(
          left: _margenIzquierdo,
          right: 0,
          top: _margenSuperior,
          bottom: _margenInferior,
          child: LayoutBuilder(
            builder: (context, restricciones) {
              final ranura = restricciones.maxWidth / math.max(1, preguntas.length);
              final anchoBarra = math.min(24.0, math.max(2.0, ranura - 2));
              return Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  for (final pregunta in preguntas)
                    Expanded(
                      child: Tooltip(
                        message: _mensaje(pregunta),
                        child: Container(
                          color: Colors.transparent,
                          alignment: Alignment.bottomCenter,
                          child: Container(
                            width: anchoBarra,
                            height: restricciones.maxHeight * pregunta.porcentajeAciertos / 100,
                            decoration: BoxDecoration(
                              color: pregunta.porcentajeAciertos >= AciertosPorPregunta._corte
                                  ? ColoresGraficos.aprobado
                                  : ColoresGraficos.noAprobado,
                              borderRadius: const BorderRadius.vertical(top: Radius.circular(4)),
                            ),
                          ),
                        ),
                      ),
                    ),
                ],
              );
            },
          ),
        ),
      ],
    );
  }

  static String _mensaje(PreguntaDelPanel p) {
    final partes = [
      'Pregunta ${p.numero}: ${formatearPorcentaje(p.porcentajeAciertos)} de aciertos '
          '(${p.aciertos} de ${p.hojas})',
      'Correcta: ${p.correcta}',
      'Marcadas: ${p.marcadas.entries.map((e) => '${e.key} ${e.value}').join(', ')}',
      if (p.enBlanco > 0) 'En blanco: ${p.enBlanco}',
      if (p.dobles > 0) 'Dobles: ${p.dobles}',
      if (p.dudosas > 0) 'Tenues o dudosas: ${p.dudosas}',
    ];
    return partes.join('\n');
  }
}

/// Retícula en 0, 50 y 100 %, y el número de la pregunta cada cinco.
class _Reticula extends CustomPainter {
  const _Reticula({
    required this.numeros,
    required this.margenIzquierdo,
    required this.margenInferior,
    required this.margenSuperior,
  });

  final List<int> numeros;
  final double margenIzquierdo;
  final double margenInferior;
  final double margenSuperior;

  @override
  void paint(Canvas canvas, Size size) {
    final ancho = size.width - margenIzquierdo;
    final alto = size.height - margenInferior - margenSuperior;
    final base = margenSuperior + alto;
    final linea = Paint()
      ..color = ColoresGraficos.reticula
      ..strokeWidth = 1;

    for (final valor in const [0, 50, 100]) {
      final y = base - alto * valor / 100;
      canvas.drawLine(Offset(margenIzquierdo, y), Offset(size.width, y), linea);
      final pintor = _texto('$valor %');
      pintor.paint(canvas, Offset(margenIzquierdo - 6 - pintor.width, y - pintor.height / 2));
      pintor.dispose();
    }

    if (numeros.isEmpty) return;
    final ranura = ancho / numeros.length;
    for (final (indice, numero) in numeros.indexed) {
      if (numero != 1 && numero % 5 != 0) continue;
      final pintor = _texto('$numero');
      final x = margenIzquierdo + ranura * (indice + 0.5) - pintor.width / 2;
      pintor.paint(canvas, Offset(x, base + 4));
      pintor.dispose();
    }
  }

  static TextPainter _texto(String texto) => TextPainter(
        text: TextSpan(text: texto, style: estiloEje),
        textDirection: TextDirection.ltr,
      )..layout();

  @override
  bool shouldRepaint(_Reticula anterior) =>
      anterior.numeros.length != numeros.length || anterior.margenIzquierdo != margenIzquierdo;
}

/// Las mismas cifras en una tabla, para leerlas sin el gráfico.
class _Tabla extends StatelessWidget {
  const _Tabla({required this.preguntas});

  final List<PreguntaDelPanel> preguntas;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: DataTable(
        headingRowHeight: 36,
        dataRowMinHeight: 32,
        dataRowMaxHeight: 36,
        columnSpacing: QEspacios.lg,
        columns: const [
          DataColumn(label: Text('Pregunta'), numeric: true),
          DataColumn(label: Text('Correcta')),
          DataColumn(label: Text('Aciertos'), numeric: true),
          DataColumn(label: Text('A'), numeric: true),
          DataColumn(label: Text('B'), numeric: true),
          DataColumn(label: Text('C'), numeric: true),
          DataColumn(label: Text('D'), numeric: true),
          DataColumn(label: Text('En blanco'), numeric: true),
          DataColumn(label: Text('Dobles'), numeric: true),
        ],
        rows: [
          for (final p in preguntas)
            DataRow(
              cells: [
                DataCell(Text('${p.numero}')),
                DataCell(Text(p.correcta)),
                DataCell(Text(
                  '${formatearPorcentaje(p.porcentajeAciertos)} (${p.aciertos}/${p.hojas})',
                )),
                for (final opcion in const ['A', 'B', 'C', 'D'])
                  DataCell(Text('${p.marcadas[opcion] ?? 0}')),
                DataCell(Text('${p.enBlanco}')),
                DataCell(Text('${p.dobles}')),
              ],
            ),
        ],
      ),
    );
  }
}
