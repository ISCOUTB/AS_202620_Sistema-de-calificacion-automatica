import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/common/tema/tema.dart';
import 'package:frontend/common/widgets/q_aviso_datos_ejemplo.dart';
import 'package:frontend/features/revision/data/datos_ejemplo_revision.dart';
import 'package:frontend/features/revision/views/pantalla_revision.dart';
import 'package:frontend/features/revision/views/widgets/seccion_estudiantes.dart';
import 'package:frontend/features/revision/views/widgets/tarjeta_caso.dart';

/// Carga las fuentes empaquetadas. Sin esto la prueba mide el texto con la fuente de pruebas de
/// Flutter, que es más ancha que Plus Jakarta Sans, y los desbordes no serían los del navegador.
Future<void> _cargarFuentes() async {
  final jakarta = FontLoader(familiaTexto);
  for (final peso in ['Regular', 'Medium', 'SemiBold', 'Bold']) {
    jakarta.addFont(rootBundle.load('assets/fuentes/PlusJakartaSans-$peso.ttf'));
  }
  final mono = FontLoader(familiaMono)
    ..addFont(rootBundle.load('assets/fuentes/JetBrainsMono-Regular.ttf'));
  await Future.wait([jakarta.load(), mono.load()]);
}

/// Monta la pantalla como lo pide el marco, en un tamaño de ventana dado.
Future<void> _montar(
  WidgetTester tester, {
  Size tamano = const Size(390, 844),
  double escalaTexto = 1,
  bool sinAnimaciones = false,
}) async {
  tester.view.physicalSize = tamano;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    MaterialApp(
      theme: construirTema(),
      builder: (context, hijo) => MediaQuery(
        data: MediaQuery.of(context).copyWith(
          textScaler: TextScaler.linear(escalaTexto),
          disableAnimations: sinAnimaciones,
        ),
        child: hijo!,
      ),
      home: const Scaffold(body: PantallaRevision()),
    ),
  );
  await tester.pumpAndSettle();
}

/// Lleva el objetivo al centro de la vista antes de tocarlo, para que el aviso flotante del pie
/// no quede encima del botón.
Future<void> _tocar(WidgetTester tester, Finder objetivo) async {
  await Scrollable.ensureVisible(tester.element(objetivo), alignment: 0.5);
  await tester.pumpAndSettle();
  await tester.tap(objetivo);
  await tester.pumpAndSettle();
}

Finder _enAviso(String texto) =>
    find.descendant(of: find.byType(SnackBar), matching: find.textContaining(texto));

Finder get _tarjetasEstudiante => find.byType(TarjetaEstudiante);

