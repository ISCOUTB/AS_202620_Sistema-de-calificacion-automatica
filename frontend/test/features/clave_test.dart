import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/common/tema/tema.dart';
import 'package:frontend/features/carga/data/servicio_examenes.dart';
import 'package:frontend/features/pauta/data/servicio_clave.dart';
import 'package:frontend/features/pauta/views/widgets/tarjeta_clave.dart';

/// Una API de claves en memoria.
class _Claves {
  _Claves([Map<String, ClaveDelExamen>? iniciales]) : guardadas = {...?iniciales};

  final Map<String, ClaveDelExamen> guardadas;
  final consultados = <String>[];
  final guardados = <(String, List<String>)>[];
  final habilitados = <String>[];

  Future<ClaveDelExamen?> consultar(String examen) async {
    consultados.add(examen);
    return guardadas[examen];
  }

  Future<ClaveDelExamen> guardar(String examen, List<String> respuestas) async {
    guardados.add((examen, respuestas));
    return guardadas[examen] =
        ClaveDelExamen(examenId: examen, respuestas: respuestas, sePuedeCambiar: true);
  }

  Future<ClaveDelExamen> habilitar(String examen) async {
    habilitados.add(examen);
    final clave = guardadas[examen]!;
    return guardadas[examen] = ClaveDelExamen(
      examenId: examen,
      respuestas: clave.respuestas,
      sePuedeCambiar: true,
      habilitadaPor: 'profe@utb.edu.co',
      habilitadaEn: DateTime.utc(2026, 11, 22, 15),
    );
  }
}

Future<void> _montar(WidgetTester tester, _Claves claves,
    {VoidCallback? alCambiar,
    Future<List<ExamenConClave>> Function()? listar,
    Size tamano = const Size(1280, 2400)}) async {
  tester.view.physicalSize = tamano;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(MaterialApp(
    theme: construirTema(),
    home: Scaffold(
      body: SingleChildScrollView(
        child: TarjetaClaveDelExamen(
          listarExamenes:
              listar ?? () async => const [ExamenConClave(examenId: 'QUIZ-1', habilitada: true)],
          consultarClave: claves.consultar,
          guardarClave: claves.guardar,
          habilitarClave: claves.habilitar,
          alCambiar: alCambiar,
        ),
      ),
    ),
  ));
  await tester.pumpAndSettle();
}

Future<void> _escribirExamen(WidgetTester tester, String examen) async {
  await tester.enterText(find.widgetWithText(TextField, 'Examen'), examen);
  await tester.pump(const Duration(milliseconds: 500));
  await tester.pumpAndSettle();
}

Future<void> _pegar(WidgetTester tester, String texto) async {
  await tester.enterText(find.widgetWithText(TextField, 'Pegar las respuestas'), texto);
  await tester.tap(find.text('Llenar'));
  await tester.pumpAndSettle();
}

Future<void> _tocar(WidgetTester tester, Finder buscador) async {
  await tester.ensureVisible(buscador);
  await tester.pumpAndSettle();
  await tester.tap(buscador);
  await tester.pumpAndSettle();
}

List<SegmentedButton<String>> _filas(WidgetTester tester) =>
    tester.widgetList<SegmentedButton<String>>(find.byType(SegmentedButton<String>)).toList();

FilledButton _guardar(WidgetTester tester) =>
    tester.widget<FilledButton>(find.widgetWithText(FilledButton, 'Guardar clave'));

