import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../../../common/tema/tema.dart';
import '../../../../common/tema/tokens.dart';
import '../../../../common/widgets/q_chip_estado.dart';
import '../../../../common/widgets/q_tarjeta.dart';
import '../../data/datos_ejemplo_revision.dart';
import '../formato_revision.dart';

/// Rendimiento del grupo: aprobados, promedio, reprobados y la distribución de notas de 0 a 5.
///
/// Las cifras salen de [ResumenNotas], que solo cuenta notas definitivas: una nota tentativa entra
/// cuando el docente resuelve su marca, y la tarjeta lo dice.
class ResumenGrupo extends StatelessWidget {
  const ResumenGrupo({
    super.key,
    required this.resumen,
    required this.pendientes,
    required this.compacto,
  });

  final ResumenNotas resumen;
  final int pendientes;
  final bool compacto;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    final r = resumen;
    final promedio = formatearDecimal(r.promedioDecimas / 10);
    final nota = switch (pendientes) {
      0 => 'Calculado sobre los ${r.calificados} estudiantes; ya no hay notas tentativas.',
      1 => 'Calculado sobre los ${r.calificados} estudiantes calificados. La nota en revisión '
          'entra cuando usted la resuelva.',
      _ => 'Calculado sobre los ${r.calificados} estudiantes calificados. Las $pendientes notas '
          'en revisión entran cuando usted las resuelva.',
    };

    return QTarjeta(
      padding: EdgeInsets.all(compacto ? QEspacios.md : QEspacios.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('Rendimiento del grupo', style: textos.titleSmall),
          const SizedBox(height: QEspacios.md),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: _Cifra(
                  etiqueta: 'Aprobados',
                  valor: formatearPorcentaje(r.porcentajeAprobados),
                  detalle: '${r.aprobados} de ${r.calificados}',
                ),
              ),
              const SizedBox(width: QEspacios.sm),
              Expanded(
                child: _Cifra(etiqueta: 'Promedio', valor: promedio, detalle: 'sobre 5,0'),
              ),
              const SizedBox(width: QEspacios.sm),
              Expanded(
                child: _Cifra(
                  etiqueta: 'Reprobados',
                  valor: '${r.reprobados}',
                  detalle: 'con menos de 3,0',
                ),
              ),
            ],
          ),
          const SizedBox(height: QEspacios.lg),
          HistogramaNotas(resumen: r),
          const SizedBox(height: QEspacios.md),
          Text(nota, style: textos.bodySmall),
        ],
      ),
    );
  }
}

class _Cifra extends StatelessWidget {
  const _Cifra({required this.etiqueta, required this.valor, required this.detalle});

  final String etiqueta;
  final String valor;
  final String detalle;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    return MergeSemantics(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(etiqueta, style: textos.labelMedium?.copyWith(color: QColores.textoSuave)),
          Text(valor, style: QTexto.cifra),
          Text(detalle, style: textos.bodySmall),
        ],
      ),
    );
  }
}

/// Histograma de notas sobre la escala de 0,0 a 5,0, con la línea de corte en 3,0 y el promedio.
///
/// Cada barra cubre dos décimas (3,0 y 3,1 van juntas), así que la línea de corte cae justo en
/// el borde entre reprobados y aprobados. Verde y rojo nunca van solos: la leyenda los nombra y la
/// etiqueta accesible da las cifras.
class HistogramaNotas extends StatelessWidget {
  const HistogramaNotas({super.key, required this.resumen});

  final ResumenNotas resumen;

  /// 26 cubetas de dos décimas: de [0,0; 0,2) hasta [5,0; 5,2), para que el 5,0 tenga su barra.
  static const cubetas = 26;

  /// Posición del corte en el eje, como fracción del ancho.
  static double get fraccionCorte => (corteAprobacionDecimas / 2) / cubetas;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    final r = resumen;
    final promedio = formatearDecimal(r.promedioDecimas / 10);
    final estiloEje = textos.labelMedium?.copyWith(color: QColores.textoSuave);

