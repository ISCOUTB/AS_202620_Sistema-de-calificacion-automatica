import 'package:flutter/material.dart';

import '../../../../common/tema/tema.dart';
import '../../../../common/tema/tokens.dart';
import '../../../../common/widgets/q_chip_estado.dart';
import '../../../../common/widgets/q_tarjeta.dart';
import '../../data/modelos_panel.dart';
import '../formato_cifras.dart';
import 'cuadricula_adaptable.dart';

/// Las cuatro cifras de cabecera del examen activo: promedio, aprobación, hojas recibidas y
/// marcas que esperan revisión manual.
class MetricasExamen extends StatelessWidget {
  const MetricasExamen({super.key, required this.resumen, required this.columnas});

  final ResumenExamen resumen;
  final int columnas;

  @override
  Widget build(BuildContext context) {
    final textos = Theme.of(context).textTheme;
    final pieSuave = textos.bodySmall;

    final promedio = formatearDecimal(resumen.promedio);
    final maxima = formatearDecimal(resumen.notaMaxima);
    final aprobacion = formatearPorcentaje(resumen.porcentajeAprobacion, decimales: 1);
    final aprobatoria = formatearDecimal(resumen.notaAprobatoria);
    final umbral = formatearPorcentaje(umbralConfianzaPorcentaje);
    final variacion = resumen.variacion;
    final faltan = resumen.estudiantes - resumen.hojasRecibidas;
    final pendientes = resumen.revisionPendiente;

    return CuadriculaAdaptable(
      columnas: columnas,
      children: [
        _TarjetaMetrica(
          etiqueta: 'Promedio del curso',
          icono: Icons.trending_up_outlined,
          colorIcono: QTono.info.texto,
          cifra: promedio,
          unidad: '/ $maxima',
          semantica: 'Promedio del curso: $promedio de $maxima. '
              '${_frasePorVariacion(variacion, resumen.referencia)}',
          pie: variacion == null || resumen.referencia == null
              ? Text('Primer examen del periodo: aún no hay con qué comparar', style: pieSuave)
              : QChipEstado(
                  texto: '${formatearVariacion(variacion)} frente al ${resumen.referencia}',
                  tono: variacion >= 0 ? QTono.exito : QTono.advertencia,
                  icono: variacion >= 0 ? Icons.north_east_outlined : Icons.south_east_outlined,
                ),
        ),
        _TarjetaMetrica(
          etiqueta: 'Aprobación',
          icono: Icons.verified_outlined,
          colorIcono: QTono.exito.texto,
          cifra: aprobacion,
          semantica: 'Aprobación: $aprobacion. ${resumen.aprobados} de ${resumen.estudiantes} '
              'estudiantes con nota de $aprobatoria o más.',
          pie: Text(
            '${resumen.aprobados} de ${resumen.estudiantes} estudiantes con nota de '
            '$aprobatoria o más',
            style: pieSuave,
          ),
        ),
        _TarjetaMetrica(
          etiqueta: 'Hojas recibidas',
          icono: Icons.document_scanner_outlined,
          colorIcono: QTono.info.texto,
          cifra: '${resumen.hojasRecibidas}',
          unidad: 'de ${resumen.estudiantes}',
          semantica: 'Hojas recibidas: ${resumen.hojasRecibidas} de ${resumen.estudiantes}.',
          pie: faltan <= 0
              ? const QChipEstado(
                  texto: 'Grupo completo',
                  tono: QTono.exito,
                  icono: Icons.check_circle_outline,
                )
              : QChipEstado(
                  texto: faltan == 1 ? 'Falta 1 hoja' : 'Faltan $faltan hojas',
                  tono: QTono.advertencia,
                  icono: Icons.warning_amber_outlined,
                ),
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
              '${pendientes == 1 ? 'marca' : 'marcas'} con confianza menor al $umbral.',
          // El 70 % es un supuesto del equipo, no una cifra medida: se dice en la tarjeta para
          // que nadie lo lea como un umbral calibrado.
          pie: Text(
            pendientes > 0
                ? 'Con confianza menor al $umbral (umbral supuesto)'
                : 'Ninguna marca por debajo del $umbral (umbral supuesto)',
            style: pieSuave,
          ),
        ),
      ],
    );
  }

  static String _frasePorVariacion(double? variacion, String? referencia) {
    if (variacion == null || referencia == null) return 'Primer examen del periodo.';
    if (variacion == 0) return 'Igual que en el $referencia.';
    final cuanto = formatearDecimal(variacion.abs());
    return variacion > 0
        ? '$cuanto más que en el $referencia.'
        : '$cuanto menos que en el $referencia.';
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
