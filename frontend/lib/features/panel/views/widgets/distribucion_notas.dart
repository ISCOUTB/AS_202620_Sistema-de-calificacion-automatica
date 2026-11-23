import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../../../common/tema/tokens.dart';
import '../../../../common/widgets/q_tarjeta.dart';
import '../../../../common/widgets/q_titulo_seccion.dart';
import '../../data/modelos_panel.dart';
import '../colores_graficos.dart';
import '../formato_cifras.dart';

/// La distribución de las notas del grupo: un histograma en tramos de 0,5 y, encima, la campana de
/// Gauss con la media y la desviación estándar del grupo (RF-05, ADR-0028).
///
/// La curva está en la misma escala que las barras: en cada nota vale cuántas hojas tendría un
/// tramo si las notas siguieran la campana. Así se ve de un vistazo si el grupo se parece a una
/// normal, si está corrido hacia arriba o hacia abajo, o si tiene dos grupos.
///
/// Las barras de los tramos por debajo de la aprobación van en ámbar y las demás en cobalto, y la
/// leyenda lo dice con palabras. Cada barra tiene su tooltip con el tramo y cuántas hojas.
class DistribucionNotas extends StatelessWidget {
  const DistribucionNotas({
    super.key,
    required this.notas,
    required this.notaAprobatoria,
    this.media,
    this.desviacion,
  });

  /// De 0 a 5.
  final List<double> notas;
  final double notaAprobatoria;
  final double? media;
  final double? desviacion;

  static const _anchoTramo = 0.5;
  static const _alto = 220.0;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    final media = this.media;
    final desviacion = this.desviacion;
    final conCurva = notas.length >= 2 && desviacion != null && desviacion > 0 && media != null;

    return QTarjeta(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          QTituloSeccion(
            titulo: 'Distribución de las notas',
            descripcion: notas.isEmpty
                ? 'Cuando haya hojas con nota, aquí verá cómo se reparten de 1 a 5'
                : 'Cuántas hojas cayeron en cada tramo de 0,5, con la campana de Gauss del grupo',
          ),
          if (notas.isNotEmpty) ...[
            const SizedBox(height: QEspacios.md),
            Semantics(
              container: true,
              label: _resumenAccesible(),
              child: ExcludeSemantics(
                child: SizedBox(
                  height: _alto,
                  child: _Histograma(
                    tramos: tramosDeNotas(notas, ancho: _anchoTramo),
                    totalHojas: notas.length,
                    notaAprobatoria: notaAprobatoria,
                    media: conCurva ? media : null,
                    desviacion: conCurva ? desviacion : null,
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
                  _Leyenda(
                    muestra: const MuestraDeColor(ColoresGraficos.aprobado),
                    texto: 'Aprobado (${formatearDecimal(notaAprobatoria)} o más)',
                  ),
                  const _Leyenda(
                    muestra: MuestraDeColor(ColoresGraficos.noAprobado),
                    texto: 'No aprobado',
                  ),
                  if (conCurva)
                    _Leyenda(
                      muestra: const MuestraDeColor(ColoresGraficos.curva, linea: true),
                      texto: 'Campana: media ${formatearDecimal(media, decimales: 2)}, '
                          'desviación ${formatearDecimal(desviacion, decimales: 2)}',
                    ),
                ],
              ),
            ),
            if (!conCurva) ...[
              const SizedBox(height: QEspacios.sm),
              Text(
                'Hacen falta al menos dos notas distintas para dibujar la campana.',
                style: textos.bodySmall?.copyWith(color: QColores.textoSuave),
              ),
            ],
          ],
        ],
      ),
    );
  }

  String _resumenAccesible() {
    final tramos = tramosDeNotas(notas, ancho: _anchoTramo).where((t) => t.hojas > 0);
    final partes = [
      for (final t in tramos)
        'de ${formatearDecimal(t.desde)} a ${formatearDecimal(t.hasta)}: ${t.hojas}',
    ];
    final curva = media == null || desviacion == null
        ? ''
        : ' Media ${formatearDecimal(media!, decimales: 2)}, desviación '
            '${formatearDecimal(desviacion!, decimales: 2)}.';
    return 'Distribución de ${notas.length} notas. ${partes.join('; ')}.$curva';
  }
}

