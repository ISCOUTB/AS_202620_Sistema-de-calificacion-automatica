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

PreguntaEnRevision _pregunta(
  int numero, {
  String? resuelta,
  bool estaResuelta = false,
  String? sugerida,
  DateTime? resueltaEn,
}) =>
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
      opcionSugerida: sugerida,
      resueltaEn: resueltaEn,
    );

/// Una hoja por revisar con la 7 preseleccionada en la C y la 9 confusa. Después de guardar, la 7
/// vuelve resuelta con lo que se guardó, conservando su sugerencia.
RevisionDelExamen _revisionConSugerida({String? guardada}) => RevisionDelExamen(
      examenId: 'PROTOTIPO-R05',
      hojas: [
        HojaEnRevision(
          hojaId: 'h-2',
          notaEnDecimas: 23,
          provisional: true,
          codigoCompleto: true,
          preguntas: [
            _pregunta(7, sugerida: 'C', resuelta: guardada, estaResuelta: guardada != null),
            _pregunta(9),
          ],
        ),
      ],
    );

SegmentedButton<String> _selectorDe(WidgetTester tester, int numero) =>
    tester.widget<SegmentedButton<String>>(find.descendant(
      of: find.ancestor(
        of: find.text('Pregunta $numero'),
        matching: find.byWidgetPredicate((w) => w.runtimeType.toString() == '_TarjetaPregunta'),
      ),
      matching: find.byType(SegmentedButton<String>),
    ));

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

<<<<<<< HEAD
typedef _Guardado = (String, String, Map<int, String?>);
=======
typedef _Guardado = (String, String, String, Map<int, String?>);
>>>>>>> 88090461e81adc5d38504d646046fa218be33615

