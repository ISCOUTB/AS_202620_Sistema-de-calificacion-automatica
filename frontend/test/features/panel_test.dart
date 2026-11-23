import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/common/tema/tema.dart';
import 'package:frontend/common/widgets/q_aviso_datos_ejemplo.dart';
import 'package:frontend/features/carga/data/servicio_examenes.dart';
import 'package:frontend/features/carga/data/servicio_resultados.dart' show ExcepcionDeConsulta;
import 'package:frontend/features/panel/data/modelos_panel.dart';
import 'package:frontend/features/panel/views/formato_cifras.dart';
import 'package:frontend/features/panel/views/pantalla_panel.dart';

/// El JSON de `GET /examenes/{examen_id}/panel`, con la forma exacta que publica la API.
Map<String, dynamic> _json({
  required String examenId,
  required String nombre,
  List<int> notas = const [20, 28, 34, 39, 43, 50],
  int aprobados = 4,
  num? promedio = 35.67,
  num? desviacion = 9.81,
  Map<String, int> marcas = const {
    'correctas': 170,
    'incorrectas': 67,
    'tenues_o_dudosas': 1,
    'dobles': 1,
    'en_blanco': 1,
    'pendientes': 2,
  },
  List<Map<String, dynamic>>? preguntas,
}) =>
    {
      'examen_id': examenId,
      'nombre': nombre,
      'resumen': {
        'hojas_recibidas': notas.length + 1,
        'hojas_leidas': notas.length,
        'hojas_con_nota': notas.length,
        'hojas_sin_nota': 0,
        'hojas_ilegibles': 0,
        'hojas_en_revision': marcas['pendientes']! > 0 ? 2 : 0,
        'preguntas_por_revisar': marcas['pendientes'],
        'aprobados': aprobados,
        'promedio_en_decimas': promedio,
        'desviacion_en_decimas': desviacion,
        'nota_aprobatoria_en_decimas': 30,
      },
      'marcas': marcas,
      'notas_en_decimas': notas,
      'preguntas': preguntas ??
          [
            {
              'numero': 1,
              'correcta': 'A',
              'aciertos': 6,
              'hojas': 6,
              'marcadas': {'A': 6, 'B': 0, 'C': 0, 'D': 0},
              'en_blanco': 0,
              'dobles': 0,
              'dudosas': 0,
            },
            {
              'numero': 2,
              'correcta': 'B',
              'aciertos': 2,
              'hojas': 6,
              'marcadas': {'A': 0, 'B': 2, 'C': 4, 'D': 0},
              'en_blanco': 0,
              'dobles': 0,
              'dudosas': 0,
            },
          ],
    };

final _parcial = PanelDelExamen.desdeJson(_json(examenId: '000001', nombre: 'Parcial 1'));
final _anterior = PanelDelExamen.desdeJson(_json(
  examenId: 'PARCIAL-1',
  nombre: 'PARCIAL-1',
  notas: const [],
  aprobados: 0,
  promedio: null,
  desviacion: null,
  marcas: const {
    'correctas': 0,
    'incorrectas': 0,
    'tenues_o_dudosas': 0,
    'dobles': 0,
    'en_blanco': 0,
    'pendientes': 0,
  },
  preguntas: const [],
));

const _examenes = [
  ExamenConClave(examenId: 'PARCIAL-1', habilitada: true),
  ExamenConClave(examenId: '000001', nombre: 'Parcial 1', habilitada: true),
];

/// Monta el panel con servicios sustitutos. El alto sobra a propósito: la página se desplaza, y
/// lo que interesa es que nada se desborde a lo ancho.
Future<List<String>> _montar(
  WidgetTester tester, {
  double ancho = 1280,
  bool sinMovimiento = false,
  List<ExamenConClave> examenes = _examenes,
  Future<PanelDelExamen> Function(String)? consultar,
  bool conServicios = true,
}) async {
  tester.view.physicalSize = Size(ancho, 3000);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  final pedidos = <String>[];

  await tester.pumpWidget(
    MaterialApp(
      theme: construirTema(),
      builder: (context, hijo) => MediaQuery(
        data: MediaQuery.of(context).copyWith(disableAnimations: sinMovimiento),
        child: hijo!,
      ),
      home: Scaffold(
        body: conServicios
            ? PantallaPanel(
                listarExamenes: () async => examenes,
                consultarPanel: (examenId) async {
                  pedidos.add(examenId);
                  if (consultar != null) return consultar(examenId);
                  return examenId == '000001' ? _parcial : _anterior;
                },
              )
            : const PantallaPanel(),
      ),
    ),
  );
  await tester.pumpAndSettle();
  return pedidos;
}