class _Leyenda extends StatelessWidget {
  const _Leyenda({required this.muestra, required this.texto});

  final Widget muestra;
  final String texto;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        muestra,
        const SizedBox(width: QEspacios.xs + 2),
        Flexible(child: Text(texto, style: Theme.of(context).textTheme.bodyMedium)),
      ],
    );
  }
}

/// El área del gráfico: retícula y ejes detrás, barras con tooltip en medio y la curva encima.
class _Histograma extends StatelessWidget {
  const _Histograma({
    required this.tramos,
    required this.totalHojas,
    required this.notaAprobatoria,
    this.media,
    this.desviacion,
  });

  final List<TramoDeNotas> tramos;
  final int totalHojas;
  final double notaAprobatoria;
  final double? media;
  final double? desviacion;

  static const _margenIzquierdo = 28.0;
  static const _margenInferior = 22.0;
  static const _margenSuperior = 16.0;

  /// El tope del eje: la barra más alta o el pico de la curva, redondeado hacia arriba.
  int get _tope {
    var maximo = tramos.fold<int>(0, (m, t) => math.max(m, t.hojas)).toDouble();
    final media = this.media;
    final desviacion = this.desviacion;
    if (media != null && desviacion != null) {
      final ancho = tramos.first.hasta - tramos.first.desde;
      maximo = math.max(maximo, totalHojas * ancho * densidadNormal(media, media, desviacion));
    }
    return math.max(1, maximo.ceil());
  }

