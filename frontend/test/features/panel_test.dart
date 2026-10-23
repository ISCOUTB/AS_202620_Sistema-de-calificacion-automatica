import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/common/tema/tema.dart';
import 'package:frontend/common/widgets/q_aviso_datos_ejemplo.dart';
import 'package:frontend/features/panel/data/datos_ejemplo_panel.dart';
import 'package:frontend/features/panel/data/modelos_panel.dart';
import 'package:frontend/features/panel/views/formato_cifras.dart';
import 'package:frontend/features/panel/views/pantalla_panel.dart';

final _parcial2 = cursoEjemplo.examenes[0];
final _parcial1 = cursoEjemplo.examenes[1];

/// Monta el panel a un ancho dado. El alto sobra a propósito: la página se desplaza, y lo que
/// interesa es que nada se desborde a lo ancho.
Future<void> _montar(
  WidgetTester tester, {
  double ancho = 1280,
  bool sinMovimiento = false,
}) async {
  tester.view.physicalSize = Size(ancho, 900);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);

  await tester.pumpWidget(
    MaterialApp(
      theme: construirTema(),
      builder: (context, hijo) => MediaQuery(
        data: MediaQuery.of(context).copyWith(disableAnimations: sinMovimiento),
        child: hijo!,
      ),
      home: const Scaffold(body: PantallaPanel()),
    ),
  );
  await tester.pumpAndSettle();
}

/// Texto que empieza con la letra de una opción y contiene su porcentaje, como «B · 38 % · …».
Finder _leyendaDe(AnalisisPregunta analisis, OpcionRespuesta opcion) {
  final porcentaje = formatearPorcentaje(analisis.porcentaje(opcion));
  return find.byWidgetPredicate(
    (widget) =>
        widget is Text &&
        (widget.data ?? '').startsWith('${opcion.letra} · ') &&
        widget.data!.contains(porcentaje),
  );
}