    return Semantics(
      container: true,
      label: 'Distribución de las ${r.calificados} notas calificadas, de 0 a 5: '
          '${r.aprobados} en 3,0 o más y ${r.reprobados} por debajo del corte de 3,0. '
          'Promedio $promedio.',
      child: ExcludeSemantics(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            SizedBox(
              height: 72,
              child: CustomPaint(
                painter: _PintorHistograma(
                  conteo: r.conteoPorNota,
                  promedioDecimas: r.promedioDecimas,
                ),
              ),
            ),
            const SizedBox(height: QEspacios.xs),
            Stack(
              children: [
                Align(
                  alignment: AlignmentDirectional.centerStart,
                  child: Text('0,0', style: estiloEje),
                ),
                // Alignment ubica el mismo punto relativo del texto y del eje: el rótulo queda
                // casi centrado en la línea, a pocos píxeles, sin medir el texto.
                Align(
                  alignment: Alignment(fraccionCorte * 2 - 1, 0),
                  child: Text('Corte 3,0', style: estiloEje?.copyWith(color: QColores.navy)),
                ),
                Align(
                  alignment: AlignmentDirectional.centerEnd,
                  child: Text('5,0', style: estiloEje),
                ),
              ],
            ),
            const SizedBox(height: QEspacios.sm),
            Wrap(
              spacing: QEspacios.md,
              runSpacing: QEspacios.xs,
              children: [
                const _Leyenda(color: QColores.exitoTexto, texto: 'Aprobado (3,0 o más)'),
                const _Leyenda(color: QColores.errorTexto, texto: 'Reprobado'),
                _Leyenda(color: QColores.navy, texto: 'Promedio $promedio', circulo: true),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _Leyenda extends StatelessWidget {
  const _Leyenda({required this.color, required this.texto, this.circulo = false});

  final Color color;
  final String texto;
  final bool circulo;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 10,
          height: circulo ? 10 : 12,
          decoration: BoxDecoration(
            color: color,
            shape: circulo ? BoxShape.circle : BoxShape.rectangle,
            borderRadius: circulo ? null : const BorderRadius.vertical(top: Radius.circular(2)),
          ),
        ),
        const SizedBox(width: 6),
        Text(texto, style: Theme.of(context).textTheme.bodySmall),
      ],
    );
  }
}

class _PintorHistograma extends CustomPainter {
  _PintorHistograma({required this.conteo, required this.promedioDecimas});

  final Map<int, int> conteo;
  final double promedioDecimas;

  @override
  void paint(Canvas canvas, Size size) {
    const cubetas = HistogramaNotas.cubetas;
    final ancho = size.width / cubetas;
    // Espacio bajo la línea base para el marcador del promedio.
    final base = size.height - 8;
    final alturaUtil = base - 4;

    final porCubeta = <int, int>{};
    conteo.forEach((nota, n) {
      final c = (nota ~/ 2).clamp(0, cubetas - 1);
      porCubeta[c] = (porCubeta[c] ?? 0) + n;
    });
    final mayor = porCubeta.values.fold<int>(1, (m, n) => n > m ? n : m);

    canvas.drawLine(
      Offset(0, base),
      Offset(size.width, base),
      Paint()
        ..color = QColores.bordeCampo
        ..strokeWidth = 1,
    );

    // Barras finas con 2 px de aire entre vecinas y la punta redondeada; el color dice de qué
    // lado del corte está la nota.
    porCubeta.forEach((c, n) {
      final alto = (n / mayor * alturaUtil).clamp(3.0, alturaUtil);
      final aprobada = c * 2 >= corteAprobacionDecimas;
      canvas.drawRRect(
        RRect.fromRectAndCorners(
          Rect.fromLTWH(c * ancho + 1, base - alto, ancho - 2, alto),
          topLeft: const Radius.circular(2),
          topRight: const Radius.circular(2),
        ),
        Paint()..color = aprobada ? QColores.exitoTexto : QColores.errorTexto,
      );
    });

    // Línea de corte punteada en 3,0.
    final xCorte = HistogramaNotas.fraccionCorte * size.width;
    final pincelCorte = Paint()
      ..color = QColores.navy
      ..strokeWidth = 1.5;
    for (var y = 0.0; y < base + 4; y += 6) {
      canvas.drawLine(Offset(xCorte, y), Offset(xCorte, (y + 3).clamp(0, base + 4)), pincelCorte);
    }

    // Promedio: un punto navy sobre la línea base, con aro blanco para separarlo de las barras.
    final xPromedio = (promedioDecimas / 2 / cubetas) * size.width;
    canvas.drawCircle(Offset(xPromedio, base), 7, Paint()..color = QColores.superficie);
    canvas.drawCircle(Offset(xPromedio, base), 5, Paint()..color = QColores.navy);
  }

  @override
  bool shouldRepaint(covariant _PintorHistograma anterior) =>
      anterior.promedioDecimas != promedioDecimas || !mapEquals(anterior.conteo, conteo);
}

/// Filtro en píldora con su conteo. Se dibuja aparte en vez de usar `ChoiceChip` para asegurar
/// los 48 px de objetivo táctil también en escritorio, donde Material los reduce a 32.
class FiltroPildora extends StatelessWidget {
  const FiltroPildora({
    super.key,
    required this.etiqueta,
    required this.icono,
    required this.colorIcono,
    required this.conteo,
    required this.seleccionado,
    required this.alPresionar,
  });

  final String etiqueta;
  final IconData icono;
  final Color colorIcono;
  final int conteo;
  final bool seleccionado;
  final VoidCallback alPresionar;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    final colorTexto = seleccionado ? QColores.textoSobreNavy : QColores.texto;
    final forma = RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(QRadios.pildora),
      side: BorderSide(color: seleccionado ? QColores.cobalto : QColores.bordeCampo),
    );

