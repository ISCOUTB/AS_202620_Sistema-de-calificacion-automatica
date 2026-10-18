import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/common/api/servicio_salud.dart';
import 'package:frontend/common/tema/tema.dart';
import 'package:frontend/features/pauta/data/datos_ejemplo_pauta.dart';
import 'package:frontend/features/pauta/data/servicio_distractores.dart';
import 'package:frontend/features/pauta/views/pantalla_pauta.dart';

typedef _Proponer = Future<ResultadoDistractores> Function(SolicitudDistractores);

/// Lo que devolvería la API para la pregunta 2, `f(x) = x·sin(x)`: tres distractores que
/// pasaron la regla y dos que no.
const _resultado = ResultadoDistractores(
  distractores: [
    DistractorPropuesto(
      expresion: 'cos(x)',
      error: 'Olvida la regla del producto: deriva cada factor por separado y multiplica.',
    ),
    DistractorPropuesto(
      expresion: 'sin(x) - x·cos(x)',
      error: 'Cambia el signo de la derivada del seno.',
    ),
    DistractorPropuesto(
      expresion: 'x·cos(x)',
      error: 'Deriva solo el segundo factor y deja el primero como está.',
    ),
  ],
  descartados: [
    PropuestaDescartada(
      expresion: 'sin(x) + x·cos(x)',
      motivo: 'Repite la respuesta correcta',
    ),
    PropuestaDescartada(expresion: 'x·sin(x)', motivo: 'Repite la función sin derivar'),
  ],
);

const _mensaje503 =
    'El proveedor de IA tardó más de 20 s. Puede volver a pedirlo o escribir los distractores '
    'a mano.';

/// Los dos textos del 429, como los redacta `autoria/presupuesto.py`.
const _mensaje429Minuto = 'Se alcanzó el límite de 6 solicitudes por minuto al proveedor. '
    'Puede volver a pedirlo en 3 s.';
const _mensaje429Dia = 'Se agotó el presupuesto diario de 150 solicitudes al proveedor. Habrá '
    'cupo en unos 5 h; mientras tanto, los distractores se pueden escribir a mano.';

final _campoEnunciado = find.byKey(const Key('campo-enunciado'));
final _campoRespuesta = find.byKey(const Key('campo-respuesta'));
final _botonProponer = find.byKey(const Key('boton-proponer'));
Finder _pregunta(int numero) => find.byKey(ValueKey('pregunta-$numero'));

/// Monta la pantalla sola, con el tema real, un sustituto de la API y el estado de conexión
/// que se quiera. Devuelve el notificador para cambiar la conexión durante la prueba.
Future<ValueNotifier<EstadoApi>> _montar(
  WidgetTester tester, {
  _Proponer? proponer,
  EstadoApi estado = EstadoApi.conectada,
  double ancho = 1280,
  double alto = 900,
  bool sinAnimaciones = false,
}) async {
  tester.view.physicalSize = Size(ancho, alto);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);

  final estadoApi = ValueNotifier(estado);
  await tester.pumpWidget(MaterialApp(
    theme: construirTema(),
    builder: sinAnimaciones
        ? (context, hijo) => MediaQuery(
              data: MediaQuery.of(context).copyWith(disableAnimations: true),
              child: hijo!,
            )
        : null,
    home: Scaffold(
      body: PantallaPauta(
        proponerDistractores: proponer ?? (_) async => _resultado,
        estadoApi: estadoApi,
      ),
    ),
  ));
  await tester.pumpAndSettle();
  return estadoApi;
}

/// Lleva el elemento a la vista antes de tocarlo: la pantalla es más alta que la ventana.
Future<void> _tocar(WidgetTester tester, Finder objetivo) async {
  await tester.ensureVisible(objetivo);
  await tester.pumpAndSettle();
  await tester.tap(objetivo);
  await tester.pumpAndSettle();
}

String _texto(WidgetTester tester, Finder campo) =>
    tester.widget<TextField>(campo).controller!.text;

VoidCallback? _accionProponer(WidgetTester tester) =>
    tester.widget<FilledButton>(_botonProponer).onPressed;

VoidCallback? _accionVolverAPedir(WidgetTester tester) =>
    tester.widget<OutlinedButton>(find.byKey(const Key('boton-volver-a-pedir'))).onPressed;

