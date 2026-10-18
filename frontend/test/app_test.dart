import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/app/app.dart';
import 'package:frontend/app/marco_app.dart';
import 'package:frontend/app/servicios.dart';
import 'package:frontend/features/carga/data/servicio_carga.dart';
import 'package:frontend/features/pauta/data/servicio_distractores.dart';
import 'package:frontend/main.dart';

/// Servicios sustitutos: la aplicación entera se monta sin backend y sin diálogo de archivos.
ServiciosApp _servicios({bool apiConectada = true}) => ServiciosApp(
      verificarSalud: () async => apiConectada,
      seleccionarArchivos: () async => [
        ArchivoSeleccionado(nombre: 'hoja1.png', contenido: Uint8List.fromList(const [1, 2, 3])),
      ],
      subirHojas: (examenId, archivos) async => ResultadoCarga(
        totalProcesados: archivos.length,
        aceptadas: const [],
        rechazados: const [],
      ),
      proponerDistractores: (solicitud) async =>
          const ResultadoDistractores(distractores: [], descartados: []),
    );

Future<void> _montar(WidgetTester tester, {required Size tamano, bool apiConectada = true}) async {
  tester.view.physicalSize = tamano;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(QuantiaApp(servicios: _servicios(apiConectada: apiConectada)));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('La barra superior muestra el nombre del sistema y la API conectada',
      (tester) async {
    await _montar(tester, tamano: const Size(1280, 900));

    expect(find.text(nombreSistema), findsOneWidget);
    expect(find.text('API conectada'), findsOneWidget);
  });

  testWidgets('Sin conexión, la barra lo dice y ofrece volver a comprobar', (tester) async {
    await _montar(tester, tamano: const Size(1280, 900), apiConectada: false);

    expect(find.text('Sin conexión con la API'), findsOneWidget);
    expect(find.byTooltip('Volver a comprobar la conexión'), findsOneWidget);
  });

  testWidgets('En escritorio la navegación es un riel lateral con las cuatro secciones',
      (tester) async {
    await _montar(tester, tamano: const Size(1280, 900));

    expect(find.byType(NavigationRail), findsOneWidget);
    expect(find.byType(NavigationBar), findsNothing);
    for (final seccion in Seccion.values) {
      expect(find.text(seccion.etiqueta), findsWidgets);
    }
  });

  testWidgets('En teléfono la navegación es una barra inferior', (tester) async {
    await _montar(tester, tamano: const Size(390, 844));

    expect(find.byType(NavigationBar), findsOneWidget);
    expect(find.byType(NavigationRail), findsNothing);
  });

  testWidgets('Cambiar de sección no pierde lo escrito en otra', (tester) async {
    await _montar(tester, tamano: const Size(1280, 900));

    await tester.tap(find.text(Seccion.carga.etiqueta).last);
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).first, 'CALC-2026-02');

    await tester.tap(find.text(Seccion.panel.etiqueta).last);
    await tester.pumpAndSettle();
    await tester.tap(find.text(Seccion.carga.etiqueta).last);
    await tester.pumpAndSettle();

    expect(find.text('CALC-2026-02'), findsOneWidget);
  });

  test('La sección inicial se lee de la URL y cae al panel si no se reconoce', () {
    expect(seccionDesdeUrl(Uri.parse('https://x/?seccion=carga')), Seccion.carga);
    expect(seccionDesdeUrl(Uri.parse('https://x/?seccion=pauta')), Seccion.pauta);
    expect(seccionDesdeUrl(Uri.parse('https://x/?seccion=otra')), Seccion.panel);
    expect(seccionDesdeUrl(Uri.parse('https://x/')), Seccion.panel);
  });
}