Finder _enLista(String nombre) =>
    find.descendant(of: _tarjetasEstudiante, matching: find.text(nombre));

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  setUpAll(_cargarFuentes);

  testWidgets('Avisa que son datos de ejemplo y muestra el primer caso con sus cifras',
      (tester) async {
    await _montar(tester);

    expect(find.byType(QAvisoDatosEjemplo), findsOneWidget);
    expect(find.textContaining('Lo que decida aquí no se guarda'), findsOneWidget);
    // El conteo del encabezado sale de los datos, no de un texto fijo.
    expect(
      find.text('Parcial 2 · 43 estudiantes · 3 marcas dudosas por revisar'),
      findsOneWidget,
    );
    expect(find.text('1 de 3 pendientes'), findsOneWidget);
    expect(find.text('Código T00063218'), findsOneWidget);
    expect(find.text('4,6 si se acepta A'), findsOneWidget);
    expect(find.text('A · Correcta (+1,0)'), findsOneWidget);
    expect(find.text('C · Incorrecta (0,0)'), findsOneWidget);
    expect(find.text('Anular · sin efecto'), findsOneWidget);
  });

  testWidgets('Cada burbuja se anuncia con su lectura y su confianza', (tester) async {
    final semantica = tester.ensureSemantics();
    await _montar(tester);

    expect(find.bySemanticsLabel('Opción A: marca tenue, 58 % de confianza'), findsOneWidget);
    expect(find.bySemanticsLabel('Opción B: vacía'), findsOneWidget);
    expect(find.bySemanticsLabel('Opción C: borrón, 42 % de confianza'), findsOneWidget);
    semantica.dispose();
  });

  testWidgets('Un veredicto recalcula la nota, avisa que no se guarda y pasa al siguiente caso',
      (tester) async {
    await _montar(tester);

    await _tocar(tester, find.text('A · Correcta (+1,0)'));

    expect(_enAviso('la nota pasa de 4,2 a 4,6'), findsOneWidget);
    expect(_enAviso('la decisión no se guarda'), findsOneWidget);
    expect(find.text('1 de 2 pendientes'), findsOneWidget);
    expect(find.text('Código T00061547'), findsOneWidget);
    expect(find.text('B · Correcta (+1,0)'), findsOneWidget);
    expect(find.text('Doble marcación'), findsWidgets);
    expect(
      find.text('Parcial 2 · 43 estudiantes · 2 marcas dudosas por revisar'),
      findsOneWidget,
    );
    // El registro de la visita deja a la vista la nota nueva.
    expect(find.textContaining('nota de 4,2 a 4,6'), findsOneWidget);
  });

  testWidgets('Deshacer devuelve la marca a revisión', (tester) async {
    await _montar(tester);

    await _tocar(tester, find.text('A · Correcta (+1,0)'));
    await tester.tap(find.widgetWithText(SnackBarAction, 'Deshacer'));
    await tester.pumpAndSettle();

    expect(find.text('1 de 3 pendientes'), findsOneWidget);
    expect(find.text('Código T00063218'), findsOneWidget);
    expect(_enAviso('vuelve a revisión'), findsOneWidget);
    expect(find.byType(RegistroDecisiones), findsNothing);
  });

  testWidgets('Al resolver las tres marcas aparece el estado vacío y el resumen se recalcula',
      (tester) async {
    await _montar(tester);
    expect(find.text('35 de 40'), findsOneWidget);

    await _tocar(tester, find.text('A · Correcta (+1,0)'));
    await _tocar(tester, find.text('D · Incorrecta (0,0)'));
    // La tercera marca decide si la estudiante aprueba (2,6 o 3,0), y la tarjeta lo dice.
    expect(find.text('Define si aprueba'), findsOneWidget);
    await _tocar(tester, find.text('C · Correcta (+1,0)'));

    expect(find.text('No quedan marcas por revisar'), findsOneWidget);
    expect(find.text('Anular · sin efecto'), findsNothing);
    expect(
      find.text('Parcial 2 · 43 estudiantes · sin marcas dudosas por revisar'),
      findsOneWidget,
    );
    // Las tres notas definitivas (4,6, 3,2 y 3,0) entran al resumen: 38 aprobados de 43.
    expect(find.text('38 de 43'), findsOneWidget);
    expect(find.text('88 %'), findsOneWidget);

    await _tocar(tester, find.text('Restablecer el ejemplo'));
    expect(find.text('1 de 3 pendientes'), findsOneWidget);
    expect(find.text('35 de 40'), findsOneWidget);
  });

  testWidgets('Los filtros cambian la lista y sus conteos salen de los datos', (tester) async {
    await _montar(tester);
    expect(_tarjetasEstudiante, findsNWidgets(8));
    expect(find.text('Ver los 43 estudiantes'), findsOneWidget);

    await _tocar(tester, find.text('Requieren revisión'));
    expect(_tarjetasEstudiante, findsNWidgets(3));
    expect(_enLista('Valeria Montes Arrieta'), findsOneWidget);
    expect(_enLista('Andrés Felipe Caraballo'), findsOneWidget);
    expect(_enLista('Laura Daniela Pájaro Ruiz'), findsOneWidget);

    await _tocar(tester, find.text('Doble marcación'));
    expect(_tarjetasEstudiante, findsOneWidget);
    expect(_enLista('Andrés Felipe Caraballo'), findsOneWidget);

    await _tocar(tester, find.text('Calificados'));
    expect(_enLista('Valeria Montes Arrieta'), findsNothing);
    await _tocar(tester, find.text('Ver los 40 estudiantes'));
    expect(_tarjetasEstudiante, findsNWidgets(40));
  });

  testWidgets('El orden «Menor nota» pone primero la nota más baja', (tester) async {
    await _montar(tester);

    await _tocar(tester, find.text('Menor nota'));

    final menor = SesionRevision.ejemplo()
        .filas
        .reduce((a, b) => b.notaDecimas < a.notaDecimas ? b : a);
    final primera = tester.widget<TarjetaEstudiante>(_tarjetasEstudiante.first);
    expect(primera.fila.estudiante.codigo, menor.estudiante.codigo);
  });

  testWidgets('El caso nuevo entra en 220 ms y sin transición si se pide menos movimiento',
      (tester) async {
    Opacity opacidadDelCaso() => tester.widget<Opacity>(
          find.ancestor(of: find.byType(TarjetaCaso), matching: find.byType(Opacity)).first,
        );

    await _montar(tester);
    await Scrollable.ensureVisible(tester.element(find.text('Anular · sin efecto')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Anular · sin efecto'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 110));
    expect(opacidadDelCaso().opacity, inExclusiveRange(0, 1));
    await tester.pumpAndSettle();
    expect(opacidadDelCaso().opacity, 1);

    // Se desmonta primero para empezar con el ejemplo intacto.
    await tester.pumpWidget(const SizedBox());
    await _montar(tester, sinAnimaciones: true);
    await Scrollable.ensureVisible(tester.element(find.text('Anular · sin efecto')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Anular · sin efecto'));
    await tester.pump();
    expect(find.text('1 de 2 pendientes'), findsOneWidget);
    expect(opacidadDelCaso().opacity, 1);
  });

  testWidgets('No desborda a 390 px en ningún estado de la pantalla', (tester) async {
    await _montar(tester);
    expect(tester.takeException(), isNull);

    await _tocar(tester, find.text('Ver los 43 estudiantes'));
    await _tocar(tester, find.text('A · Correcta (+1,0)'));
    expect(tester.takeException(), isNull, reason: 'caso de doble marcación y registro');
    await _tocar(tester, find.text('Anular · sin efecto'));
    await _tocar(tester, find.text('Anular · sin efecto'));
    expect(find.text('No quedan marcas por revisar'), findsOneWidget);
    await _tocar(tester, find.text('Requieren revisión'));
    expect(find.text('Nadie en este filtro'), findsOneWidget);
    expect(tester.takeException(), isNull, reason: 'estado vacío del caso y de la lista');
  });

  testWidgets('No desborda a 390 px con el texto del sistema al 130 %', (tester) async {
    await _montar(tester, escalaTexto: 1.3);
    expect(tester.takeException(), isNull);
  });

  testWidgets('En escritorio el caso va a la izquierda y la lista a la derecha', (tester) async {
    await _montar(tester, tamano: const Size(1280, 800));
    expect(tester.takeException(), isNull);

    final caso = tester.getRect(find.byType(TarjetaCaso));
    final resumen = tester.getRect(find.byType(ResumenGrupo));
    expect(resumen.left, greaterThan(caso.right));
    expect(resumen.top, lessThan(caso.bottom));
  });
}
