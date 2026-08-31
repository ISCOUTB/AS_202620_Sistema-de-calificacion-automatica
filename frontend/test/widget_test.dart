import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/pantalla_carga.dart';
import 'package:frontend/pantalla_inicio.dart';
import 'package:frontend/servicio_carga.dart';

final _hoja = ArchivoSeleccionado(
  nombre: 'hoja1.jpg',
  contenido: Uint8List.fromList(const [1, 2, 3]),
);

/// Monta la pantalla de carga con las dos operaciones sustituidas: ni diálogo de archivos ni
/// backend. Es lo que permite probar el aspecto A-01 del lado del docente sin levantar nada.
Widget _pantallaCarga({
  List<ArchivoSeleccionado>? seleccion,
  Future<ResultadoCarga> Function(String, List<ArchivoSeleccionado>)? subir,
}) {
  return MaterialApp(
    home: PantallaCarga(
      seleccionarArchivos: () async => seleccion ?? [_hoja],
      subirHojas: subir ??
          (examenId, archivos) async => ResultadoCarga(
                totalProcesados: archivos.length,
                aceptadas: const [],
                rechazados: const [],
              ),
    ),
  );
}

void main() {
  testWidgets('Muestra el nombre del sistema y confirma la conexión con el backend',
      (tester) async {
    await tester.pumpWidget(MaterialApp(
      home: PantallaInicio(verificarSalud: () async => true),
    ));

    expect(find.text(nombreSistema), findsWidgets);

    await tester.pumpAndSettle();

    expect(find.text('Conectado al backend'), findsOneWidget);
  });

  testWidgets('Muestra un mensaje de falla cuando no puede alcanzar al backend',
      (tester) async {
    await tester.pumpWidget(MaterialApp(
      home: PantallaInicio(verificarSalud: () async => false),
    ));

    await tester.pumpAndSettle();

    expect(find.text('No se pudo conectar al backend'), findsOneWidget);
  });

  testWidgets('No ofrece cargar hojas si el backend no responde', (tester) async {
    await tester.pumpWidget(MaterialApp(
      home: PantallaInicio(verificarSalud: () async => false),
    ));
    await tester.pumpAndSettle();

    final boton = tester.widget<FilledButton>(find.byType(FilledButton));
    expect(boton.onPressed, isNull);
  });

  testWidgets('El botón de subir sigue deshabilitado sin examen o sin archivos',
      (tester) async {
    await tester.pumpWidget(_pantallaCarga());
    await tester.pumpAndSettle();

    FilledButton subir() => tester.widget<FilledButton>(find.byType(FilledButton));

    expect(subir().onPressed, isNull, reason: 'sin examen ni archivos');

    await tester.enterText(find.byType(TextField), 'CALC-2026-01');
    await tester.pumpAndSettle();
    expect(subir().onPressed, isNull, reason: 'hay examen pero no hay archivos');

    await tester.tap(find.text('Seleccionar hojas'));
    await tester.pumpAndSettle();
    expect(subir().onPressed, isNotNull, reason: 'ya hay examen y archivos');
  });

  testWidgets('El reporte muestra las aceptadas y las rechazadas con su motivo',
      (tester) async {
    await tester.pumpWidget(_pantallaCarga(
      subir: (examenId, archivos) async => const ResultadoCarga(
        totalProcesados: 2,
        aceptadas: [HojaAceptada(nombreArchivo: 'hoja1.jpg', trabajoId: 'abc-123')],
        rechazados: [
          ArchivoRechazado(nombreArchivo: 'apuntes.txt', motivo: 'Extensión no admitida (.txt).'),
        ],
      ),
    ));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), 'CALC-2026-01');
    await tester.tap(find.text('Seleccionar hojas'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Subir al sistema'));
    await tester.pumpAndSettle();

    // El total es la parte visible de EC-07: el docente puede contar lo que subió contra lo
    // que el sistema dice haber procesado.
    expect(find.text('Se procesaron 2 archivo(s)'), findsOneWidget);
    expect(find.text('hoja1.jpg'), findsOneWidget);
    expect(find.text('apuntes.txt'), findsOneWidget);
    expect(find.text('Extensión no admitida (.txt).'), findsOneWidget);
  });

  testWidgets('Una falla de red se muestra como aviso, no como rechazo', (tester) async {
    await tester.pumpWidget(_pantallaCarga(
      subir: (examenId, archivos) async =>
          throw const ExcepcionDeCarga('No se pudo contactar al backend.'),
    ));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), 'CALC-2026-01');
    await tester.tap(find.text('Seleccionar hojas'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Subir al sistema'));
    await tester.pumpAndSettle();

    expect(find.text('No se pudo contactar al backend.'), findsOneWidget);
    expect(find.textContaining('Se procesaron'), findsNothing);
  });
}