  @override
  Widget build(BuildContext context) {
    final tope = _tope;
    final desde = tramos.first.desde;
    final hasta = tramos.last.hasta;

    return Stack(
      children: [
        Positioned.fill(
          child: CustomPaint(
            painter: _Ejes(
              tope: tope,
              desde: desde,
              hasta: hasta,
              notaAprobatoria: notaAprobatoria,
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
              final ranura = restricciones.maxWidth / tramos.length;
              final anchoBarra = math.min(24.0, math.max(2.0, ranura - 2));
              return Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  for (final tramo in tramos)
                    Expanded(
                      child: Tooltip(
                        message: _mensaje(tramo),
                        // La zona del tooltip es la columna entera, no solo la barra: una barra
                        // baja o vacía también se puede consultar.
                        child: Container(
                          color: Colors.transparent,
                          alignment: Alignment.bottomCenter,
                          child: Container(
                            width: anchoBarra,
                            height: restricciones.maxHeight * tramo.hojas / tope,
                            decoration: BoxDecoration(
                              color: tramo.desde >= notaAprobatoria - 1e-9
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
        if (media != null && desviacion != null)
          Positioned(
            left: _margenIzquierdo,
            right: 0,
            top: _margenSuperior,
            bottom: _margenInferior,
            child: IgnorePointer(
              child: CustomPaint(
                painter: _Campana(
                  media: media!,
                  desviacion: desviacion!,
                  totalHojas: totalHojas,
                  anchoTramo: tramos.first.hasta - tramos.first.desde,
                  desde: desde,
                  hasta: hasta,
                  tope: tope,
                ),
              ),
            ),
          ),
      ],
    );
  }

  String _mensaje(TramoDeNotas tramo) {
    final ultimo = identical(tramo, tramos.last);
    final rango = 'De ${formatearDecimal(tramo.desde)} a '
        '${ultimo ? formatearDecimal(tramo.hasta) : 'menos de ${formatearDecimal(tramo.hasta)}'}';
    final hojas = tramo.hojas == 1 ? '1 hoja' : '${tramo.hojas} hojas';
    final porcentaje = formatearPorcentaje(tramo.hojas * 100 / totalHojas);
    return '$rango: $hojas ($porcentaje)';
  }
}

/// Retícula horizontal, rótulos de los dos ejes y la línea de la nota aprobatoria.
class _Ejes extends CustomPainter {
  const _Ejes({
    required this.tope,
    required this.desde,
    required this.hasta,
    required this.notaAprobatoria,
    required this.margenIzquierdo,
    required this.margenInferior,
    required this.margenSuperior,
  });

  final int tope;
  final double desde;
  final double hasta;
  final double notaAprobatoria;
  final double margenIzquierdo;
  final double margenInferior;
  final double margenSuperior;

  @override
  void paint(Canvas canvas, Size size) {
    final ancho = size.width - margenIzquierdo;
    final alto = size.height - margenInferior - margenSuperior;
    final base = margenSuperior + alto;
    final reticula = Paint()
      ..color = ColoresGraficos.reticula
      ..strokeWidth = 1;

    // Eje vertical: hasta cinco marcas en números enteros de hojas.
    final paso = math.max(1, (tope / 4).ceil());
    for (var valor = 0; valor <= tope; valor += paso) {
      final y = base - alto * valor / tope;
      canvas.drawLine(Offset(margenIzquierdo, y), Offset(size.width, y), reticula);
      _rotulo(canvas, '$valor', Offset(margenIzquierdo - 6, y), alinearDerecha: true);
    }

    // Eje horizontal: las notas enteras.
    double xDe(double nota) => margenIzquierdo + ancho * (nota - desde) / (hasta - desde);
    for (var nota = desde.ceil(); nota <= hasta; nota++) {
      _rotulo(canvas, '$nota', Offset(xDe(nota.toDouble()), base + 4), centrar: true);
    }

    // La nota aprobatoria: una línea fina y su rótulo arriba.
    if (notaAprobatoria > desde && notaAprobatoria < hasta) {
      final x = xDe(notaAprobatoria);
      canvas.drawLine(
        Offset(x, margenSuperior),
        Offset(x, base),
        Paint()
          ..color = QColores.textoTenue
          ..strokeWidth = 1,
      );
      _rotulo(
        canvas,
        'Aprueba ${formatearDecimal(notaAprobatoria)}',
        Offset(x + 4, 0),
      );
    }
  }

  void _rotulo(
    Canvas canvas,
    String texto,
    Offset punto, {
    bool alinearDerecha = false,
    bool centrar = false,
  }) {
    final pintor = TextPainter(
      text: TextSpan(text: texto, style: estiloEje),
      textDirection: TextDirection.ltr,
    )..layout();
    var x = punto.dx;
    var y = punto.dy;
    if (alinearDerecha) {
      x -= pintor.width;
      y -= pintor.height / 2;
    }
    if (centrar) x -= pintor.width / 2;
    pintor.paint(canvas, Offset(x, y));
    pintor.dispose();
  }

  @override
  bool shouldRepaint(_Ejes anterior) =>
      anterior.tope != tope ||
      anterior.desde != desde ||
      anterior.hasta != hasta ||
      anterior.notaAprobatoria != notaAprobatoria;
}

/// La campana de Gauss, en la escala de las barras, y una marca en la media.
class _Campana extends CustomPainter {
  const _Campana({
    required this.media,
    required this.desviacion,
    required this.totalHojas,
    required this.anchoTramo,
    required this.desde,
    required this.hasta,
    required this.tope,
  });

  final double media;
  final double desviacion;
  final int totalHojas;
  final double anchoTramo;
  final double desde;
  final double hasta;
  final int tope;

  @override
  void paint(Canvas canvas, Size size) {
    Offset punto(double nota) {
      final hojas = totalHojas * anchoTramo * densidadNormal(nota, media, desviacion);
      return Offset(
        size.width * (nota - desde) / (hasta - desde),
        size.height - size.height * hojas / tope,
      );
    }

    final camino = Path();
    const pasos = 120;
    for (var i = 0; i <= pasos; i++) {
      final p = punto(desde + (hasta - desde) * i / pasos);
      if (i == 0) {
        camino.moveTo(p.dx, p.dy);
      } else {
        camino.lineTo(p.dx, p.dy);
      }
    }
    canvas.drawPath(
      camino,
      Paint()
        ..color = ColoresGraficos.curva
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2
        ..strokeJoin = StrokeJoin.round
        ..strokeCap = StrokeCap.round,
    );

    // La media: un punto sobre la curva, con un anillo del color de la superficie.
    if (media >= desde && media <= hasta) {
      final cima = punto(media);
      canvas.drawCircle(cima, 6, Paint()..color = QColores.superficie);
      canvas.drawCircle(cima, 4, Paint()..color = ColoresGraficos.curva);
    }
  }

  @override
  bool shouldRepaint(_Campana anterior) =>
      anterior.media != media ||
      anterior.desviacion != desviacion ||
      anterior.totalHojas != totalHojas ||
      anterior.tope != tope ||
      anterior.desde != desde ||
      anterior.hasta != hasta;
}
