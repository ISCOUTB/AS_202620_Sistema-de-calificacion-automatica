import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/common/api/servicio_salud.dart';
import 'package:frontend/common/tema/tema.dart';
import 'package:frontend/features/pauta/data/datos_ejemplo_pauta.dart';
import 'package:frontend/features/pauta/data/servicio_distractores.dart';
import 'package:frontend/features/pauta/data/servicio_preguntas.dart';
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
  _Api? api,
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
        guardarDistractores: api?.guardar,
        listarDistractoresGuardados: api?.listarGuardados,
        quitarDistractoresGuardados: api?.quitar,
        listarPreguntas: api?.listarPreguntas,
        agregarPregunta: api?.agregar,
        eliminarPregunta: api?.eliminar,
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
    expect(find.text('Sin conexión con el servidor'), findsOneWidget);

    estado.value = EstadoApi.conectada;
    await tester.pump();
    expect(_accionProponer(tester), isNotNull, reason: 'volvió la conexión');
    expect(find.text('Sin conexión con el servidor'), findsNothing);
  });

  testWidgets('Mientras espera muestra la forma de las tarjetas y que tarda unos segundos',
      (tester) async {
    final respuesta = Completer<ResultadoDistractores>();
    await _montar(tester, proponer: (_) => respuesta.future);

    await _tocar(tester, _pregunta(2));
    await _tocar(tester, _botonProponer);

    expect(find.byKey(const Key('esqueleto-propuestas')), findsOneWidget);
    expect(find.textContaining('Suele tardar unos segundos'), findsOneWidget);
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

  testWidgets('El aviso de los datos de ejemplo solo dice que las preguntas son de ejemplo',
      (tester) async {
    await _montar(tester);

    expect(find.textContaining('Estas preguntas son de ejemplo.'), findsOneWidget);
    expect(find.textContaining('sí funciona'), findsNothing);
  });

  testWidgets('La nota de las propuestas dice que las elegidas se copian al examen',
      (tester) async {
    await _montar(tester);
    await _tocar(tester, _pregunta(2));
    await _tocar(tester, _botonProponer);

    expect(
      find.text('Ninguna propuesta entra al examen sin su aprobación. Las que elija no quedan '
          'guardadas aquí; cópielas a su examen.'),
      findsOneWidget,
    );
    expect(find.textContaining('Por ahora'), findsNothing);
    expect(find.text('Guardar distractores'), findsNothing);
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
    // Antes, el botón principal seguía activo, y cada clic era
    // otro 429 contado en los rechazos de /metricas. Ahora espera lo que dijo Retry-After...
    expect(_accionProponer(tester), isNull);

    // ...y vuelve solo cuando pasa: el docente no tiene que recargar la página.
    await tester.pump(const Duration(hours: 5));
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

    // «Pedir otras propuestas» repite la última solicitud y pide propuestas nuevas, no las que
    // la API tiene guardadas para esa misma pregunta (ADR-0019).
    await _tocar(tester, find.text('Pedir otras propuestas'));
    expect(solicitudes, hasLength(3));
    expect(solicitudes.last.aJson(), {...solicitudes[1].aJson(), 'otras': true});
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
    expect(find.text('Sin conexión con el servidor'), findsOneWidget);
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
  // --- Regenerar una y guardar las elegidas (ADR-0029) ---------------------------------------

  Finder tarjeta(int i) => find.byKey(ValueKey('distractor-$i'));
  Finder enTarjeta(int i, String texto) =>
      find.descendant(of: tarjeta(i), matching: find.text(texto));

  /// La API sustituta: la solicitud normal devuelve `_resultado`; la de una sola, [nueva].
  _Proponer conRegenerar(List<SolicitudDistractores> pedidas, DistractorPropuesto nueva) =>
      (solicitud) async {
        pedidas.add(solicitud);
        if (solicitud.cantidad == 1) {
          return ResultadoDistractores(distractores: [nueva], descartados: const []);
        }
        return _resultado;
      };

  const nueva = DistractorPropuesto(
    expresion: 'sin(x) + cos(x)',
    error: 'Deriva cada factor y los suma, sin la regla del producto.',
  );

  testWidgets('Al descartar aparece Regenerar a la izquierda de Deshacer, solo en esa tarjeta',
      (tester) async {
    await _montar(tester);
    await _tocar(tester, _pregunta(2));
    await _tocar(tester, _botonProponer);
    expect(find.text('Regenerar'), findsNothing);

    await _tocar(tester, enTarjeta(1, 'Descartar'));

    expect(find.text('Regenerar'), findsOneWidget);
    expect(enTarjeta(1, 'Regenerar'), findsOneWidget);
    expect(
      tester.getCenter(enTarjeta(1, 'Regenerar')).dx,
      lessThan(tester.getCenter(enTarjeta(1, 'Deshacer')).dx),
    );
  });

  testWidgets('Regenerar pide una sola propuesta nueva y cambia solo esa tarjeta', (tester) async {
    final pedidas = <SolicitudDistractores>[];
    await _montar(tester, proponer: conRegenerar(pedidas, nueva));
    await _tocar(tester, _pregunta(2));
    await _tocar(tester, _botonProponer);
    await _tocar(tester, enTarjeta(0, 'Usar'));
    await _tocar(tester, enTarjeta(1, 'Descartar'));

    await _tocar(tester, enTarjeta(1, 'Regenerar'));

    expect(pedidas.last.cantidad, 1);
    expect(pedidas.last.otras, isTrue);
    expect(pedidas.last.enunciado, pedidas.first.enunciado);
    expect(enTarjeta(1, 'sin(x) + cos(x)'), findsOneWidget);
    expect(enTarjeta(1, 'Propuesta del modelo'), findsOneWidget);
    expect(find.text('sin(x) - x·cos(x)'), findsNothing);
    expect(enTarjeta(0, 'Usted la eligió'), findsOneWidget, reason: 'las demás no cambian');
    expect(enTarjeta(2, 'x·cos(x)'), findsOneWidget);
  });

  testWidgets('Si la nueva repite otra que ya está, lo dice y la tarjeta sigue descartada',
      (tester) async {
    await _montar(tester, proponer: conRegenerar([], _resultado.distractores.first));
    await _tocar(tester, _pregunta(2));
    await _tocar(tester, _botonProponer);
    await _tocar(tester, enTarjeta(1, 'Descartar'));

    await _tocar(tester, enTarjeta(1, 'Regenerar'));

    expect(find.textContaining('que ya está'), findsOneWidget);
    expect(enTarjeta(1, 'Usted la descartó'), findsOneWidget);
    expect(enTarjeta(1, 'sin(x) - x·cos(x)'), findsOneWidget);
  });

  testWidgets('Si regenerar falla, la tarjeta dice el motivo y deja volver a intentarlo',
      (tester) async {
    await _montar(tester, proponer: (solicitud) async {
      if (solicitud.cantidad == 1) {
        throw const ExcepcionDistractores(_mensaje503, proveedorNoDisponible: true);
      }
      return _resultado;
    });
    await _tocar(tester, _pregunta(2));
    await _tocar(tester, _botonProponer);
    await _tocar(tester, enTarjeta(1, 'Descartar'));

    await _tocar(tester, enTarjeta(1, 'Regenerar'));

    expect(enTarjeta(1, _mensaje503), findsOneWidget);
    expect(enTarjeta(1, 'Regenerar'), findsOneWidget);
  });

  // --- Guardar, la lista y las preguntas agregadas (ADR-0029 y ADR-0030) ---------------------

  final ejemplo2 = examenEjemplo.preguntas[1];
  const guardadosDe2 = [
    DistractorPropuesto(expresion: 'x·cos(x)', error: 'Deriva solo el segundo factor.'),
    DistractorPropuesto(expresion: 'cos(2x)', error: 'Confunde el producto con el ángulo doble.'),
  ];
  final guardadoDe2 = _guardado(ejemplo2.enunciado, ejemplo2.respuestaCorrecta, guardadosDe2);
  final grupoGuardadas = find.text('Con distractores guardados');
  final botonGuardar = find.byKey(const Key('boton-guardar-distractores'));
  final botonNueva = find.byKey(const Key('boton-nueva-pregunta'));
  final campoNuevoEnunciado = find.byKey(const Key('campo-nueva-enunciado'));
  final campoNuevaRespuesta = find.byKey(const Key('campo-nueva-respuesta'));
  final botonAgregar = find.byKey(const Key('boton-agregar-pregunta'));
  Finder fila(String llave) => find.byKey(ValueKey('pregunta-$llave'));
  Finder enFila(Finder fila, String texto) =>
      find.descendant(of: fila, matching: find.text(texto));
  final xLnX = _agregada('Calcule la derivada de f(x) = x·ln(x).', 'ln(x) + 1');

  testWidgets('Guardar manda las elegidas y pasa la pregunta al final de la lista, con ellas',
      (tester) async {
    final api = _Api();
    await _montar(tester, api: api);
    await _tocar(tester, _pregunta(2));
    await _tocar(tester, _botonProponer);

    expect(tester.widget<FilledButton>(botonGuardar).onPressed, isNull, reason: 'sin elegir');
    expect(find.textContaining('Las que guarde quedan con la pregunta'), findsOneWidget);
    expect(grupoGuardadas, findsNothing);

    await _tocar(tester, enTarjeta(0, 'Usar'));
    await _tocar(tester, enTarjeta(2, 'Usar'));
    await _tocar(tester, botonGuardar);

    expect(api.enviadas.single.map((d) => d.expresion), ['cos(x)', 'x·cos(x)']);
    expect(
      find.text('Se guardaron 2 distractores. La pregunta quedó al final de la lista.'),
      findsOneWidget,
    );
    expect(find.text('Guardada'), findsNWidgets(2));
    expect(tester.widget<FilledButton>(botonGuardar).onPressed, isNull, reason: 'ya guardadas');
    expect(_y(tester, _pregunta(2)), greaterThan(_y(tester, grupoGuardadas)));
    expect(_y(tester, grupoGuardadas), greaterThan(_y(tester, _pregunta(10))));
    expect(enFila(_pregunta(2), 'x·cos(x)'), findsOneWidget);
    expect(api.preguntas, isEmpty, reason: 'una pregunta de ejemplo no se agrega');
  });

  testWidgets('Al abrir, lo guardado está al final de la lista con sus distractores',
      (tester) async {
    await _montar(tester, api: _Api(guardados: [guardadoDe2]));

    expect(_y(tester, _pregunta(2)), greaterThan(_y(tester, grupoGuardadas)));
    expect(_y(tester, grupoGuardadas), greaterThan(_y(tester, _pregunta(10))));
    expect(enFila(_pregunta(2), 'x·cos(x)'), findsOneWidget);
    expect(enFila(_pregunta(2), 'cos(2x)'), findsOneWidget);
    expect(enFila(_pregunta(2), 'Quitar'), findsOneWidget);
  });

  testWidgets('Elegir una guardada muestra sus distractores sin pedirle nada al modelo',
      (tester) async {
    final pedidas = <SolicitudDistractores>[];
    await _montar(
      tester,
      api: _Api(guardados: [guardadoDe2]),
      proponer: (solicitud) async {
        pedidas.add(solicitud);
        return _resultado;
      },
    );

    await _tocar(tester, _pregunta(2));

    expect(pedidas, isEmpty);
    expect(_texto(tester, _campoEnunciado), ejemplo2.enunciado);
    expect(find.text('Distractores guardados'), findsOneWidget);
    expect(enTarjeta(0, 'x·cos(x)'), findsOneWidget);
    expect(enTarjeta(1, 'cos(2x)'), findsOneWidget);
    expect(find.text('Guardada'), findsNWidgets(2));
  });

  testWidgets('Pedir otras desde una guardada trae lo guardado primero, sin repetirlo',
      (tester) async {
    await _montar(tester, api: _Api(guardados: [guardadoDe2]));
    await _tocar(tester, _pregunta(2));

    await _tocar(tester, find.text('Pedir otras propuestas'));

    expect(enTarjeta(0, 'x·cos(x)'), findsOneWidget);
    expect(enTarjeta(1, 'cos(2x)'), findsOneWidget);
    expect(find.text('Guardada'), findsNWidgets(2));
    expect(find.text('Propuesta del modelo'), findsNWidgets(2), reason: 'x·cos(x) ya estaba');
  });

  testWidgets('Quitar devuelve la pregunta de ejemplo a su número', (tester) async {
    final api = _Api(guardados: [guardadoDe2]);
    await _montar(tester, api: api);
    await _tocar(tester, _pregunta(2));

    await _tocar(tester, find.byKey(ValueKey('quitar-${guardadoDe2.llave}')));

    expect(api.quitadas, [guardadoDe2.llave]);
    expect(grupoGuardadas, findsNothing);
    expect(_y(tester, _pregunta(2)), greaterThan(_y(tester, _pregunta(1))));
    expect(_y(tester, _pregunta(2)), lessThan(_y(tester, _pregunta(3))));
    expect(find.text('Guardada'), findsNothing, reason: 'las tarjetas ya no están guardadas');
  });

  testWidgets('Una agregada vuelve arriba al quitarle lo guardado', (tester) async {
    final api = _Api(
      preguntas: [xLnX],
      guardados: [_guardado(xLnX.enunciado, xLnX.respuestaCorrecta, guardadosDe2)],
    );
    await _montar(tester, api: api);
    expect(_y(tester, fila(xLnX.llave)), greaterThan(_y(tester, grupoGuardadas)));

    await _tocar(tester, find.byKey(ValueKey('quitar-${xLnX.llave}')));

    expect(_y(tester, fila(xLnX.llave)), lessThan(_y(tester, _pregunta(1))));
    expect(enFila(fila(xLnX.llave), 'Agregada por usted'), findsOneWidget);
  });

  testWidgets('«+» abre una fila para agregar; la nueva queda arriba y se puede elegir',
      (tester) async {
    final api = _Api();
    await _montar(tester, api: api);
    expect(campoNuevoEnunciado, findsNothing);

    await _tocar(tester, botonNueva);
    await tester.enterText(campoNuevoEnunciado, 'Calcule la derivada de f(x) = x·ln(x).');
    await tester.enterText(campoNuevaRespuesta, 'ln(x) + 1');
    await _tocar(tester, botonAgregar);

    final nueva = api.preguntas.single;
    expect(_y(tester, fila(nueva.llave)), lessThan(_y(tester, _pregunta(1))));
    expect(_texto(tester, campoNuevoEnunciado), isEmpty, reason: 'lista para agregar otra');

    await _tocar(tester, enFila(fila(nueva.llave), 'Agregada por usted'));
    expect(_texto(tester, _campoEnunciado), 'Calcule la derivada de f(x) = x·ln(x).');
    expect(_texto(tester, _campoRespuesta), 'ln(x) + 1');
  });

  testWidgets('No agrega una pregunta vacía ni una que ya está en la lista', (tester) async {
    final api = _Api();
    await _montar(tester, api: api);
    await _tocar(tester, botonNueva);

    await _tocar(tester, botonAgregar);
    expect(find.text('Escriba el enunciado y la respuesta correcta.'), findsOneWidget);

    await tester.enterText(campoNuevoEnunciado, ' ${ejemplo2.enunciado}');
    await tester.enterText(campoNuevaRespuesta, ejemplo2.respuestaCorrecta);
    await _tocar(tester, botonAgregar);
    expect(find.text('Esa pregunta ya está en la lista.'), findsOneWidget);
    expect(api.preguntas, isEmpty);
  });

  testWidgets('Si el servidor no agrega la pregunta, la fila dice por qué', (tester) async {
    final api = _Api()..fallaAlAgregar = const ExcepcionPreguntas('El servidor respondió 500.');
    await _montar(tester, api: api);
    await _tocar(tester, botonNueva);

    await tester.enterText(campoNuevoEnunciado, xLnX.enunciado);
    await tester.enterText(campoNuevaRespuesta, xLnX.respuestaCorrecta);
    await _tocar(tester, botonAgregar);

    expect(find.text('El servidor respondió 500.'), findsOneWidget);
    expect(_texto(tester, campoNuevoEnunciado), xLnX.enunciado, reason: 'no se pierde lo escrito');
  });

  testWidgets('Eliminar quita una pregunta agregada de la lista', (tester) async {
    final api = _Api(preguntas: [xLnX]);
    await _montar(tester, api: api);
    expect(fila(xLnX.llave), findsOneWidget);

    await _tocar(tester, find.byKey(ValueKey('eliminar-${xLnX.llave}')));

    expect(api.eliminadas, [xLnX.llave]);
    expect(fila(xLnX.llave), findsNothing);
  });

  testWidgets('Guardar una pregunta escrita en el generador la agrega a la lista', (tester) async {
    final api = _Api();
    await _montar(tester, api: api);
    await tester.enterText(_campoEnunciado, xLnX.enunciado);
    await tester.enterText(_campoRespuesta, xLnX.respuestaCorrecta);
    await _tocar(tester, _botonProponer);
    await _tocar(tester, enTarjeta(0, 'Usar'));

    await _tocar(tester, botonGuardar);

    final agregada = api.preguntas.single;
    expect(agregada.enunciado, xLnX.enunciado);
    expect(_y(tester, fila(agregada.llave)), greaterThan(_y(tester, grupoGuardadas)));

    await _tocar(tester, find.byKey(ValueKey('quitar-${agregada.llave}')));
    expect(_y(tester, fila(agregada.llave)), lessThan(_y(tester, _pregunta(1))));
  });

  testWidgets('Si no se puede cargar la lista, lo dice y deja reintentar', (tester) async {
    final api = _Api(guardados: [guardadoDe2])
      ..fallaAlListar = const ExcepcionPreguntas('El servidor respondió 500.');
    await _montar(tester, api: api);

    expect(find.text('No se pudieron cargar sus preguntas ni sus distractores guardados.'),
        findsOneWidget);
    expect(grupoGuardadas, findsNothing);

    api.fallaAlListar = null;
    await _tocar(tester, find.byKey(const Key('boton-reintentar-lista')));
    expect(grupoGuardadas, findsOneWidget);
  });

  testWidgets('Si guardar falla, lo dice con el motivo de la API', (tester) async {
    final api = _Api()..fallaAlGuardar = const ExcepcionDistractores('«cos(x)» está dos veces.');
    await _montar(tester, api: api);
    await _tocar(tester, _pregunta(2));
    await _tocar(tester, _botonProponer);
    await _tocar(tester, enTarjeta(0, 'Usar'));

    await _tocar(tester, botonGuardar);

    expect(find.text('«cos(x)» está dos veces.'), findsOneWidget);
    expect(find.text('Guardada'), findsNothing);
    expect(grupoGuardadas, findsNothing);
  });

  testWidgets('Con preguntas a nombre del docente, el aviso dice cuáles son de ejemplo',
      (tester) async {
    await _montar(tester, api: _Api());

    expect(find.textContaining('Las preguntas numeradas son de ejemplo.'), findsOneWidget);
  });

  // --- Cambiar de pregunta en la lista ----------------------------------------------------------

  final hayTarjetas = find.byKey(const ValueKey('distractor-0'));
  final sinPropuestas = find.text('Todavía no hay propuestas');

  testWidgets('Elegir otra pregunta quita los distractores guardados de la anterior',
      (tester) async {
    await _montar(tester, api: _Api(guardados: [guardadoDe2]));
    await _tocar(tester, _pregunta(2));
    expect(find.text('Distractores guardados'), findsOneWidget);

    await _tocar(tester, _pregunta(3));

    expect(_texto(tester, _campoRespuesta), examenEjemplo.preguntas[2].respuestaCorrecta);
    expect(find.text('Distractores guardados'), findsNothing);
    expect(hayTarjetas, findsNothing);
    expect(sinPropuestas, findsOneWidget);
  });

  testWidgets('Elegir otra pregunta quita las propuestas de la anterior', (tester) async {
    await _montar(tester);
    await _tocar(tester, _pregunta(2));
    await _tocar(tester, _botonProponer);
    expect(hayTarjetas, findsOneWidget);

    await _tocar(tester, _pregunta(3));

    expect(hayTarjetas, findsNothing);
    expect(sinPropuestas, findsOneWidget);
  });

  testWidgets('Elegir la misma pregunta otra vez deja sus propuestas', (tester) async {
    await _montar(tester);
    await _tocar(tester, _pregunta(2));
    await _tocar(tester, _botonProponer);

    await _tocar(tester, _pregunta(2));

    expect(hayTarjetas, findsOneWidget);
  });

  testWidgets('Las propuestas que llegan tarde, de la pregunta anterior, no se muestran',
      (tester) async {
    final respuesta = Completer<ResultadoDistractores>();
    await _montar(tester, proponer: (_) => respuesta.future);
    await _tocar(tester, _pregunta(2));
    await _tocar(tester, _botonProponer);

    await _tocar(tester, _pregunta(3));
    respuesta.complete(_resultado);
    await tester.pumpAndSettle();

    expect(hayTarjetas, findsNothing);
    expect(sinPropuestas, findsOneWidget);
    expect(_accionProponer(tester), isNotNull, reason: 'se puede pedir para la nueva');
  });

  testWidgets('Mientras corre la espera del límite, cambiar de pregunta deja el aviso',
      (tester) async {
    await _montar(
      tester,
      proponer: (_) async => throw const ExcepcionDistractores(
        _mensaje429Minuto,
        presupuestoAgotado: true,
        reintentarEn: Duration(seconds: 30),
      ),
    );
    await _tocar(tester, _pregunta(2));
    await _tocar(tester, _botonProponer);

    await _tocar(tester, _pregunta(3));

    expect(find.byKey(const Key('aviso-presupuesto')), findsOneWidget);
    expect(_accionProponer(tester), isNull, reason: 'otra solicitud sería otro 429');
    await tester.pump(const Duration(seconds: 31));
  });

  testWidgets('A 390 px la lista, la fila nueva, Regenerar y Guardar no desbordan',
      (tester) async {
    await _montar(
      tester,
      ancho: 390,
      alto: 844,
      proponer: conRegenerar([], nueva),
      api: _Api(preguntas: [xLnX], guardados: [guardadoDe2]),
    );
    await _tocar(tester, botonNueva);
    await _tocar(tester, _pregunta(3));
    await _tocar(tester, _botonProponer);
    await _tocar(tester, enTarjeta(0, 'Usar'));
    await _tocar(tester, enTarjeta(1, 'Descartar'));
    await _tocar(tester, botonGuardar);

    expect(tester.takeException(), isNull);
  });
}

double _y(WidgetTester tester, Finder objetivo) => tester.getTopLeft(objetivo).dy;

/// La llave con que la API sustituta reconoce una pregunta. La real es un sha256; aquí basta con
/// que la misma pregunta dé la misma.
String _llave(String enunciado, String respuesta) =>
    'l${formaDeLaPregunta(enunciado, respuesta).hashCode.toRadixString(16)}';

PreguntaDelDocente _agregada(String enunciado, String respuesta) => PreguntaDelDocente(
      llave: _llave(enunciado, respuesta),
      enunciado: enunciado,
      respuestaCorrecta: respuesta,
      agregadaEn: DateTime.utc(2026, 11, 22, 9),
    );

DistractoresGuardados _guardado(
  String enunciado,
  String respuesta,
  List<DistractorPropuesto> distractores,
) =>
    DistractoresGuardados(
      llave: _llave(enunciado, respuesta),
      enunciado: enunciado,
      respuestaCorrecta: respuesta,
      distractores: distractores,
      guardadoEn: DateTime.utc(2026, 11, 22, 9),
    );

/// La API sustituta de lo guardado y de las preguntas agregadas, con su estado: lo que se agrega
/// o se guarda aparece en la próxima lista, y lo que se quita o se elimina, no.
class _Api {
  _Api({
    List<PreguntaDelDocente> preguntas = const [],
    List<DistractoresGuardados> guardados = const [],
  })  : preguntas = [...preguntas],
        guardados = [...guardados];

  final List<PreguntaDelDocente> preguntas;
  final List<DistractoresGuardados> guardados;
  final enviadas = <List<DistractorPropuesto>>[];
  final quitadas = <String>[];
  final eliminadas = <String>[];
  Object? fallaAlListar;
  Object? fallaAlAgregar;
  Object? fallaAlGuardar;
  int _minuto = 0;

  DateTime _ahora() => DateTime.utc(2026, 11, 23, 9, ++_minuto);

  Future<List<PreguntaDelDocente>> listarPreguntas() async {
    if (fallaAlListar case final falla?) throw falla;
    return [...preguntas];
  }

  Future<List<DistractoresGuardados>> listarGuardados() async {
    if (fallaAlListar case final falla?) throw falla;
    return [...guardados];
  }

  Future<PreguntaDelDocente> agregar(String enunciado, String respuesta) async {
    if (fallaAlAgregar case final falla?) throw falla;
    final pregunta = PreguntaDelDocente(
      llave: _llave(enunciado, respuesta),
      enunciado: enunciado.trim(),
      respuestaCorrecta: respuesta.trim(),
      agregadaEn: _ahora(),
    );
    preguntas.insert(0, pregunta);
    return pregunta;
  }

  Future<void> eliminar(String llave) async {
    eliminadas.add(llave);
    preguntas.removeWhere((p) => p.llave == llave);
  }

  Future<DistractoresGuardados> guardar(
    SolicitudDistractores pregunta,
    List<DistractorPropuesto> elegidos,
  ) async {
    if (fallaAlGuardar case final falla?) throw falla;
    enviadas.add(elegidos);
    final nuevos = _guardado(pregunta.enunciado, pregunta.respuestaCorrecta, elegidos);
    guardados
      ..removeWhere((g) => g.llave == nuevos.llave)
      ..add(nuevos);
    return nuevos;
  }

  Future<void> quitar(String llave) async {
    quitadas.add(llave);
    guardados.removeWhere((g) => g.llave == llave);
  }
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