Widget _pantalla({
  Future<RevisionDelExamen> Function(String)? consultar,
  List<_Guardado>? guardados,
  ValueNotifier<String?>? pedido,
  Map<String, String> nombres = const {'h-2': 'foto inclinada.jpg'},
  VoidCallback? alGuardar,
  bool guardarFalla = false,
  Listenable? alMostrarse,
<<<<<<< HEAD
  String Function(String examenId, String hojaId, int numero)? urlDelRecorte,
  Map<String, String> Function()? encabezadosDelRecorte,
=======
>>>>>>> 88090461e81adc5d38504d646046fa218be33615
}) {
  var resuelta = false;
  return MaterialApp(
    theme: construirTema(),
    home: Scaffold(
      body: PantallaRevision(
        listarExamenes: () async => _examenes,
        consultarRevision: consultar ?? (examen) async => _revision(resuelta: resuelta),
<<<<<<< HEAD
        guardarRevision: (examen, hoja, opciones) async {
          if (guardarFalla) throw const ExcepcionDeRevision('No se pudo contactar con el servidor.');
          guardados?.add((examen, hoja, opciones));
=======
        guardarRevision: (examen, hoja, por, opciones) async {
          if (guardarFalla) throw const ExcepcionDeRevision('No se pudo contactar con el servidor.');
          guardados?.add((examen, hoja, por, opciones));
>>>>>>> 88090461e81adc5d38504d646046fa218be33615
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
        alMostrarse: alMostrarse,
<<<<<<< HEAD
        urlDelRecorte: urlDelRecorte,
        encabezadosDelRecorte: encabezadosDelRecorte,
=======
>>>>>>> 88090461e81adc5d38504d646046fa218be33615
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

  testWidgets('Cada hoja dice con qué nombre y cuándo se subió, aunque el nombre se repita',
      (tester) async {
    _fijarTamano(tester, const Size(1280, 1800));
    HojaEnRevision hoja(String id, int dia, {List<PreguntaEnRevision>? preguntas}) =>
        HojaEnRevision(
          hojaId: id,
          notaEnDecimas: 39,
          provisional: true,
          codigoCompleto: true,
          preguntas: preguntas ?? [_pregunta(7)],
          nombreArchivo: 'hoja1.jpg',
          recibidaEn: DateTime(2026, 11, dia, 14, 32),
        );
    await tester.pumpWidget(_pantalla(
      // El nombre de la API gana al de la sesión de carga, que ya no sirve después de recargar.
      nombres: const {'h-1': 'nombre de la sesión.jpg'},
      consultar: (examen) async => RevisionDelExamen(
        examenId: examen,
        hojas: [hoja('h-1', 15), hoja('h-2', 16, preguntas: [_pregunta(9)])],
      ),
    ));
    await tester.pumpAndSettle();
    await _elegirExamen(tester, 'PROTOTIPO-R05');

    expect(find.text('nombre de la sesión.jpg'), findsNothing);
    expect(find.text('hoja1.jpg'), findsWidgets);
    expect(find.text('1 pregunta por revisar\nSubida el 15 nov, 14:32'), findsOneWidget);
    expect(find.text('1 pregunta por revisar\nSubida el 16 nov, 14:32'), findsOneWidget);
    // El detalle de la hoja elegida también lo dice: la más nueva, que es la de arriba.
    expect(find.text('Subida el 16 nov, 14:32'), findsOneWidget);
  });

<<<<<<< HEAD
  testWidgets('Guarda lo elegido y recalcula', (tester) async {
=======
  testWidgets('Guarda lo elegido con el nombre del docente y recalcula', (tester) async {
>>>>>>> 88090461e81adc5d38504d646046fa218be33615
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
<<<<<<< HEAD
    expect(find.text('Se guardarán 2 preguntas.'), findsOneWidget);
    expect(_guardar(tester).enabled, isTrue);
=======
    expect(find.text('Escriba su nombre para guardar.'), findsOneWidget);
    expect(_guardar(tester).enabled, isFalse);

    await tester.enterText(find.widgetWithText(TextField, 'Su nombre'), 'Docente de prueba');
    await tester.pumpAndSettle();
    expect(find.text('Se guardarán 2 preguntas.'), findsOneWidget);
>>>>>>> 88090461e81adc5d38504d646046fa218be33615

    await _tocar(tester, find.text('Guardar'));

    // Dart compara un mapa dentro de un record por identidad: se compara campo por campo.
<<<<<<< HEAD
    final (examen, hoja, opciones) = guardados.single;
    expect((examen, hoja), ('PROTOTIPO-R05', 'h-2'));
=======
    final (examen, hoja, por, opciones) = guardados.single;
    expect((examen, hoja, por), ('PROTOTIPO-R05', 'h-2', 'Docente de prueba'));
>>>>>>> 88090461e81adc5d38504d646046fa218be33615
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

<<<<<<< HEAD
    await _tocar(tester, find.text('A').first);
    await _tocar(tester, find.text('Guardar'));

    expect(guardados.single.$3, {3: 'A'});
  });

  group('Preselección (ADR-0024)', () {
    testWidgets('Una pregunta con sugerencia llega marcada y se guarda con un toque',
        (tester) async {
      _fijarTamano(tester, const Size(1280, 1800));
      final guardados = <_Guardado>[];
      await tester.pumpWidget(_pantalla(
        guardados: guardados,
        consultar: (examen) async => _revisionConSugerida(guardada: guardados.isEmpty ? null : 'C'),
      ));
      await tester.pumpAndSettle();
      await _elegirExamen(tester, 'PROTOTIPO-R05');

      expect(_selectorDe(tester, 7).selected, {'C'});
      expect(_selectorDe(tester, 9).selected, isEmpty);
      expect(find.text('Se guardará 1 pregunta.'), findsOneWidget);
      expect(_guardar(tester).enabled, isTrue);
      await _tocar(tester, find.text('Guardar'));

      final (examen, hoja, opciones) = guardados.single;
      expect((examen, hoja), ('PROTOTIPO-R05', 'h-2'));
      expect(opciones, {7: 'C'});
    });

    testWidgets('La nota provisional no cambia por las preseleccionadas', (tester) async {
      _fijarTamano(tester, const Size(1280, 1800));
      await tester.pumpWidget(_pantalla(consultar: (examen) async => _revisionConSugerida()));
      await tester.pumpAndSettle();
      await _elegirExamen(tester, 'PROTOTIPO-R05');

      expect(_selectorDe(tester, 7).selected, {'C'});
      expect(find.text('Nota provisional 2,3'), findsOneWidget);
    });

    testWidgets('Cambiar una preselección a Ninguna la envía como nula', (tester) async {
      _fijarTamano(tester, const Size(1280, 1800));
      final guardados = <_Guardado>[];
      await tester.pumpWidget(_pantalla(
        guardados: guardados,
        consultar: (examen) async => _revisionConSugerida(),
      ));
      await tester.pumpAndSettle();
      await _elegirExamen(tester, 'PROTOTIPO-R05');

      // Las confusas van primero: la 9 es la primera tarjeta y la 7 la segunda.
      await _tocar(tester, find.text('Ninguna').at(1));
      await _tocar(tester, find.text('Guardar'));

      expect(guardados.single.$3, {7: null});
    });

    testWidgets('Si guardar falla, las preselecciones siguen marcadas', (tester) async {
      _fijarTamano(tester, const Size(1280, 1800));
      await tester.pumpWidget(_pantalla(
        guardarFalla: true,
        consultar: (examen) async => _revisionConSugerida(),
      ));
      await tester.pumpAndSettle();
      await _elegirExamen(tester, 'PROTOTIPO-R05');

      await _tocar(tester, find.text('Guardar'));

      expect(find.text('No se pudo contactar con el servidor.'), findsOneWidget);
      expect(_selectorDe(tester, 7).selected, {'C'});
      expect(_guardar(tester).enabled, isTrue);
    });

    testWidgets('Después de guardar se ve lo guardado y no la sugerencia', (tester) async {
      _fijarTamano(tester, const Size(1280, 1800));
      final guardados = <_Guardado>[];
      await tester.pumpWidget(_pantalla(
        guardados: guardados,
        consultar: (examen) async => _revisionConSugerida(
          guardada: guardados.isEmpty ? null : guardados.single.$3[7],
        ),
      ));
      await tester.pumpAndSettle();
      await _elegirExamen(tester, 'PROTOTIPO-R05');

      await _tocar(tester, find.text('A').at(1));
      await _tocar(tester, find.text('Guardar'));

      expect(guardados.single.$3, {7: 'A'});
      expect(_selectorDe(tester, 7).selected, {'A'});
      expect(_guardar(tester).enabled, isFalse, reason: 'nada cambió desde lo guardado');
    });

    testWidgets('Las confusas van antes que las preseleccionadas', (tester) async {
      _fijarTamano(tester, const Size(1280, 1800));
      await tester.pumpWidget(_pantalla(consultar: (examen) async => _revisionConSugerida()));
      await tester.pumpAndSettle();
      await _elegirExamen(tester, 'PROTOTIPO-R05');

      expect(
        tester.getTopLeft(find.text('Pregunta 9')).dy,
        lessThan(tester.getTopLeft(find.text('Pregunta 7')).dy),
      );
    });
  });

  group('Lista de hojas', () {
    /// Dos hojas con el mismo nombre: la de ayer ya revisada (editada esta mañana) y la de hoy por
    /// revisar.
    RevisionDelExamen fechadas(String examen) => RevisionDelExamen(
          examenId: examen,
          hojas: [
            HojaEnRevision(
              hojaId: 'h-1',
              notaEnDecimas: 40,
              provisional: false,
              codigoCompleto: true,
              preguntas: [
                _pregunta(3,
                    resuelta: 'B', estaResuelta: true, resueltaEn: DateTime(2026, 11, 19, 10, 5)),
              ],
              nombreArchivo: 'hoja1.jpg',
              recibidaEn: DateTime(2026, 11, 18, 14, 32),
            ),
            HojaEnRevision(
              hojaId: 'h-2',
              notaEnDecimas: 23,
              provisional: true,
              codigoCompleto: true,
              preguntas: [_pregunta(7)],
              nombreArchivo: 'hoja1.jpg',
              recibidaEn: DateTime(2026, 11, 19, 9, 0),
            ),
          ],
        );
    const revisada = 'Revisada\nSubida el 18 nov, 14:32\nEditada el 19 nov, 10:05';
    const porRevisar = '1 pregunta por revisar\nSubida el 19 nov, 09:00';

    testWidgets('El código del estudiante va junto al nombre, en la lista y en el detalle',
        (tester) async {
      _fijarTamano(tester, const Size(1280, 1800));
      final revision = fechadas('PROTOTIPO-R05');
      await tester.pumpWidget(_pantalla(
        consultar: (examen) async => RevisionDelExamen(examenId: examen, hojas: [
          for (final (indice, hoja) in revision.hojas.indexed)
            HojaEnRevision(
              hojaId: hoja.hojaId,
              notaEnDecimas: hoja.notaEnDecimas,
              provisional: hoja.provisional,
              // La revisada, con un dígito sin leer.
              codigoCompleto: indice == 1,
              codigo: indice == 1 ? 'T20261105' : 'T2026?105',
              preguntas: hoja.preguntas,
              nombreArchivo: hoja.nombreArchivo,
              recibidaEn: hoja.recibidaEn,
            ),
        ]),
      ));
      await tester.pumpAndSettle();
      await _elegirExamen(tester, 'PROTOTIPO-R05');

      // La abierta es la por revisar: su código está en la lista y en el detalle.
      expect(find.text('T20261105'), findsNWidgets(2));
      expect(find.text('T2026?105'), findsOneWidget);
      final nombreDelDetalle = find.text('hoja1.jpg').last;
      final codigoDelDetalle = find.text('T20261105').last;
      expect(
        tester.getTopLeft(codigoDelDetalle).dx,
        greaterThan(tester.getTopRight(nombreDelDetalle).dx),
      );
      expect(
        tester.getTopLeft(codigoDelDetalle).dy,
        lessThan(tester.getBottomLeft(nombreDelDetalle).dy),
      );
    });

    testWidgets('La lista pone arriba la hoja más nueva y dice cuándo se editó', (tester) async {
      _fijarTamano(tester, const Size(1280, 1800));
      await tester.pumpWidget(_pantalla(consultar: (examen) async => fechadas(examen)));
      await tester.pumpAndSettle();
      await _elegirExamen(tester, 'PROTOTIPO-R05');

      expect(find.text(revisada), findsOneWidget);
      expect(
        tester.getTopLeft(find.text(porRevisar)).dy,
        lessThan(tester.getTopLeft(find.text(revisada)).dy),
      );
    });

    testWidgets('Desmarcar Por revisar oculta la hoja abierta y abre la primera visible',
        (tester) async {
      _fijarTamano(tester, const Size(1280, 1800));
      await tester.pumpWidget(_pantalla());
      await tester.pumpAndSettle();
      await _elegirExamen(tester, 'PROTOTIPO-R05');
      expect(find.text('Pregunta 7'), findsOneWidget);

      await _tocar(tester, find.widgetWithText(FilterChip, 'Por revisar'));

      expect(find.text('Pregunta 7'), findsNothing);
      expect(find.text('Pregunta 3'), findsOneWidget, reason: 'se abre la hoja revisada');
      expect(find.text('1 por revisar'), findsOneWidget, reason: 'cuenta todas, no las filtradas');

      await _tocar(tester, find.widgetWithText(FilterChip, 'Por revisar'));
      expect(find.text('foto inclinada.jpg'), findsOneWidget, reason: 'vuelve a la lista');
    });

    testWidgets('Con los dos filtros desmarcados lo dice', (tester) async {
      _fijarTamano(tester, const Size(1280, 1800));
      await tester.pumpWidget(_pantalla());
      await tester.pumpAndSettle();
      await _elegirExamen(tester, 'PROTOTIPO-R05');

      await _tocar(tester, find.widgetWithText(FilterChip, 'Por revisar'));
      await _tocar(tester, find.widgetWithText(FilterChip, 'Revisadas'));

      expect(
        find.text('No hay hojas para mostrar. Marque «Por revisar» o «Revisadas».'),
        findsOneWidget,
      );
      expect(find.textContaining('Pregunta'), findsNothing);
      expect(find.text('1 por revisar'), findsOneWidget);
    });

    testWidgets('Con un solo filtro y nada que mostrar, dice qué falta', (tester) async {
      _fijarTamano(tester, const Size(1280, 1800));
      var revisadas = true;
      await tester.pumpWidget(_pantalla(
        consultar: (examen) async =>
            revisadas ? _revision(resuelta: true) : _revisionConSugerida(),
      ));
      await tester.pumpAndSettle();
      await _elegirExamen(tester, 'PROTOTIPO-R05');

      // Todo revisado y solo «Por revisar» marcado: el final de una sesión.
      await _tocar(tester, find.widgetWithText(FilterChip, 'Revisadas'));
      expect(find.text('No quedan hojas por revisar.'), findsOneWidget);

      // Nada revisado y solo «Revisadas» marcado.
      revisadas = false;
      await _elegirExamen(tester, 'QUIZ-3');
      await _tocar(tester, find.widgetWithText(FilterChip, 'Revisadas'));
      await _tocar(tester, find.widgetWithText(FilterChip, 'Por revisar'));
      expect(find.text('Todavía no hay hojas revisadas.'), findsOneWidget);
    });

    testWidgets('En el teléfono caben los filtros y las tres líneas de cada hoja', (tester) async {
      _fijarTamano(tester, const Size(390, 900));
      await tester.pumpWidget(_pantalla(consultar: (examen) async => fechadas(examen)));
      await tester.pumpAndSettle();
      await _elegirExamen(tester, 'PROTOTIPO-R05');

      expect(find.widgetWithText(FilterChip, 'Revisadas'), findsOneWidget);
      expect(find.text(revisada), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
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

  group('Volver a la revisión', () {
    /// Cada consulta trae una hoja más, como si entre una y otra se hubiera subido otra hoja.
    Future<RevisionDelExamen> Function(String) creciente(List<String> pedidos) =>
        (examen) async {
          pedidos.add(examen);
          return RevisionDelExamen(examenId: examen, hojas: [
            for (var i = 1; i <= pedidos.length; i++)
              HojaEnRevision(
                hojaId: 'h-$i',
                notaEnDecimas: 23,
                provisional: true,
                codigoCompleto: true,
                preguntas: [_pregunta(7)],
                nombreArchivo: 'hoja $i.jpg',
              ),
          ]);
        };

    testWidgets('Si la carga pide el examen que ya estaba elegido, trae las hojas nuevas',
        (tester) async {
      // Lo que se vio en local: elegir el examen en Revisión, subir hojas en Carga y tocar
      // «Revisar» mostraba la revisión de antes de subir.
      _fijarTamano(tester, const Size(1280, 1800));
      final pedidos = <String>[];
      final pedido = ValueNotifier<String?>(null);
      final mostrada = ValueNotifier<int>(0);
      addTearDown(pedido.dispose);
      addTearDown(mostrada.dispose);
      await tester.pumpWidget(
        _pantalla(consultar: creciente(pedidos), pedido: pedido, alMostrarse: mostrada),
      );
      await tester.pumpAndSettle();
      await _elegirExamen(tester, 'PROTOTIPO-R05');
      expect(find.text('hoja 2.jpg'), findsNothing);

      pedido.value = 'PROTOTIPO-R05';
      mostrada.value++;
      await tester.pumpAndSettle();

      expect(find.text('hoja 2.jpg'), findsOneWidget);
      expect(pedidos, ['PROTOTIPO-R05', 'PROTOTIPO-R05']);
    });

    testWidgets('Si la carga pide otro examen, lo pide una sola vez', (tester) async {
      _fijarTamano(tester, const Size(1280, 1800));
      final pedidos = <String>[];
      final pedido = ValueNotifier<String?>(null);
      final mostrada = ValueNotifier<int>(0);
      addTearDown(pedido.dispose);
      addTearDown(mostrada.dispose);
      await tester.pumpWidget(
        _pantalla(consultar: creciente(pedidos), pedido: pedido, alMostrarse: mostrada),
      );
      await tester.pumpAndSettle();
      await _elegirExamen(tester, 'PROTOTIPO-R05');

      pedido.value = 'QUIZ-3';
      mostrada.value++;
      await tester.pump(const Duration(milliseconds: 400));
      await tester.pumpAndSettle();

      expect(pedidos, ['PROTOTIPO-R05', 'QUIZ-3']);
    });

    testWidgets('Volver sin examen elegido no pide nada', (tester) async {
      final pedidos = <String>[];
      final mostrada = ValueNotifier<int>(0);
      addTearDown(mostrada.dispose);
      await tester.pumpWidget(_pantalla(consultar: creciente(pedidos), alMostrarse: mostrada));
      await tester.pumpAndSettle();

      mostrada.value++;
      await tester.pumpAndSettle();

      expect(pedidos, isEmpty);
    });
  });

  testWidgets('En el teléfono no se desborda', (tester) async {
    _fijarTamano(tester, const Size(390, 900));
    await tester.pumpWidget(_pantalla());
    await tester.pumpAndSettle();
    await _elegirExamen(tester, 'PROTOTIPO-R05');

    expect(find.text('Pregunta 7'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('No pide el nombre: guarda el docente de la sesión (ADR-0025)', (tester) async {
    _fijarTamano(tester, const Size(1280, 1800));
    await tester.pumpWidget(_pantalla());
    await tester.pumpAndSettle();
    await _elegirExamen(tester, 'PROTOTIPO-R05');

    expect(find.widgetWithText(TextField, 'Su nombre'), findsNothing);
    expect(find.textContaining('Escriba su nombre'), findsNothing);
  });

  testWidgets('El recorte se pide con el token de la sesión', (tester) async {
    _fijarTamano(tester, const Size(1280, 1800));
    await tester.pumpWidget(_pantalla(
      urlDelRecorte: (examen, hoja, numero) => 'http://api/$examen/$hoja/$numero',
      encabezadosDelRecorte: () => {'Authorization': 'Bearer v1.abc.def'},
    ));
    await tester.pumpAndSettle();
    await _elegirExamen(tester, 'PROTOTIPO-R05');

    final imagenes = tester.widgetList<Image>(find.byType(Image)).map((i) => i.image);
    expect(imagenes, isNotEmpty);
    for (final imagen in imagenes) {
      expect((imagen as NetworkImage).headers, {'Authorization': 'Bearer v1.abc.def'});
    }
=======
    await tester.enterText(find.widgetWithText(TextField, 'Su nombre'), 'Docente de prueba');
    await _tocar(tester, find.text('A').first);
    await _tocar(tester, find.text('Guardar'));

    expect(guardados.single.$4, {3: 'A'});
  });

  group('Preselección (ADR-0024)', () {
    testWidgets('Una pregunta con sugerencia llega marcada y se guarda con solo escribir el nombre',
        (tester) async {
      _fijarTamano(tester, const Size(1280, 1800));
      final guardados = <_Guardado>[];
      await tester.pumpWidget(_pantalla(
        guardados: guardados,
        consultar: (examen) async => _revisionConSugerida(guardada: guardados.isEmpty ? null : 'C'),
      ));
      await tester.pumpAndSettle();
      await _elegirExamen(tester, 'PROTOTIPO-R05');

      expect(_selectorDe(tester, 7).selected, {'C'});
      expect(_selectorDe(tester, 9).selected, isEmpty);
      expect(find.text('Escriba su nombre para guardar.'), findsOneWidget);

      await tester.enterText(find.widgetWithText(TextField, 'Su nombre'), 'Docente de prueba');
      await tester.pumpAndSettle();
      expect(find.text('Se guardará 1 pregunta.'), findsOneWidget);
      expect(_guardar(tester).enabled, isTrue);
      await _tocar(tester, find.text('Guardar'));

      final (examen, hoja, por, opciones) = guardados.single;
      expect((examen, hoja, por), ('PROTOTIPO-R05', 'h-2', 'Docente de prueba'));
      expect(opciones, {7: 'C'});
    });

    testWidgets('La nota provisional no cambia por las preseleccionadas', (tester) async {
      _fijarTamano(tester, const Size(1280, 1800));
      await tester.pumpWidget(_pantalla(consultar: (examen) async => _revisionConSugerida()));
      await tester.pumpAndSettle();
      await _elegirExamen(tester, 'PROTOTIPO-R05');

      expect(_selectorDe(tester, 7).selected, {'C'});
      expect(find.text('Nota provisional 2,3'), findsOneWidget);
    });

    testWidgets('Cambiar una preselección a Ninguna la envía como nula', (tester) async {
      _fijarTamano(tester, const Size(1280, 1800));
      final guardados = <_Guardado>[];
      await tester.pumpWidget(_pantalla(
        guardados: guardados,
        consultar: (examen) async => _revisionConSugerida(),
      ));
      await tester.pumpAndSettle();
      await _elegirExamen(tester, 'PROTOTIPO-R05');

      await tester.enterText(find.widgetWithText(TextField, 'Su nombre'), 'Docente de prueba');
      // Las confusas van primero: la 9 es la primera tarjeta y la 7 la segunda.
      await _tocar(tester, find.text('Ninguna').at(1));
      await _tocar(tester, find.text('Guardar'));

      expect(guardados.single.$4, {7: null});
    });

    testWidgets('Si guardar falla, las preselecciones siguen marcadas', (tester) async {
      _fijarTamano(tester, const Size(1280, 1800));
      await tester.pumpWidget(_pantalla(
        guardarFalla: true,
        consultar: (examen) async => _revisionConSugerida(),
      ));
      await tester.pumpAndSettle();
      await _elegirExamen(tester, 'PROTOTIPO-R05');

      await tester.enterText(find.widgetWithText(TextField, 'Su nombre'), 'Docente de prueba');
      await _tocar(tester, find.text('Guardar'));

      expect(find.text('No se pudo contactar con el servidor.'), findsOneWidget);
      expect(_selectorDe(tester, 7).selected, {'C'});
      expect(_guardar(tester).enabled, isTrue);
    });

    testWidgets('Después de guardar se ve lo guardado y no la sugerencia', (tester) async {
      _fijarTamano(tester, const Size(1280, 1800));
      final guardados = <_Guardado>[];
      await tester.pumpWidget(_pantalla(
        guardados: guardados,
        consultar: (examen) async => _revisionConSugerida(
          guardada: guardados.isEmpty ? null : guardados.single.$4[7],
        ),
      ));
      await tester.pumpAndSettle();
      await _elegirExamen(tester, 'PROTOTIPO-R05');

      await tester.enterText(find.widgetWithText(TextField, 'Su nombre'), 'Docente de prueba');
      await _tocar(tester, find.text('A').at(1));
      await _tocar(tester, find.text('Guardar'));

      expect(guardados.single.$4, {7: 'A'});
      expect(_selectorDe(tester, 7).selected, {'A'});
      expect(_guardar(tester).enabled, isFalse, reason: 'nada cambió desde lo guardado');
    });

    testWidgets('Las confusas van antes que las preseleccionadas', (tester) async {
      _fijarTamano(tester, const Size(1280, 1800));
      await tester.pumpWidget(_pantalla(consultar: (examen) async => _revisionConSugerida()));
      await tester.pumpAndSettle();
      await _elegirExamen(tester, 'PROTOTIPO-R05');

      expect(
        tester.getTopLeft(find.text('Pregunta 9')).dy,
        lessThan(tester.getTopLeft(find.text('Pregunta 7')).dy),
      );
    });
  });

  group('Lista de hojas', () {
    /// Dos hojas con el mismo nombre: la de ayer ya revisada (editada esta mañana) y la de hoy por
    /// revisar.
    RevisionDelExamen fechadas(String examen) => RevisionDelExamen(
          examenId: examen,
          hojas: [
            HojaEnRevision(
              hojaId: 'h-1',
              notaEnDecimas: 40,
              provisional: false,
              codigoCompleto: true,
              preguntas: [
                _pregunta(3,
                    resuelta: 'B', estaResuelta: true, resueltaEn: DateTime(2026, 11, 19, 10, 5)),
              ],
              nombreArchivo: 'hoja1.jpg',
              recibidaEn: DateTime(2026, 11, 18, 14, 32),
            ),
            HojaEnRevision(
              hojaId: 'h-2',
              notaEnDecimas: 23,
              provisional: true,
              codigoCompleto: true,
              preguntas: [_pregunta(7)],
              nombreArchivo: 'hoja1.jpg',
              recibidaEn: DateTime(2026, 11, 19, 9, 0),
            ),
          ],
        );
    const revisada = 'Revisada\nSubida el 18 nov, 14:32\nEditada el 19 nov, 10:05';
    const porRevisar = '1 pregunta por revisar\nSubida el 19 nov, 09:00';

    testWidgets('La lista pone arriba la hoja más nueva y dice cuándo se editó', (tester) async {
      _fijarTamano(tester, const Size(1280, 1800));
      await tester.pumpWidget(_pantalla(consultar: (examen) async => fechadas(examen)));
      await tester.pumpAndSettle();
      await _elegirExamen(tester, 'PROTOTIPO-R05');

      expect(find.text(revisada), findsOneWidget);
      expect(
        tester.getTopLeft(find.text(porRevisar)).dy,
        lessThan(tester.getTopLeft(find.text(revisada)).dy),
      );
    });

    testWidgets('Desmarcar Por revisar oculta la hoja abierta y abre la primera visible',
        (tester) async {
      _fijarTamano(tester, const Size(1280, 1800));
      await tester.pumpWidget(_pantalla());
      await tester.pumpAndSettle();
      await _elegirExamen(tester, 'PROTOTIPO-R05');
      expect(find.text('Pregunta 7'), findsOneWidget);

      await _tocar(tester, find.widgetWithText(FilterChip, 'Por revisar'));

      expect(find.text('Pregunta 7'), findsNothing);
      expect(find.text('Pregunta 3'), findsOneWidget, reason: 'se abre la hoja revisada');
      expect(find.text('1 por revisar'), findsOneWidget, reason: 'cuenta todas, no las filtradas');

      await _tocar(tester, find.widgetWithText(FilterChip, 'Por revisar'));
      expect(find.text('foto inclinada.jpg'), findsOneWidget, reason: 'vuelve a la lista');
    });

    testWidgets('Con los dos filtros desmarcados lo dice', (tester) async {
      _fijarTamano(tester, const Size(1280, 1800));
      await tester.pumpWidget(_pantalla());
      await tester.pumpAndSettle();
      await _elegirExamen(tester, 'PROTOTIPO-R05');

      await _tocar(tester, find.widgetWithText(FilterChip, 'Por revisar'));
      await _tocar(tester, find.widgetWithText(FilterChip, 'Revisadas'));

      expect(
        find.text('No hay hojas para mostrar. Marque «Por revisar» o «Revisadas».'),
        findsOneWidget,
      );
      expect(find.textContaining('Pregunta'), findsNothing);
      expect(find.text('1 por revisar'), findsOneWidget);
    });

    testWidgets('Con un solo filtro y nada que mostrar, dice qué falta', (tester) async {
      _fijarTamano(tester, const Size(1280, 1800));
      var revisadas = true;
      await tester.pumpWidget(_pantalla(
        consultar: (examen) async =>
            revisadas ? _revision(resuelta: true) : _revisionConSugerida(),
      ));
      await tester.pumpAndSettle();
      await _elegirExamen(tester, 'PROTOTIPO-R05');

      // Todo revisado y solo «Por revisar» marcado: el final de una sesión.
      await _tocar(tester, find.widgetWithText(FilterChip, 'Revisadas'));
      expect(find.text('No quedan hojas por revisar.'), findsOneWidget);

      // Nada revisado y solo «Revisadas» marcado.
      revisadas = false;
      await _elegirExamen(tester, 'QUIZ-3');
      await _tocar(tester, find.widgetWithText(FilterChip, 'Revisadas'));
      await _tocar(tester, find.widgetWithText(FilterChip, 'Por revisar'));
      expect(find.text('Todavía no hay hojas revisadas.'), findsOneWidget);
    });

    testWidgets('En el teléfono caben los filtros y las tres líneas de cada hoja', (tester) async {
      _fijarTamano(tester, const Size(390, 900));
      await tester.pumpWidget(_pantalla(consultar: (examen) async => fechadas(examen)));
      await tester.pumpAndSettle();
      await _elegirExamen(tester, 'PROTOTIPO-R05');

      expect(find.widgetWithText(FilterChip, 'Revisadas'), findsOneWidget);
      expect(find.text(revisada), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
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

  group('Volver a la revisión', () {
    /// Cada consulta trae una hoja más, como si entre una y otra se hubiera subido otra hoja.
    Future<RevisionDelExamen> Function(String) creciente(List<String> pedidos) =>
        (examen) async {
          pedidos.add(examen);
          return RevisionDelExamen(examenId: examen, hojas: [
            for (var i = 1; i <= pedidos.length; i++)
              HojaEnRevision(
                hojaId: 'h-$i',
                notaEnDecimas: 23,
                provisional: true,
                codigoCompleto: true,
                preguntas: [_pregunta(7)],
                nombreArchivo: 'hoja $i.jpg',
              ),
          ]);
        };

    testWidgets('Si la carga pide el examen que ya estaba elegido, trae las hojas nuevas',
        (tester) async {
      // Lo que se vio en local: elegir el examen en Revisión, subir hojas en Carga y tocar
      // «Revisar» mostraba la revisión de antes de subir.
      _fijarTamano(tester, const Size(1280, 1800));
      final pedidos = <String>[];
      final pedido = ValueNotifier<String?>(null);
      final mostrada = ValueNotifier<int>(0);
      addTearDown(pedido.dispose);
      addTearDown(mostrada.dispose);
      await tester.pumpWidget(
        _pantalla(consultar: creciente(pedidos), pedido: pedido, alMostrarse: mostrada),
      );
      await tester.pumpAndSettle();
      await _elegirExamen(tester, 'PROTOTIPO-R05');
      expect(find.text('hoja 2.jpg'), findsNothing);

      pedido.value = 'PROTOTIPO-R05';
      mostrada.value++;
      await tester.pumpAndSettle();

      expect(find.text('hoja 2.jpg'), findsOneWidget);
      expect(pedidos, ['PROTOTIPO-R05', 'PROTOTIPO-R05']);
    });

    testWidgets('Si la carga pide otro examen, lo pide una sola vez', (tester) async {
      _fijarTamano(tester, const Size(1280, 1800));
      final pedidos = <String>[];
      final pedido = ValueNotifier<String?>(null);
      final mostrada = ValueNotifier<int>(0);
      addTearDown(pedido.dispose);
      addTearDown(mostrada.dispose);
      await tester.pumpWidget(
        _pantalla(consultar: creciente(pedidos), pedido: pedido, alMostrarse: mostrada),
      );
      await tester.pumpAndSettle();
      await _elegirExamen(tester, 'PROTOTIPO-R05');

      pedido.value = 'QUIZ-3';
      mostrada.value++;
      await tester.pump(const Duration(milliseconds: 400));
      await tester.pumpAndSettle();

      expect(pedidos, ['PROTOTIPO-R05', 'QUIZ-3']);
    });

    testWidgets('Volver sin examen elegido no pide nada', (tester) async {
      final pedidos = <String>[];
      final mostrada = ValueNotifier<int>(0);
      addTearDown(mostrada.dispose);
      await tester.pumpWidget(_pantalla(consultar: creciente(pedidos), alMostrarse: mostrada));
      await tester.pumpAndSettle();

      mostrada.value++;
      await tester.pumpAndSettle();

      expect(pedidos, isEmpty);
    });
  });

  testWidgets('En el teléfono no se desborda', (tester) async {
    _fijarTamano(tester, const Size(390, 900));
    await tester.pumpWidget(_pantalla());
    await tester.pumpAndSettle();
    await _elegirExamen(tester, 'PROTOTIPO-R05');

    expect(find.text('Pregunta 7'), findsOneWidget);
    expect(tester.takeException(), isNull);
>>>>>>> 88090461e81adc5d38504d646046fa218be33615
  });
}