void main() {
  group('Los modelos', () {
    test('Leen el JSON de la API y pasan las notas de décimas a la escala de 0 a 5', () {
      final resumen = _parcial.resumen;

      expect(_parcial.notas, [2.0, 2.8, 3.4, 3.9, 4.3, 5.0]);
      expect(resumen.promedio, closeTo(3.567, 1e-9));
      expect(resumen.desviacion, closeTo(0.981, 1e-9));
      expect(resumen.notaAprobatoria, 3.0);
      expect(resumen.porLeer, 1);
      expect(formatearPorcentaje(resumen.porcentajeAprobacion, decimales: 1), '66,7\u00a0%');
      expect(_parcial.marcas.total, 240);
      expect(_parcial.preguntas[1].distractorMasMarcado, 'C');
    });

    test('Sin hojas con nota no hay promedio y la aprobación es 0, no NaN', () {
      expect(_anterior.resumen.promedio, isNull);
      expect(_anterior.resumen.porcentajeAprobacion, 0);
    });

    test('Los tramos de notas empiezan en 1,0 y el 5,0 cae en el último', () {
      final tramos = tramosDeNotas(_parcial.notas);

      expect(tramos.length, 8);
      expect((tramos.first.desde, tramos.last.hasta), (1.0, 5.0));
      expect([for (final t in tramos) t.hojas], [0, 0, 1, 1, 1, 1, 1, 1]);
      // Un 3,0 abre el tramo de aprobados aunque llegue como 2,9999999.
      expect(tramosDeNotas([3.0, 2.9999999999])[4].hojas, 2);
    });

    test('Con una nota menor que 1,0 los tramos empiezan en 0,0', () {
      final tramos = tramosDeNotas([0.4, 4.0]);

      expect(tramos.length, 10);
      expect(tramos.first.hojas, 1);
    });

    test('La densidad normal tiene su pico en la media y es simétrica', () {
      expect(densidadNormal(3, 3, 1), closeTo(0.39894, 1e-5));
      expect(densidadNormal(2, 3, 1), closeTo(densidadNormal(4, 3, 1), 1e-12));
    });
  });

  testWidgets('Ya no avisa que la vista usa datos de ejemplo', (tester) async {
    await _montar(tester);

    expect(find.byType(QAvisoDatosEjemplo), findsNothing);
    expect(find.textContaining('ejemplo'), findsNothing);
    // Lo de los datos de ejemplo que ya no existe: competencias y fórmulas inventadas.
    expect(find.textContaining('Regla de la cadena'), findsNothing);
    expect(find.textContaining('competencias'), findsNothing);
  });

  testWidgets('Abre el examen más reciente del docente y pide sus cifras', (tester) async {
    final pedidos = await _montar(tester);

    expect(pedidos, ['000001']);
    expect(find.text('Parcial 1'), findsOneWidget);
  });

  testWidgets('Las métricas muestran las cifras del examen', (tester) async {
    await _montar(tester);

    expect(find.text('3,6'), findsOneWidget);
    expect(find.text(formatearPorcentaje(400 / 6, decimales: 1)), findsOneWidget);
    expect(find.textContaining('4 de 6 con nota de 3,0 o más'), findsOneWidget);
    expect(find.text('7'), findsOneWidget, reason: 'hojas recibidas');
    expect(find.text('Falta 1 por leer'), findsOneWidget);
    expect(find.text('2'), findsWidgets, reason: 'revisión pendiente');
    expect(find.textContaining('desviación 1,0'), findsOneWidget);
  });

  testWidgets('La barra de marcas dice con texto cuántas hay de cada tipo', (tester) async {
    await _montar(tester);

    for (final (nombre, cantidad) in [
      ('Correctas', 170),
      ('Incorrectas', 67),
      ('Marca doble', 1),
      ('Tenue o dudosa', 1),
      ('En blanco', 1),
    ]) {
      expect(find.text(nombre), findsOneWidget, reason: nombre);
      final porcentaje = formatearPorcentaje(cantidad * 100 / 240, decimales: 1);
      expect(find.text('$cantidad · $porcentaje'), findsWidgets, reason: nombre);
      expect(find.byTooltip('$nombre: $cantidad ($porcentaje)'), findsOneWidget, reason: nombre);
    }
    expect(find.textContaining('2 de las tenues o dobles esperan su revisión'), findsOneWidget);
    expect(
      find.bySemanticsLabel(RegExp(r'^Cómo se marcaron las respuestas: Correctas, 170')),
      findsOneWidget,
    );
  });

  testWidgets('La distribución de notas tiene la campana y un tooltip por tramo', (tester) async {
    await _montar(tester);

    expect(find.text('Distribución de las notas'), findsOneWidget);
    expect(find.text('Campana: media 3,57, desviación 0,98'), findsOneWidget);
    expect(find.text('Aprobado (3,0 o más)'), findsOneWidget);
    expect(find.text('No aprobado'), findsOneWidget);
    final una = formatearPorcentaje(100 / 6);
    expect(find.byTooltip('De 4,5 a 5,0: 1 hoja ($una)'), findsOneWidget);
    expect(find.byTooltip('De 3,0 a menos de 3,5: 1 hoja ($una)'), findsOneWidget);
    expect(
      find.byTooltip('De 1,0 a menos de 1,5: 0 hojas (${formatearPorcentaje(0)})'),
      findsOneWidget,
    );
  });

  testWidgets('Los aciertos por pregunta señalan la que más costó', (tester) async {
    await _montar(tester);

    final frase = tester.widget<Text>(find.byKey(const Key('pregunta-mas-dificil'))).data!;
    expect(frase, contains('la pregunta 2'));
    expect(frase, contains('(2 de 6)'));
    expect(frase, contains('la incorrecta más marcada fue la C (4 veces)'));
    expect(
      find.byWidgetPredicate(
        (w) => w is Tooltip && (w.message ?? '').startsWith('Pregunta 2: '),
      ),
      findsOneWidget,
    );

    await tester.tap(find.text('Ver como tabla'));
    await tester.pumpAndSettle();
    expect(find.byType(DataTable), findsOneWidget);
  });

  testWidgets('Elegir otro examen pide sus cifras y cambia el conjunto de datos', (tester) async {
    final pedidos = await _montar(tester);

    await tester.tap(find.text('Parcial 1'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('PARCIAL-1'));
    await tester.pumpAndSettle();

    expect(pedidos, ['000001', 'PARCIAL-1']);
    expect(find.text('—'), findsOneWidget, reason: 'sin promedio');
    expect(find.text('Aún no hay hojas con nota'), findsOneWidget);
    expect(find.textContaining('4 de 6'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Sin animaciones, el cambio de examen es inmediato', (tester) async {
    await _montar(tester, sinMovimiento: true);

    await tester.tap(find.text('Parcial 1'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('PARCIAL-1'));
    await tester.pumpAndSettle();

    expect(find.textContaining('4 de 6'), findsNothing);
  });

  testWidgets('Sin exámenes, dice cómo crear el primero', (tester) async {
    final pedidos = await _montar(tester, examenes: const []);

    expect(pedidos, isEmpty);
    expect(find.text('Todavía no tiene exámenes'), findsOneWidget);
  });

  testWidgets('Sin los servicios, no inventa cifras', (tester) async {
    await _montar(tester, conServicios: false);

    expect(find.text('El panel necesita el servidor'), findsOneWidget);
    expect(find.text('3,6'), findsNothing);
  });

  testWidgets('Si las cifras no llegan, lo dice y deja volver a intentar', (tester) async {
    var falla = true;
    await _montar(
      tester,
      consultar: (examenId) async {
        if (falla) throw const ExcepcionDeConsulta('Ese examen no existe en su cuenta.');
        return _parcial;
      },
    );

    expect(find.text('Ese examen no existe en su cuenta.'), findsOneWidget);
    falla = false;
    await tester.tap(find.text('Volver a intentar'));
    await tester.pumpAndSettle();
    expect(find.text('3,6'), findsOneWidget);
  });

  testWidgets('El botón de actualizar vuelve a pedir las cifras', (tester) async {
    final pedidos = await _montar(tester);

    await tester.tap(find.byTooltip('Actualizar las cifras'));
    await tester.pumpAndSettle();

    expect(pedidos, ['000001', '000001']);
  });

  for (final ancho in [390.0, 1280.0]) {
    testWidgets('No se desborda a ${ancho.toInt()} px de ancho', (tester) async {
      await _montar(tester, ancho: ancho);
      expect(tester.takeException(), isNull);

      await tester.tap(find.text('Parcial 1'));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
      await tester.tap(find.text('PARCIAL-1'));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    });
  }
}
