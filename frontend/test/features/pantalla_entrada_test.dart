import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/common/api/sesion.dart';
import 'package:frontend/common/tema/tema.dart';
import 'package:frontend/features/sesion/views/pantalla_entrada.dart';

typedef _Entrada = ({String correo, String contrasena, bool recordar});

Future<List<_Entrada>> _montar(
  WidgetTester tester, {
  Future<void> Function()? respuesta,
  String? aviso,
  Size tamano = const Size(400, 860),
}) async {
  tester.view.physicalSize = tamano;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  final entradas = <_Entrada>[];
  await tester.pumpWidget(MaterialApp(
    theme: construirTema(),
    home: PantallaEntrada(
      aviso: aviso,
      alEntrar: (correo, contrasena, recordar) async {
        entradas.add((correo: correo, contrasena: contrasena, recordar: recordar));
        await respuesta?.call();
      },
    ),
  ));
  return entradas;
}

Finder _campo(String etiqueta) => find.widgetWithText(TextField, etiqueta);

void main() {
  testWidgets('Muestra la bienvenida, el correo, la contraseña y «Recordar sesión»', (tester) async {
    await _montar(tester);

    expect(find.text('Bienvenido a QuantIA'), findsOneWidget);
    expect(find.text('Portal docente UTB'), findsOneWidget);
    expect(_campo('Correo institucional'), findsOneWidget);
    expect(_campo('Contraseña del docente'), findsOneWidget);
    expect(find.text('Recordar sesión en este dispositivo'), findsOneWidget);
    expect(find.widgetWithText(FilledButton, 'Iniciar sesión'), findsOneWidget);
  });

  testWidgets('No ofrece nada que QuantIA no hace', (tester) async {
    await _montar(tester);

    for (final texto in ['SAVIO', 'Microsoft', 'Olvidaste', 'federada', 'Ley 1581', 'Exclusivo']) {
      expect(find.textContaining(texto), findsNothing, reason: texto);
    }
  });

  testWidgets('Entra con el correo sin espacios, la contraseña y si recordar', (tester) async {
    final entradas = await _montar(tester);

    await tester.enterText(_campo('Correo institucional'), '  profe@utb.edu.co ');
    await tester.enterText(_campo('Contraseña del docente'), 'calculo-diferencial');
    await tester.tap(find.text('Recordar sesión en este dispositivo'));
    await tester.tap(find.text('Iniciar sesión'));
    await tester.pumpAndSettle();

    expect(entradas, [(correo: 'profe@utb.edu.co', contrasena: 'calculo-diferencial', recordar: true)]);
  });

  testWidgets('Enter en la contraseña también entra', (tester) async {
    final entradas = await _montar(tester);

    await tester.enterText(_campo('Correo institucional'), 'profe@utb.edu.co');
    await tester.enterText(_campo('Contraseña del docente'), 'calculo-diferencial');
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pumpAndSettle();

    expect(entradas.single.recordar, isFalse);
  });

  testWidgets('Sin correo válido o sin contraseña no llama a la API y dice qué falta', (tester) async {
    final entradas = await _montar(tester);

    await tester.tap(find.text('Iniciar sesión'));
    await tester.pump();
    expect(find.text('Escriba su correo y su contraseña.'), findsOneWidget);

    await tester.enterText(_campo('Correo institucional'), 'profe');
    await tester.enterText(_campo('Contraseña del docente'), 'calculo-diferencial');
    await tester.tap(find.text('Iniciar sesión'));
    await tester.pump();
    expect(find.text('Escriba el correo completo, con @.'), findsOneWidget);

    expect(entradas, isEmpty);
  });

  testWidgets('Si la API no deja entrar, muestra su motivo y se puede reintentar', (tester) async {
    var intentos = 0;
    await _montar(tester, respuesta: () async {
      intentos++;
      if (intentos == 1) throw const ExcepcionDeSesion('El correo o la contraseña no coinciden.');
    });

    await tester.enterText(_campo('Correo institucional'), 'profe@utb.edu.co');
    await tester.enterText(_campo('Contraseña del docente'), 'otra-cosa');
    await tester.tap(find.text('Iniciar sesión'));
    await tester.pumpAndSettle();

    expect(find.text('El correo o la contraseña no coinciden.'), findsOneWidget);

    await tester.tap(find.text('Iniciar sesión'));
    await tester.pumpAndSettle();

    expect(intentos, 2);
    expect(find.text('El correo o la contraseña no coinciden.'), findsNothing);
  });

  testWidgets('Mientras entra, el botón no se puede volver a pulsar', (tester) async {
    final entradas = await _montar(tester, respuesta: () => Future.delayed(const Duration(seconds: 1)));

    await tester.enterText(_campo('Correo institucional'), 'profe@utb.edu.co');
    await tester.enterText(_campo('Contraseña del docente'), 'calculo-diferencial');
    await tester.tap(find.text('Iniciar sesión'));
    await tester.pump();
    await tester.tap(find.byType(FilledButton), warnIfMissed: false);
    await tester.pump(const Duration(seconds: 2));

    expect(entradas, hasLength(1));
  });

  testWidgets('El ojo muestra y oculta la contraseña', (tester) async {
    await _montar(tester);
    bool oculta() => tester
        .widget<TextField>(_campo('Contraseña del docente'))
        .obscureText;

    expect(oculta(), isTrue);
    await tester.tap(find.byTooltip('Mostrar la contraseña'));
    await tester.pump();
    expect(oculta(), isFalse);
    await tester.tap(find.byTooltip('Ocultar la contraseña'));
    await tester.pump();
    expect(oculta(), isTrue);
  });

  testWidgets('Muestra el aviso de por qué volvió a la entrada', (tester) async {
    await _montar(tester, aviso: 'Su sesión terminó. Vuelva a entrar.');

    expect(find.text('Su sesión terminó. Vuelva a entrar.'), findsOneWidget);
  });

  testWidgets('Cabe en un teléfono y en una pantalla ancha sin desbordarse', (tester) async {
    await _montar(tester, tamano: const Size(320, 640));
    expect(tester.takeException(), isNull);

    await _montar(tester, tamano: const Size(1440, 900));
    expect(tester.takeException(), isNull);
  });
}
