import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/common/tema/tema.dart';
import 'package:frontend/features/carga/data/servicio_examenes.dart';
import 'package:frontend/features/carga/data/servicio_resultados.dart';
import 'package:frontend/features/revision/data/servicio_revision.dart';
import 'package:frontend/features/revision/views/pantalla_revision.dart';

const _examenes = [
  ExamenConClave(examenId: 'PROTOTIPO-R05', habilitada: true),
  ExamenConClave(examenId: 'QUIZ-3', habilitada: true),
];

PreguntaEnRevision _pregunta(int numero, {String? resuelta, bool estaResuelta = false}) =>
    PreguntaEnRevision(
      numero: numero,
      burbujas: const [
        BurbujaLeida(opcion: 'A', tipo: 'vacia', confianza: 0),
        BurbujaLeida(opcion: 'B', tipo: 'vacia', confianza: 0),
        BurbujaLeida(opcion: 'C', tipo: 'tenue', confianza: 58),
        BurbujaLeida(opcion: 'D', tipo: 'vacia', confianza: 0),
      ],
      conRecorte: true,
      resuelta: estaResuelta,
      opcionResuelta: resuelta,
      resueltaPor: estaResuelta ? 'Docente de prueba' : null,
    );

/// Dos hojas: la primera ya revisada y la segunda con dos preguntas por revisar.
RevisionDelExamen _revision({bool resuelta = false}) => RevisionDelExamen(
      examenId: 'PROTOTIPO-R05',
      hojas: [
        HojaEnRevision(
          hojaId: 'h-1',
          notaEnDecimas: 50,
          provisional: false,
          codigoCompleto: true,
          preguntas: [_pregunta(3, resuelta: 'B', estaResuelta: true)],
        ),
        HojaEnRevision(
          hojaId: 'h-2',
          notaEnDecimas: resuelta ? 39 : 23,
          provisional: !resuelta,
          codigoCompleto: true,
          preguntas: [
            _pregunta(7, resuelta: resuelta ? 'C' : null, estaResuelta: resuelta),
            _pregunta(9, resuelta: null, estaResuelta: resuelta),
          ],
        ),
      ],
    );

typedef _Guardado = (String, String, String, Map<int, String?>);

Widget _pantalla({
  Future<RevisionDelExamen> Function(String)? consultar,
  List<_Guardado>? guardados,
  ValueNotifier<String?>? pedido,
  Map<String, String> nombres = const {'h-2': 'foto inclinada.jpg'},
  VoidCallback? alGuardar,
}) {
  var resuelta = false;
  return MaterialApp(
    theme: construirTema(),
    home: Scaffold(
      body: PantallaRevision(
        listarExamenes: () async => _examenes,
        consultarRevision: consultar ?? (examen) async => _revision(resuelta: resuelta),
        guardarRevision: (examen, hoja, por, opciones) async {
          guardados?.add((examen, hoja, por, opciones));
          resuelta = true;
          return const ResultadoDeHoja(
            hojaId: 'h-2',
            estado: EstadoDeLectura.calificada,
            notaEnDecimas: 39,
            revisada: true,
          );
        },
        nombresDeHojas: ValueNotifier(nombres),
        examenPedido: pedido,
        alGuardar: alGuardar,
      ),
    ),
  );
}

Future<void> _tocar(WidgetTester tester, Finder buscador) async {
  await tester.pumpAndSettle();
  await tester.ensureVisible(buscador);
  await tester.pumpAndSettle();
  await tester.tap(buscador);
  await tester.pumpAndSettle();
}

Future<void> _elegirExamen(WidgetTester tester, String examen) async {
  await _tocar(tester, find.byType(DropdownMenu<String>));
  await _tocar(tester, find.text(examen).last);
  // La revisión se pide un momento después de elegir.
  await tester.pump(const Duration(milliseconds: 400));
  await tester.pumpAndSettle();
}

ButtonStyleButton _guardar(WidgetTester tester) => tester.widget<ButtonStyleButton>(
      find.ancestor(
        of: find.text('Guardar'),
        matching: find.byWidgetPredicate((w) => w is ButtonStyleButton),
      ),
    );

void _fijarTamano(WidgetTester tester, Size tamano) {
  tester.view.physicalSize = tamano;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
}