void main() {
  testWidgets('Un examen sin clave empieza con las 40 preguntas vacías', (tester) async {
    final claves = _Claves();
    await _montar(tester, claves);

    await _escribirExamen(tester, 'NUEVO-1');

    expect(claves.consultados, ['NUEVO-1']);
    expect(find.text('Sin clave registrada.'), findsOneWidget);
    expect(_filas(tester), hasLength(40));
    expect(_filas(tester).every((fila) => fila.selected.isEmpty), isTrue);
    expect(_guardar(tester).onPressed, isNull);
  });

  testWidgets('Una clave guardada llena la cuadrícula y dice quién la habilitó', (tester) async {
    final claves = _Claves({
      'QUIZ-1': ClaveDelExamen(
        examenId: 'QUIZ-1',
        respuestas: const ['A', 'C', 'D'],
        sePuedeCambiar: true,
        habilitadaPor: 'profe@utb.edu.co',
        habilitadaEn: DateTime.utc(2026, 11, 22, 15),
      ),
    });
    await _montar(tester, claves);

    await _escribirExamen(tester, 'QUIZ-1');

    expect([for (final fila in _filas(tester)) fila.selected], [{'A'}, {'C'}, {'D'}]);
    expect(find.textContaining('Habilitada por profe@utb.edu.co el 22 nov'), findsOneWidget);
  });

  testWidgets('Pegar las respuestas pide confirmarlas y después llena la cuadrícula', (tester) async {
    await _montar(tester, _Claves());
    await _escribirExamen(tester, 'NUEVO-1');

    await _pegar(tester, '1. a, 2. b, 3. C, 4. D');

    expect(find.text('¿Son estas las respuestas?'), findsOneWidget);
    expect(find.text('Asegúrese de que estas son las respuestas correctas de cada pregunta:'),
        findsOneWidget);
    expect(find.text('1. A'), findsOneWidget);
    expect(find.text('4. D'), findsOneWidget);

    await tester.tap(find.text('Llenar la cuadrícula'));
    await tester.pumpAndSettle();

    expect([for (final fila in _filas(tester)) fila.selected], [{'A'}, {'B'}, {'C'}, {'D'}]);
    expect(find.widgetWithText(TextField, '4'), findsOneWidget);
    expect(_guardar(tester).onPressed, isNotNull);
  });

  testWidgets('«Corregir» cierra el cuadro sin tocar la cuadrícula', (tester) async {
    await _montar(tester, _Claves());
    await _escribirExamen(tester, 'NUEVO-1');

    await _pegar(tester, 'ABCD');
    await tester.tap(find.text('Corregir'));
    await tester.pumpAndSettle();

    expect(_filas(tester), hasLength(40));
    expect(_filas(tester).every((fila) => fila.selected.isEmpty), isTrue);
  });

  testWidgets('Un texto pegado que no sirve dice por qué, sin abrir el cuadro', (tester) async {
    await _montar(tester, _Claves());
    await _escribirExamen(tester, 'NUEVO-1');

    await _pegar(tester, 'ABE');

    expect(find.text('La pregunta 3 dice «E»: solo valen A, B, C y D.'), findsOneWidget);
    expect(find.text('¿Son estas las respuestas?'), findsNothing);
  });

  testWidgets('Guardar manda las respuestas y deja habilitar', (tester) async {
    final claves = _Claves();
    var cambios = 0;
    await _montar(tester, claves, alCambiar: () => cambios++);
    await _escribirExamen(tester, 'NUEVO-1');
    await _pegar(tester, 'ABC');
    await tester.tap(find.text('Llenar la cuadrícula'));
    await tester.pumpAndSettle();

    await _tocar(tester, find.text('Guardar clave'));

    expect(claves.guardados.single.$1, 'NUEVO-1');
    expect(claves.guardados.single.$2, ['A', 'B', 'C']);
    expect(find.text('Guardada, sin habilitar.'), findsOneWidget);
    expect(cambios, 1);
    final habilitar = tester.widget<OutlinedButton>(find.widgetWithText(OutlinedButton, 'Habilitar'));
    expect(habilitar.onPressed, isNotNull);
  });

  testWidgets('Guardar agrega el examen a «Con clave:» sin recargar la página', (tester) async {
    final claves = _Claves();
    await _montar(tester, claves, listar: () async => [
          for (final clave in claves.guardadas.values)
            ExamenConClave(examenId: clave.examenId, habilitada: clave.habilitadaPor != null),
        ]);
    await _escribirExamen(tester, 'NUEVO-1');
    await _pegar(tester, 'ABC');
    await tester.tap(find.text('Llenar la cuadrícula'));
    await tester.pumpAndSettle();
    expect(find.widgetWithText(ActionChip, 'NUEVO-1'), findsNothing);

    await _tocar(tester, find.text('Guardar clave'));

    expect(find.widgetWithText(ActionChip, 'NUEVO-1'), findsOneWidget);
  });

  testWidgets('Habilitar pide confirmación y queda a nombre del docente', (tester) async {
    final claves = _Claves({
      'QUIZ-1': const ClaveDelExamen(examenId: 'QUIZ-1', respuestas: ['A'], sePuedeCambiar: true),
    });
    var cambios = 0;
    await _montar(tester, claves, alCambiar: () => cambios++);
    await _escribirExamen(tester, 'QUIZ-1');

    await _tocar(tester, find.widgetWithText(OutlinedButton, 'Habilitar'));
    expect(find.text('¿Habilitar la clave de QUIZ-1?'), findsOneWidget);
    await tester.tap(find.text('Cancelar'));
    await tester.pumpAndSettle();
    expect(claves.habilitados, isEmpty);

    await _tocar(tester, find.widgetWithText(OutlinedButton, 'Habilitar'));
    await tester.tap(find.widgetWithText(FilledButton, 'Habilitar'));
    await tester.pumpAndSettle();

    expect(claves.habilitados, ['QUIZ-1']);
    expect(find.textContaining('Habilitada por profe@utb.edu.co'), findsOneWidget);
    expect(cambios, 1);
  });

  testWidgets('Con hojas calificadas la cuadrícula queda fija', (tester) async {
    final claves = _Claves({
      'QUIZ-1': ClaveDelExamen(
        examenId: 'QUIZ-1',
        respuestas: const ['A', 'B'],
        sePuedeCambiar: false,
        habilitadaPor: 'profe@utb.edu.co',
        habilitadaEn: DateTime.utc(2026, 11, 22, 15),
      ),
    });
    await _montar(tester, claves);

    await _escribirExamen(tester, 'QUIZ-1');

    expect(find.textContaining('Ya hay hojas calificadas con ella: no se puede cambiar.'), findsOneWidget);
    expect(_filas(tester).every((fila) => fila.onSelectionChanged == null), isTrue);
    expect(_guardar(tester).onPressed, isNull);
  });

  testWidgets('Con una pregunta sin respuesta no se puede guardar', (tester) async {
    await _montar(tester, _Claves());
    await _escribirExamen(tester, 'NUEVO-1');
    await _pegar(tester, 'AB');
    await tester.tap(find.text('Llenar la cuadrícula'));
    await tester.pumpAndSettle();

    await tester.enterText(find.widgetWithText(TextField, '2'), '3');
    await tester.pumpAndSettle();

    expect(_filas(tester), hasLength(3));
    expect(_guardar(tester).onPressed, isNull);
    expect(find.text('Falta la respuesta de la pregunta 3.'), findsOneWidget);
  });

  testWidgets('Un identificador que la API no acepta se avisa sin consultarla', (tester) async {
    final claves = _Claves();
    await _montar(tester, claves);

    await _escribirExamen(tester, 'con espacio');

    expect(claves.consultados, isEmpty);
    expect(find.text('Solo letras sin acento, dígitos, guiones y guiones bajos.'), findsOneWidget);
  });

  testWidgets('En un teléfono cabe sin desbordarse', (tester) async {
    await _montar(tester, _Claves(), tamano: const Size(360, 2400));
    await _escribirExamen(tester, 'NUEVO-1');
    await _pegar(tester, 'ABCD');
    await tester.tap(find.text('Llenar la cuadrícula'));
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
  });
}