void main() {
  test('Sin estudiantes, el porcentaje de aprobación es 0 y no NaN', () {
    // La división no protegía el cero, a diferencia de
    // los otros porcentajes del panel. Sin el cambio, da NaN y esta prueba falla.
    const vacio = ResumenExamen(
      promedio: 0,
      estudiantes: 0,
      aprobados: 0,
      hojasRecibidas: 0,
      revisionPendiente: 0,
    );

    expect(vacio.porcentajeAprobacion, 0);
    expect(formatearPorcentaje(vacio.porcentajeAprobacion), isNot(contains('NaN')));
  });

  test('Los datos de ejemplo son coherentes entre sí', () {
    final resumen = _parcial2.resumen;
    expect(formatearPorcentaje(resumen.porcentajeAprobacion, decimales: 1), '74,4 %');

    // La distribución de la pregunta 7 suma 100 % y da las cifras acordadas con el equipo.
    final analisis = _parcial2.analisis;
    expect(analisis.opciones.map(analisis.porcentaje).fold<int>(0, (a, b) => a + b), 100);
    expect(analisis.porcentaje(analisis.distractor), 48);
    expect(analisis.porcentaje(analisis.correcta), 38);

    // El promedio de aciertos por competencia, ponderado por preguntas, cae en el promedio de
    // notas: 3,7 sobre 5,0 en el Parcial 2 y 3,3 en el Parcial 1.
    for (final examen in cursoEjemplo.examenes) {
      final preguntas = examen.competencias.fold<int>(0, (a, c) => a + c.preguntas);
      final aciertos = examen.competencias
          .fold<int>(0, (a, c) => a + c.preguntas * c.porcentajeAciertos);
      final nota = aciertos / preguntas / 100 * examen.resumen.notaMaxima;
      expect(nota, closeTo(examen.resumen.promedio, 0.05), reason: examen.nombre);
    }

    // La variación del Parcial 2 es la diferencia real con el Parcial 1.
    expect(
      resumen.promedio - _parcial1.resumen.promedio,
      closeTo(resumen.variacion!, 1e-9),
    );
  });

  testWidgets('Avisa arriba que la vista usa datos de ejemplo', (tester) async {
    await _montar(tester);

    expect(find.byType(QAvisoDatosEjemplo), findsOneWidget);
    expect(find.textContaining('Vista con datos de ejemplo'), findsOneWidget);
    expect(find.textContaining('(A-02)'), findsOneWidget);
    expect(find.textContaining('(A-03)'), findsOneWidget);
  });

  testWidgets('No saluda a un docente ni ofrece acciones de IA fuera del alcance',
      (tester) async {
    await _montar(tester);

    expect(find.text('Panel del curso'), findsOneWidget);
    expect(find.textContaining('Hola'), findsNothing);
    // ADR-0005: el modelo solo propone distractores; no genera talleres.
    expect(find.textContaining('taller'), findsNothing);
    expect(find.byType(FilledButton), findsNothing);
  });

  testWidgets('Las métricas muestran las cifras de los datos', (tester) async {
    await _montar(tester);
    final resumen = _parcial2.resumen;

    expect(find.text(formatearDecimal(resumen.promedio)), findsOneWidget);
    expect(find.text('+0,4 frente al Parcial 1'), findsOneWidget);
    expect(find.text(formatearPorcentaje(resumen.porcentajeAprobacion, decimales: 1)),
        findsOneWidget);
    expect(find.textContaining('32 de 43'), findsOneWidget);
    expect(find.text('${resumen.hojasRecibidas}'), findsOneWidget);
    expect(find.text('de ${resumen.estudiantes}'), findsOneWidget);
    expect(find.text('${resumen.revisionPendiente}'), findsOneWidget);
    expect(find.textContaining('menor al 70 %'), findsOneWidget);
  });

  testWidgets('La leyenda de la distribución tiene texto para cada opción', (tester) async {
    await _montar(tester);
    final analisis = _parcial2.analisis;

    for (final opcion in analisis.opciones) {
      expect(_leyendaDe(analisis, opcion), findsOneWidget, reason: 'opción ${opcion.letra}');
    }
    // El papel de cada opción va escrito, no solo en el color de la barra.
    expect(find.text('B · 38 % · correcta'), findsOneWidget);
    expect(find.text('C · 48 % · distractor más elegido'), findsOneWidget);

    // La barra se lee con un rótulo que repite la leyenda completa.
    final semantica = tester.getSemantics(
      find.bySemanticsLabel(RegExp('^Distribución de las marcas en la pregunta 7')),
    );
    for (final opcion in analisis.opciones) {
      expect(semantica.label, contains('${opcion.letra} · '));
    }

    expect(find.text(analisis.enunciado), findsOneWidget);
    expect(find.text('6x·cos(x)'), findsOneWidget);
    expect(find.text('6x·cos(3x²)'), findsOneWidget);
  });

  testWidgets('Las competencias muestran el porcentaje de aciertos en texto', (tester) async {
    await _montar(tester);

    for (final competencia in _parcial2.competencias) {
      expect(find.text(competencia.nombre), findsOneWidget);
    }
    expect(find.text('60 %'), findsOneWidget);
    expect(find.text('8 preguntas · incluye la pregunta 7'), findsOneWidget);
  });

  testWidgets('Elegir otro examen cambia el conjunto de datos', (tester) async {
    await _montar(tester);

    await tester.tap(find.text(_parcial2.titulo));
    await tester.pumpAndSettle();
    await tester.tap(find.text(_parcial1.nombre));
    await tester.pumpAndSettle();

    expect(find.text(_parcial1.titulo), findsOneWidget);
    expect(find.textContaining('28 de 43'), findsOneWidget);
    expect(find.textContaining('32 de 43'), findsNothing);
    expect(find.text(_parcial1.analisis.enunciado), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Sin animaciones, el cambio de examen es inmediato', (tester) async {
    await _montar(tester, sinMovimiento: true);

    await tester.tap(find.text(_parcial2.titulo));
    await tester.pumpAndSettle();
    await tester.tap(find.text(_parcial1.nombre));
    await tester.pump();
    await tester.pump();

    expect(find.textContaining('28 de 43'), findsOneWidget);
    expect(find.textContaining('32 de 43'), findsNothing);
  });

  for (final ancho in [390.0, 1280.0]) {
    testWidgets('No se desborda a ${ancho.toInt()} px de ancho', (tester) async {
      await _montar(tester, ancho: ancho);
      expect(tester.takeException(), isNull);

      // También con el menú de exámenes abierto y con el otro conjunto de datos.
      await tester.tap(find.text(_parcial2.titulo));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      await tester.tap(find.text(_parcial1.nombre));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    });
  }
}
