import 'package:flutter/material.dart';

import '../../../common/tema/tokens.dart';
import '../../../common/widgets/q_aviso_datos_ejemplo.dart';
import '../../../common/widgets/q_chip_estado.dart';
import '../../../common/widgets/q_encabezado_pantalla.dart';
import '../../../common/widgets/q_pagina.dart';
import '../data/datos_ejemplo_panel.dart';
import '../data/modelos_panel.dart';
import 'widgets/metricas_examen.dart';
import 'widgets/panel_analisis_pregunta.dart';
import 'widgets/rendimiento_competencias.dart';
import 'widgets/selector_examen.dart';

/// Panel del curso (RF-05): cómo le fue al grupo en un examen y qué pregunta conviene mirar.
///
/// Lo que muestra es de ejemplo en su totalidad, y lo dice arriba: las notas y la estadística por pregunta
/// dependen de la detección de marcas (A-02) y de la calificación (A-03), que no existen todavía.
/// Por eso la pantalla no recibe servicios del marco; cuando existan, se le pasará una función
/// que traiga el resumen del examen, como hacen Carga y Pauta.
///
/// Frente al diseño de Stitch no hay saludo a un docente (no hay cuentas, A-05) ni acciones que
/// el sistema no tiene: exportar a SAVIO, escanear con cámara o pedirle a la IA un taller.
class PantallaPanel extends StatefulWidget {
  const PantallaPanel({super.key});

  @override
  State<PantallaPanel> createState() => _PantallaPanelState();
}

class _PantallaPanelState extends State<PantallaPanel> {
  static const _curso = cursoEjemplo;

  /// Ancho útil desde el que las tarjetas van de a dos. Es [QAnchos.dosColumnas] medido sin los
  /// márgenes de la página (24 px por lado a ese ancho), porque aquí se mide el espacio que deja
  /// [QPagina], no la pantalla entera.
  static const _anchoDosColumnas = QAnchos.dosColumnas - 2 * QEspacios.lg;

  ExamenPanel _examen = _curso.examenes.first;

  void _elegir(ExamenPanel examen) {
    if (examen.id == _examen.id) return;
    setState(() => _examen = examen);
  }

  @override
  Widget build(BuildContext context) {
    final sinMovimiento = MediaQuery.disableAnimationsOf(context);

    return QPagina(
      children: [
        const QAvisoDatosEjemplo(
          detalle: 'Las notas y la estadística por pregunta llegan cuando estén construidas '
              'la detección de marcas (A-02) y la calificación (A-03).',
        ),
        const SizedBox(height: QEspacios.lg),
        QEncabezadoPantalla(
          titulo: 'Panel del curso',
          descripcion:
              '${_curso.asignatura} · ${_curso.grupo} · ${_curso.estudiantes} estudiantes',
          extremo: QChipEstado(
            texto: 'Periodo ${_curso.periodo}',
            tono: QTono.info,
            icono: Icons.event_outlined,
          ),
        ),
        const SizedBox(height: QEspacios.lg),
        SelectorExamen(examenes: _curso.examenes, actual: _examen, alElegir: _elegir),
        const SizedBox(height: QEspacios.lg),
        LayoutBuilder(
          builder: (context, restricciones) {
            final columnas = restricciones.maxWidth >= _anchoDosColumnas ? 2 : 1;
            // Al cambiar de examen las cifras se funden en vez de saltar, para que se note que
            // cambió el conjunto de datos y no solo un número. Sin animación si el sistema
            // pide reducir el movimiento.
            return AnimatedSwitcher(
              duration: sinMovimiento ? Duration.zero : QDuraciones.media,
              switchInCurve: Curves.easeOut,
              switchOutCurve: Curves.easeIn,
              layoutBuilder: (actual, anteriores) => Stack(
                alignment: AlignmentDirectional.topStart,
                children: [...anteriores, if (actual != null) actual],
              ),
              child: _ContenidoExamen(
                key: ValueKey(_examen.id),
                examen: _examen,
                columnas: columnas,
              ),
            );
          },
        ),
      ],
    );
  }
}

/// Lo que depende del examen elegido: métricas, análisis por pregunta y competencias.
class _ContenidoExamen extends StatelessWidget {
  const _ContenidoExamen({super.key, required this.examen, required this.columnas});

  final ExamenPanel examen;
  final int columnas;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        MetricasExamen(resumen: examen.resumen, columnas: columnas),
        const SizedBox(height: QEspacios.xl),
        PanelAnalisisPregunta(analisis: examen.analisis),
        const SizedBox(height: QEspacios.xl),
        RendimientoCompetencias(competencias: examen.competencias, columnas: columnas),
      ],
    );
  }
}