    return Semantics(
      button: true,
      selected: seleccionado,
      label: '$etiqueta, $conteo ${conteo == 1 ? 'estudiante' : 'estudiantes'}',
      child: Material(
        color: seleccionado ? QColores.cobalto : QColores.superficie,
        shape: forma,
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: alPresionar,
          child: ConstrainedBox(
            constraints: const BoxConstraints(minHeight: 48),
            child: Padding(
              padding: const EdgeInsetsDirectional.fromSTEB(14, 0, 10, 0),
              child: ExcludeSemantics(
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      icono,
                      size: 18,
                      color: seleccionado ? QColores.textoSobreNavy : colorIcono,
                    ),
                    const SizedBox(width: QEspacios.sm),
                    Flexible(
                      child: Text(
                        etiqueta,
                        style: textos.labelLarge?.copyWith(color: colorTexto),
                      ),
                    ),
                    const SizedBox(width: QEspacios.sm),
                    Container(
                      constraints: const BoxConstraints(minWidth: 24),
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: seleccionado
                            ? QColores.superficie
                            : QColores.superficieAzulMedia,
                        borderRadius: BorderRadius.circular(QRadios.pildora),
                      ),
                      child: Text(
                        '$conteo',
                        textAlign: TextAlign.center,
                        style: textos.labelMedium?.copyWith(
                          color: seleccionado ? QColores.cobaltoOscuro : QColores.texto,
                          fontFeatures: const [FontFeature.tabularFigures()],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Tarjeta compacta de un estudiante: nombre, código, confianza de la lectura, nota y desempeño.
/// El riel dice el estado (naranja por revisar, rojo reprobado, verde aprobado) y el texto lo
/// repite, para quien no distingue los colores.
class TarjetaEstudiante extends StatelessWidget {
  const TarjetaEstudiante({super.key, required this.fila});

  final FilaEstudiante fila;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    final e = fila.estudiante;
    final desempeno = fila.desempeno;
    final (tono, icono) = switch (desempeno) {
      Desempeno.excelente => (QTono.exito, Icons.emoji_events_outlined),
      Desempeno.bueno => (QTono.exito, Icons.thumb_up_outlined),
      Desempeno.aprobado => (QTono.neutro, Icons.check_outlined),
      Desempeno.reprobado => (QTono.error, Icons.flag_outlined),
      Desempeno.porRevisar => (QTono.advertencia, Icons.pending_outlined),
    };
    final riel = switch (desempeno) {
      Desempeno.porRevisar => QColores.advertencia,
      Desempeno.reprobado => QColores.error,
      _ => QColores.exito,
    };
    final confianza = formatearPorcentaje(e.confianzaOmr);
    final chipLectura = fila.pendiente
        ? QChipEstado(
            texto: 'Confianza $confianza',
            tono: QTono.advertencia,
            icono: Icons.warning_amber_outlined,
            pildora: true,
          )
        : fila.revisadaAMano
            ? const QChipEstado(
                texto: 'Revisada por usted',
                tono: QTono.info,
                icono: Icons.fact_check_outlined,
                pildora: true,
              )
            : QChipEstado(
                texto: 'Confianza $confianza',
                tono: QTono.exito,
                icono: Icons.check_circle_outline,
                pildora: true,
              );
    final nota = formatearNota(fila.notaDecimas);
    final lectura = fila.pendiente
        ? 'Lectura con $confianza de confianza, por revisar'
        : fila.revisadaAMano
            ? 'Lectura revisada por usted'
            : 'Lectura con $confianza de confianza';

    return Semantics(
      container: true,
      label: '${e.nombreCompleto}, código ${e.codigo}. '
          'Nota $nota de 5,0${fila.pendiente ? ', tentativa' : ''}: ${desempeno.etiqueta}. '
          '$lectura.',
      child: ExcludeSemantics(
        child: QTarjeta(
          riel: riel,
          padding: const EdgeInsetsDirectional.fromSTEB(
            QEspacios.md,
            QEspacios.sm + 4,
            QEspacios.md,
            QEspacios.sm + 4,
          ),
          child: Row(
            children: [
              AvatarIniciales(iniciales: e.iniciales),
              const SizedBox(width: QEspacios.sm + 4),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      e.nombreCompleto,
                      style: textos.titleSmall,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 2),
                    Text(e.codigo, style: QTexto.codigo),
                    const SizedBox(height: 6),
                    chipLectura,
                  ],
                ),
              ),
              const SizedBox(width: QEspacios.sm),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text.rich(
                    TextSpan(
                      children: [
                        TextSpan(
                          text: nota,
                          style: QTexto.cifra.copyWith(
                            color: fila.pendiente ? QColores.textoSuave : QColores.navy,
                          ),
                        ),
                        TextSpan(text: ' / 5,0', style: textos.bodySmall),
                      ],
                    ),
                  ),
                  const SizedBox(height: QEspacios.xs),
                  QChipEstado(texto: desempeno.etiqueta, tono: tono, icono: icono),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
