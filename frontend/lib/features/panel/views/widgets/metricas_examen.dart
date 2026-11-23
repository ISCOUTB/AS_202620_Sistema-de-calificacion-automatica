import 'package:flutter/material.dart';

import '../../../../common/tema/tema.dart';
import '../../../../common/tema/tokens.dart';
import '../../../../common/widgets/q_chip_estado.dart';
import '../../../../common/widgets/q_tarjeta.dart';
import '../../data/modelos_panel.dart';
import '../formato_cifras.dart';
import 'cuadricula_adaptable.dart';

/// Las cuatro cifras de cabecera del examen activo: promedio, aprobación, hojas recibidas y
/// preguntas que esperan revisión manual. Todas salen de las hojas que el sistema leyó
/// (ADR-0028); las notas provisionales cuentan, con lo pendiente en cero hasta que se resuelva.
class MetricasExamen extends StatelessWidget {
  const MetricasExamen({super.key, required this.resumen, required this.columnas});

  final ResumenExamen resumen;
  final int columnas;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    final pieSuave = textos.bodySmall;

    final promedio = resumen.promedio;
    final cifraPromedio = promedio == null ? '—' : formatearDecimal(promedio);
    final maxima = formatearDecimal(resumen.notaMaxima);
    final aprobacion = formatearPorcentaje(resumen.porcentajeAprobacion, decimales: 1);
    final aprobatoria = formatearDecimal(resumen.notaAprobatoria);
    final desviacion = resumen.desviacion;
    final conNota = resumen.hojasConNota;
    final hojasConNota = conNota == 1 ? '1 hoja' : '$conNota hojas';
    final porLeer = resumen.porLeer;
    final ilegibles = resumen.hojasIlegibles;
    final pendientes = resumen.preguntasPorRevisar;
    final enRevision = resumen.hojasEnRevision;

    final Widget pieHojas;
    if (porLeer > 0) {
      pieHojas = QChipEstado(
        texto: porLeer == 1 ? 'Falta 1 por leer' : 'Faltan $porLeer por leer',
        tono: QTono.info,
        icono: Icons.hourglass_top_outlined,
      );
    } else if (ilegibles > 0) {
      pieHojas = QChipEstado(
        texto: ilegibles == 1 ? '1 ilegible: vuelva a escanearla' : '$ilegibles ilegibles',
        tono: QTono.advertencia,
        icono: Icons.warning_amber_outlined,
      );
    } else if (resumen.hojasRecibidas == 0) {
      pieHojas = Text('Todavía no se ha subido ninguna hoja', style: pieSuave);
    } else {
      pieHojas = const QChipEstado(
        texto: 'Todas leídas',
        tono: QTono.exito,
        icono: Icons.check_circle_outline,
      );
    }

    return CuadriculaAdaptable(
      columnas: columnas,
      children: [
        _TarjetaMetrica(
          etiqueta: 'Promedio del curso',
          icono: Icons.trending_up_outlined,
          colorIcono: QTono.info.texto,
          cifra: cifraPromedio,
          unidad: '/ $maxima',
          semantica: promedio == null
              ? 'Promedio del curso: todavía no hay hojas con nota.'
              : 'Promedio del curso: $cifraPromedio de $maxima, en $hojasConNota con nota.',
          pie: Text(
            promedio == null
                ? 'Aún no hay hojas con nota'
                : desviacion == null
                    ? 'De $hojasConNota con nota'
                    : 'De $hojasConNota con nota · desviación ${formatearDecimal(desviacion)}',
            style: pieSuave,
          ),
        ),
        _TarjetaMetrica(
          etiqueta: 'Aprobación',
          icono: Icons.verified_outlined,
          colorIcono: QTono.exito.texto,
          cifra: aprobacion,
          semantica: 'Aprobación: $aprobacion. ${resumen.aprobados} de $conNota '
              'hojas con nota de $aprobatoria o más.',
          pie: Text(
            '${resumen.aprobados} de $conNota con nota de $aprobatoria o más',
            style: pieSuave,
          ),
        ),
        _TarjetaMetrica(
          etiqueta: 'Hojas recibidas',
          icono: Icons.document_scanner_outlined,
          colorIcono: QTono.info.texto,
          cifra: '${resumen.hojasRecibidas}',
          unidad: resumen.hojasSinNota > 0 ? '· ${resumen.hojasSinNota} sin nota' : null,
          semantica: 'Hojas recibidas: ${resumen.hojasRecibidas}. Leídas: '
              '${resumen.hojasLeidas}. Con nota: $conNota. Ilegibles: $ilegibles.',
          pie: pieHojas,
        ),
        _TarjetaMetrica(
          etiqueta: 'Revisión pendiente',
          colorEtiqueta: pendientes > 0 ? QTono.advertencia.texto : null,
          icono: Icons.rate_review_outlined,
          colorIcono: pendientes > 0 ? QTono.advertencia.texto : QTono.neutro.texto,
          cifra: '$pendientes',
          colorCifra: pendientes > 0 ? QTono.advertencia.texto : null,
          unidad: pendientes == 1 ? 'marca' : 'marcas',
          semantica: 'Revisión pendiente: $pendientes '
              '${pendientes == 1 ? 'marca' : 'marcas'} en $enRevision '
              '${enRevision == 1 ? 'hoja' : 'hojas'}.',
          pie: Text(
            pendientes == 0
                ? 'Nada espera su revisión'
                : 'Tenues, borrosas o dobles, en $enRevision '
                    '${enRevision == 1 ? 'hoja' : 'hojas'}',
            style: pieSuave,
          ),
        ),
      ],
    );
  }
}

/// Una métrica: etiqueta e ícono arriba, la cifra grande y una línea que la explica.
///
/// Se lee como un solo nodo de accesibilidad con [semantica], que dice la cifra con su contexto
/// («3,7 de 5,0»); leídos por separado, «3,7» y «/ 5,0» no se entienden.
class _TarjetaMetrica extends StatelessWidget {
  const _TarjetaMetrica({
    required this.etiqueta,
    required this.icono,
    required this.colorIcono,
    required this.cifra,
    required this.semantica,
    required this.pie,
    this.unidad,
    this.colorCifra,
    this.colorEtiqueta,
  });

  final String etiqueta;
  final IconData icono;
  final Color colorIcono;
  final String cifra;
  final String? unidad;
  final Color? colorCifra;
  final Color? colorEtiqueta;
  final String semantica;
  final Widget pie;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    return Semantics(
      container: true,
      label: semantica,
      child: ExcludeSemantics(
        child: QTarjeta(
          padding: const EdgeInsets.all(QEspacios.lg - 4),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      etiqueta,
                      style: textos.labelLarge?.copyWith(
                        color: colorEtiqueta ?? QColores.textoSuave,
                      ),
                    ),
                  ),
                  Icon(icono, size: 20, color: colorIcono),
                ],
              ),
              const SizedBox(height: QEspacios.sm),
              Wrap(
                crossAxisAlignment: WrapCrossAlignment.end,
                spacing: QEspacios.sm - 2,
                children: [
                  Text(
                    cifra,
                    style: QTexto.cifraGrande.copyWith(color: colorCifra),
                  ),
                  if (unidad != null)
                    Padding(
                      padding: const EdgeInsetsDirectional.only(bottom: 4),
                      child: Text(
                        unidad!,
                        style: textos.bodyLarge?.copyWith(
                          color: QColores.textoSuave,
                          fontFeatures: const [FontFeature.tabularFigures()],
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: QEspacios.sm + 4),
              pie,
            ],
          ),
        ),
      ),
    );
  }
}