void main() {
  testWidgets('Elegir una pregunta de ejemplo llena el formulario del generador', (tester) async {
    await _montar(tester);
    final pregunta = examenEjemplo.preguntas[1];

    await _tocar(tester, _pregunta(2));

    expect(_texto(tester, _campoEnunciado), pregunta.enunciado);
    expect(_texto(tester, _campoRespuesta), pregunta.respuestaCorrecta);
    expect(find.text('Pregunta 2 · Regla del producto'), findsOneWidget);
    expect(_accionProponer(tester), isNotNull);
  });

  testWidgets('El botón queda deshabilitado sin enunciado, sin respuesta o sin conexión',
      (tester) async {
    final estado = await _montar(tester);

    expect(_accionProponer(tester), isNull, reason: 'formulario vacío');

    await tester.enterText(_campoEnunciado, 'Calcule la derivada de f(x) = x·sin(x).');
    await tester.pump();
    expect(_accionProponer(tester), isNull, reason: 'falta la respuesta correcta');

    await tester.enterText(_campoEnunciado, '   ');
    await tester.enterText(_campoRespuesta, 'sin(x) + x·cos(x)');
    await tester.pump();
    expect(_accionProponer(tester), isNull, reason: 'el enunciado solo tiene espacios');
    // El error va debajo del campo, y solo después de que el docente lo tocó.
    expect(find.text('Escriba el enunciado de la pregunta.'), findsOneWidget);

    await tester.enterText(_campoEnunciado, 'Calcule la derivada de f(x) = x·sin(x).');
    await tester.pump();
    expect(_accionProponer(tester), isNotNull, reason: 'los dos campos están llenos');
    expect(find.text('Escriba el enunciado de la pregunta.'), findsNothing);

    estado.value = EstadoApi.sinConexion;
    await tester.pump();
    expect(_accionProponer(tester), isNull, reason: 'la API no responde');
    expect(find.text('Sin conexión con la API'), findsOneWidget);

    estado.value = EstadoApi.conectada;
    await tester.pump();
    expect(_accionProponer(tester), isNotNull, reason: 'volvió la conexión');
    expect(find.text('Sin conexión con la API'), findsNothing);
  });

  testWidgets('Mientras espera muestra la forma de las tarjetas y el límite de 20 s',
      (tester) async {
    final respuesta = Completer<ResultadoDistractores>();
    await _montar(tester, proponer: (_) => respuesta.future);

    await _tocar(tester, _pregunta(2));
    await _tocar(tester, _botonProponer);

    expect(find.byKey(const Key('esqueleto-propuestas')), findsOneWidget);
    expect(find.textContaining('20 s'), findsOneWidget);
    expect(find.byType(CircularProgressIndicator), findsNothing);
    expect(_accionProponer(tester), isNull, reason: 'no se pide dos veces a la vez');

    respuesta.complete(_resultado);
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('esqueleto-propuestas')), findsNothing);
    expect(find.text('cos(x)'), findsOneWidget);
  });

  testWidgets(
      'El resultado muestra cada distractor con su diagnóstico y las descartadas con '
      'su motivo', (tester) async {
    await _montar(tester);
    await _tocar(tester, _pregunta(2));
    await _tocar(tester, _botonProponer);

    for (final distractor in _resultado.distractores) {
      expect(find.text(distractor.expresion), findsOneWidget);
      expect(find.text(distractor.error), findsOneWidget);
    }
    expect(find.text('Diagnóstico: error que representa'), findsNWidgets(3));
    for (final letra in ['B', 'C', 'D']) {
      expect(find.text(letra), findsOneWidget);
    }
    expect(find.text('Clave'), findsOneWidget);
    expect(find.text('Pedir otras propuestas'), findsOneWidget);
    // La frecuencia solo existe después de aplicar el examen.
    expect(find.textContaining('Frecuencia'), findsNothing);
    // La nota sobre las expresiones equivalentes está siempre a la vista.
    expect(find.textContaining('no detecta una expresión equivalente'), findsOneWidget);

    // Las descartadas empiezan plegadas, con el conteo a la vista.
    expect(find.text('2 propuestas descartadas'), findsOneWidget);
    expect(find.textContaining('Repite la respuesta correcta'), findsNothing);

    await _tocar(tester, find.byKey(const Key('cabecera-descartadas')));
    expect(find.textContaining('Repite la respuesta correcta'), findsOneWidget);
    expect(find.textContaining('Repite la función sin derivar'), findsOneWidget);
  });

  testWidgets('Usar y Descartar registran la decisión del docente y se pueden deshacer',
      (tester) async {
    await _montar(tester);
    await _tocar(tester, _pregunta(2));
    await _tocar(tester, _botonProponer);

    await _tocar(tester, find.text('Usar').first);
    expect(find.text('Usted la eligió'), findsOneWidget);
    expect(find.text('Usar'), findsNWidgets(2));

    await _tocar(tester, find.text('Descartar').first);
    expect(find.text('Usted la descartó'), findsOneWidget);
    expect(find.textContaining('1 elegida'), findsOneWidget);

    await _tocar(tester, find.text('Deshacer').first);
    expect(find.text('Usted la eligió'), findsNothing);
    expect(find.text('Usar'), findsNWidgets(2));
  });

  testWidgets('Un 503 muestra el mensaje de la API como advertencia y permite volver a pedir',
      (tester) async {
    var llamadas = 0;
    await _montar(tester, proponer: (_) async {
      llamadas++;
      throw const ExcepcionDistractores(_mensaje503, proveedorNoDisponible: true);
    });
    await _tocar(tester, _pregunta(2));
    await _tocar(tester, _botonProponer);

    expect(find.byKey(const Key('aviso-proveedor')), findsOneWidget);
    expect(find.text(_mensaje503), findsOneWidget);
    expect(find.text('Volver a pedir'), findsOneWidget);

    await _tocar(tester, find.text('Volver a pedir'));
    expect(llamadas, 2);
  });

  testWidgets('Otra falla se muestra como error y no ofrece volver a pedir', (tester) async {
    const mensaje = 'No se pudo contactar con la API. Revise su conexión y vuelva a intentarlo.';
    await _montar(tester, proponer: (_) async => throw const ExcepcionDistractores(mensaje));
    await _tocar(tester, _pregunta(2));
    await _tocar(tester, _botonProponer);

    expect(find.byKey(const Key('aviso-error')), findsOneWidget);
    expect(find.text(mensaje), findsOneWidget);
    expect(find.text('Volver a pedir'), findsNothing);
  });

  testWidgets('Un 429 por minuto muestra el mensaje de la API y cuenta hasta poder volver a pedir',
      (tester) async {
    var llamadas = 0;
    await _montar(tester, proponer: (_) async {
      llamadas++;
      throw const ExcepcionDistractores(
        _mensaje429Minuto,
        presupuestoAgotado: true,
        reintentarEn: Duration(seconds: 3),
      );
    });
    await _tocar(tester, _pregunta(2));
    await _tocar(tester, _botonProponer);

    expect(find.byKey(const Key('aviso-presupuesto')), findsOneWidget);
    expect(find.text(_mensaje429Minuto), findsOneWidget);
    expect(find.textContaining('429'), findsNothing);
    expect(find.text('Volver a pedir en 3 s'), findsOneWidget);
    expect(_accionVolverAPedir(tester), isNull);
    expect(_accionProponer(tester), isNull);

    await tester.pump(const Duration(seconds: 1));
    expect(find.text('Volver a pedir en 2 s'), findsOneWidget);

    await tester.pump(const Duration(seconds: 2));
    expect(find.text('Volver a pedir'), findsOneWidget);
    expect(_accionVolverAPedir(tester), isNotNull);
    expect(_accionProponer(tester), isNotNull);

    await _tocar(tester, find.text('Volver a pedir'));
    expect(llamadas, 2);
  });

  testWidgets('Con el límite diario agotado el aviso no ofrece volver a pedir', (tester) async {
    await _montar(
      tester,
      proponer: (_) async => throw const ExcepcionDistractores(
        _mensaje429Dia,
        presupuestoAgotado: true,
        reintentarEn: Duration(hours: 5),
      ),
    );
    await _tocar(tester, _pregunta(2));
    await _tocar(tester, _botonProponer);

    expect(find.byKey(const Key('aviso-presupuesto')), findsOneWidget);
    expect(find.text(_mensaje429Dia), findsOneWidget);
    expect(find.byKey(const Key('boton-volver-a-pedir')), findsNothing);
    // El formulario sigue disponible: el docente puede volver más tarde sin recargar.
    expect(_accionProponer(tester), isNotNull);
  });

  testWidgets('Un 429 sin la espera legible deja volver a pedir de inmediato', (tester) async {
    await _montar(
      tester,
      proponer: (_) async =>
          throw const ExcepcionDistractores(_mensaje429Minuto, presupuestoAgotado: true),
    );
    await _tocar(tester, _pregunta(2));
    await _tocar(tester, _botonProponer);

    expect(find.byKey(const Key('aviso-presupuesto')), findsOneWidget);
    expect(find.text('Volver a pedir'), findsOneWidget);
    expect(_accionVolverAPedir(tester), isNotNull);
  });

  testWidgets('La solicitud lleva los tres campos con la cantidad elegida', (tester) async {
    final solicitudes = <SolicitudDistractores>[];
    await _montar(tester, proponer: (solicitud) async {
      solicitudes.add(solicitud);
      return _resultado;
    });

    await tester.enterText(_campoEnunciado, '  Calcule la derivada de f(x) = ln(cos(x)).  ');
    await tester.enterText(_campoRespuesta, '-tan(x)');
    await tester.pump();
    await _tocar(tester, _botonProponer);

    expect(solicitudes.single.aJson(), {
      'enunciado': 'Calcule la derivada de f(x) = ln(cos(x)).',
      'respuesta_correcta': '-tan(x)',
      'cantidad': 3,
    });

    await _tocar(
      tester,
      find.descendant(
        of: find.byKey(const Key('selector-cantidad')),
        matching: find.text('5'),
      ),
    );
    await _tocar(tester, _botonProponer);
    expect(solicitudes.last.cantidad, 5);
    expect(solicitudes.last.respuestaCorrecta, '-tan(x)');

    // «Pedir otras propuestas» repite la última solicitud tal cual.
    await _tocar(tester, find.text('Pedir otras propuestas'));
    expect(solicitudes, hasLength(3));
    expect(solicitudes.last.aJson(), solicitudes[1].aJson());
  });

  testWidgets('En escritorio la lista va a la izquierda y el generador a la derecha',
      (tester) async {
    await _montar(tester, ancho: 1280);

    final lista = tester.getTopLeft(_pregunta(1));
    final generador = tester.getTopLeft(find.text('Generador de distractores diagnósticos'));
    expect(generador.dx, greaterThan(lista.dx + 300));
    expect(generador.dy, lessThan(lista.dy));
  });

  testWidgets('A 390 px no hay desbordes y elegir una pregunta lleva al generador', (tester) async {
    final estado = await _montar(tester, ancho: 390, alto: 844);

    final generador = find.text('Generador de distractores diagnósticos');
    expect(tester.getTopLeft(generador).dy, greaterThan(tester.getTopLeft(_pregunta(10)).dy));

    await _tocar(tester, _pregunta(10));
    // En teléfono el formulario queda diez filas más abajo: la vista baja hasta él.
    final y = tester.getTopLeft(generador).dy;
    expect(y, inInclusiveRange(0, 844));
    expect(find.text('Pregunta 10 · Trigonométricas y cadena'), findsOneWidget);

    await _tocar(tester, _botonProponer);
    await _tocar(tester, find.byKey(const Key('cabecera-descartadas')));
    await _tocar(tester, find.text('Usar').first);
    await _tocar(tester, find.text('Descartar').first);

    estado.value = EstadoApi.sinConexion;
    await tester.pumpAndSettle();
    expect(find.text('Sin conexión con la API'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('A 390 px los avisos de error tampoco desbordan', (tester) async {
    await _montar(
      tester,
      ancho: 390,
      alto: 844,
      proponer: (_) async =>
          throw const ExcepcionDistractores(_mensaje503, proveedorNoDisponible: true),
    );
    await _tocar(tester, _pregunta(1));
    await _tocar(tester, _botonProponer);

    expect(find.text('Volver a pedir'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('A 390 px el aviso del 429 con la cuenta regresiva no desborda', (tester) async {
    await _montar(
      tester,
      ancho: 390,
      alto: 844,
      proponer: (_) async => throw const ExcepcionDistractores(
        _mensaje429Minuto,
        presupuestoAgotado: true,
        reintentarEn: Duration(seconds: 59),
      ),
    );
    await _tocar(tester, _pregunta(1));
    await _tocar(tester, _botonProponer);

    expect(find.text('Volver a pedir en 59 s'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Los resultados aparecen con un fundido de 220 ms', (tester) async {
    await _montar(tester);
    await _tocar(tester, _pregunta(2));
    await tester.ensureVisible(_botonProponer);
    await tester.pumpAndSettle();
    await tester.tap(_botonProponer);
    await tester.pump();

    expect(_opacidades(tester), contains(lessThan(1.0)), reason: 'recién llegado');
    await tester.pump(const Duration(milliseconds: 220));
    expect(_opacidades(tester), everyElement(1.0), reason: 'terminó la transición');
  });

  testWidgets('Con el movimiento reducido, los resultados aparecen sin transición', (tester) async {
    await _montar(tester, sinAnimaciones: true);
    await _tocar(tester, _pregunta(2));
    await tester.ensureVisible(_botonProponer);
    await tester.pumpAndSettle();
    await tester.tap(_botonProponer);
    await tester.pump();

    expect(_opacidades(tester), isNotEmpty);
    expect(_opacidades(tester), everyElement(1.0));
  });
}

/// La opacidad de los fundidos que envuelven la primera tarjeta de distractor.
List<double> _opacidades(WidgetTester tester) => tester
    .widgetList<FadeTransition>(
      find.ancestor(
        of: find.byKey(const ValueKey('distractor-0')),
        matching: find.byType(FadeTransition),
      ),
    )
    .map((f) => f.opacity.value)
    .toList();
