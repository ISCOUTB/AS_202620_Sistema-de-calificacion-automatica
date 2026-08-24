import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/pantalla_inicio.dart';

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
}