void main() {
  testWidgets('Sin examen elegido invita a elegir uno', (tester) async {
    await tester.pumpWidget(_pantalla());
    await tester.pumpAndSettle();

    expect(find.text('Elija un examen'), findsOneWidget);
    expect(find.textContaining('Vista con datos de ejemplo'), findsNothing);
  });

  testWidgets('Al elegir el examen muestra primero la hoja con preguntas por revisar',
      (tester) async {
    _fijarTamano(tester, const Size(1280, 1800));
    await tester.pumpWidget(_pantalla());
    await tester.pumpAndSettle();

    await _elegirExamen(tester, 'PROTOTIPO-R05');

    expect(find.text('1 por revisar'), findsOneWidget);
    // El nombre del archivo, si se subió en esta sesión; si no, su lugar en el examen.
    expect(find.text('foto inclinada.jpg'), findsWidgets);
    expect(find.text('Hoja 1'), findsOneWidget);
    expect(find.text('Nota provisional 2,3'), findsOneWidget);
    expect(find.text('Pregunta 7'), findsOneWidget);
    expect(find.text('Pregunta 9'), findsOneWidget);
    expect(find.text('Se ve: C tenue (58 %).'), findsNWidgets(2));
  });

  testWidgets('Guarda lo elegido con el nombre del docente y recalcula', (tester) async {
    _fijarTamano(tester, const Size(1280, 1800));
    final guardados = <_Guardado>[];
    var avisos = 0;
    await tester.pumpWidget(_pantalla(guardados: guardados, alGuardar: () => avisos++));
    await tester.pumpAndSettle();
    await _elegirExamen(tester, 'PROTOTIPO-R05');

    expect(_guardar(tester).enabled, isFalse);
    expect(find.text('Elija lo que marcó el estudiante.'), findsOneWidget);

    await _tocar(tester, find.text('C').first);
    await _tocar(tester, find.text('Ninguna').at(1));
    expect(find.text('Escriba su nombre para guardar.'), findsOneWidget);
    expect(_guardar(tester).enabled, isFalse);

    await tester.enterText(find.widgetWithText(TextField, 'Su nombre'), 'Docente de prueba');
    await tester.pumpAndSettle();
    expect(find.text('Se guardarán 2 preguntas.'), findsOneWidget);

    await _tocar(tester, find.text('Guardar'));

    // Dart compara un mapa dentro de un record por identidad: se compara campo por campo.
    final (examen, hoja, por, opciones) = guardados.single;
    expect((examen, hoja, por), ('PROTOTIPO-R05', 'h-2', 'Docente de prueba'));
    expect(opciones, {7: 'C', 9: null});
    expect(avisos, 1);
    expect(find.text('Guardado. Nota 3,9.'), findsOneWidget);
    expect(find.text('Todas revisadas'), findsOneWidget);
    expect(find.text('Resuelta por Docente de prueba.'), findsWidgets);
  });

  testWidgets('Una pregunta ya resuelta muestra lo guardado y se puede cambiar', (tester) async {
    _fijarTamano(tester, const Size(1280, 1800));
    final guardados = <_Guardado>[];
    await tester.pumpWidget(_pantalla(guardados: guardados));
    await tester.pumpAndSettle();
    await _elegirExamen(tester, 'PROTOTIPO-R05');

    await _tocar(tester, find.text('Hoja 1'));
    expect(find.text('Pregunta 3'), findsOneWidget);
    final selector = tester.widget<SegmentedButton<String>>(find.byType(SegmentedButton<String>));
    expect(selector.selected, {'B'});
    expect(_guardar(tester).enabled, isFalse, reason: 'nada cambió');

    await tester.enterText(find.widgetWithText(TextField, 'Su nombre'), 'Docente de prueba');
    await _tocar(tester, find.text('A').first);
    await _tocar(tester, find.text('Guardar'));

    expect(guardados.single.$4, {3: 'A'});
  });

  testWidgets('Un examen sin dudas lo dice', (tester) async {
    await tester.pumpWidget(_pantalla(
      consultar: (examen) async => const RevisionDelExamen(examenId: 'QUIZ-3', hojas: []),
    ));
    await tester.pumpAndSettle();
    await _elegirExamen(tester, 'QUIZ-3');

    expect(find.text('No hay preguntas por revisar'), findsOneWidget);
  });

  testWidgets('Si la revisión no llega, lo dice y deja volver a intentar', (tester) async {
    var pedidos = 0;
    await tester.pumpWidget(_pantalla(consultar: (examen) async {
      pedidos++;
      throw const ExcepcionDeRevision('No se pudo contactar con el servidor.');
    }));
    await tester.pumpAndSettle();
    await _elegirExamen(tester, 'PROTOTIPO-R05');

    expect(find.text('No se pudo pedir la revisión'), findsOneWidget);
    await _tocar(tester, find.text('Volver a intentar'));
    expect(pedidos, 2);
  });

  testWidgets('El examen que pide la carga queda elegido', (tester) async {
    final pedido = ValueNotifier<String?>(null);
    addTearDown(pedido.dispose);
    await tester.pumpWidget(_pantalla(pedido: pedido));
    await tester.pumpAndSettle();

    pedido.value = 'PROTOTIPO-R05';
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pumpAndSettle();

    expect(find.text('Pregunta 7'), findsOneWidget);
  });

  testWidgets('En el teléfono no se desborda', (tester) async {
    _fijarTamano(tester, const Size(390, 900));
    await tester.pumpWidget(_pantalla());
    await tester.pumpAndSettle();
    await _elegirExamen(tester, 'PROTOTIPO-R05');

    expect(find.text('Pregunta 7'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
