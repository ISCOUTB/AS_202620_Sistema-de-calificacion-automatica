import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/app/app.dart';
import 'package:frontend/app/marco_app.dart';
import 'package:frontend/app/servicios.dart';
import 'package:frontend/app/sesion_actual.dart';
import 'package:frontend/common/api/sesion.dart';
import 'package:frontend/features/carga/data/servicio_carga.dart';
import 'package:frontend/features/carga/data/servicio_examenes.dart';
import 'package:frontend/features/pauta/data/servicio_clave.dart';
import 'package:frontend/features/pauta/data/servicio_distractores.dart';
import 'package:frontend/features/revision/data/servicio_revision.dart';
import 'package:frontend/main.dart';

/// Servicios sustitutos: la aplicación entera se monta sin backend y sin diálogo de archivos.
ServiciosApp _servicios({
  bool apiConectada = true,
  Future<ArchivoSeleccionado?> Function()? tomarFoto,
  Future<RevisionDelExamen> Function(String)? consultarRevision,
}) =>
    ServiciosApp(
      tomarFoto: tomarFoto,
      listarExamenes: consultarRevision == null
          ? null
          : () async => const [ExamenConClave(examenId: 'PROTOTIPO-R05', habilitada: true)],
      consultarRevision: consultarRevision,
      verificarSalud: () async => apiConectada,
      seleccionarArchivos: ({alAvanzar}) async => [
        ArchivoSeleccionado(nombre: 'hoja1.png', contenido: Uint8List.fromList(const [1, 2, 3])),
      ],
      subirHojas: (examenId, archivos) async => ResultadoCarga(
        totalProcesados: archivos.length,
        aceptadas: const [],
        rechazados: const [],
      ),
      proponerDistractores: (solicitud) async =>
          const ResultadoDistractores(distractores: [], descartados: []),
    );

Future<void> _montar(
  WidgetTester tester, {
  required Size tamano,
  bool apiConectada = true,
  Future<ArchivoSeleccionado?> Function()? tomarFoto,
  Future<RevisionDelExamen> Function(String)? consultarRevision,
}) async {
  tester.view.physicalSize = tamano;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    QuantiaApp(
      servicios: _servicios(
        apiConectada: apiConectada,
        tomarFoto: tomarFoto,
        consultarRevision: consultarRevision,
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('Con cámara, la sección Carga ofrece tomar la foto desde la aplicación',
      (tester) async {
    await _montar(
      tester,
      tamano: const Size(390, 1700),
      tomarFoto: () async =>
          ArchivoSeleccionado(nombre: 'foto 14.32.05.jpg', contenido: Uint8List(4)),
    );
    await tester.tap(find.text('Carga'));
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.text('Tomar foto'));
    await tester.tap(find.text('Tomar foto'));
    await tester.pumpAndSettle();

    expect(find.text('foto 14.32.05.jpg'), findsOneWidget);
  });

  testWidgets('Cambiar el ancho de la ventana no borra el examen ni las fotos elegidas',
      (tester) async {
    // En ancho la navegación es un riel junto al contenido, y en angosto una barra abajo: antes,
    // cruzar ese ancho creaba las pantallas de nuevo y se perdía lo elegido.
    await _montar(tester, tamano: const Size(1280, 1400));
    await tester.tap(find.text('Carga'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'CALC-2026-02');
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Seleccionar archivos'));
    await tester.tap(find.text('Seleccionar archivos'));
    await tester.pumpAndSettle();
    expect(find.text('hoja1.png'), findsOneWidget);

    tester.view.physicalSize = const Size(390, 1700);
    await tester.pumpAndSettle();

    expect(find.text('hoja1.png'), findsOneWidget);
    expect(find.text('CALC-2026-02'), findsOneWidget);
  });

  testWidgets('Volver a Revisión pide otra vez la revisión del examen elegido', (tester) async {
    // La sección queda viva mientras se mira otra: sin pedirla de nuevo, las hojas subidas en
    // Carga no aparecían hasta recargar la página.
    final pedidos = <String>[];
    await _montar(
      tester,
      tamano: const Size(1280, 1400),
      consultarRevision: (examen) async {
        pedidos.add(examen);
        return RevisionDelExamen(examenId: examen, hojas: const []);
      },
    );
    await tester.tap(find.text(Seccion.revision.etiqueta).last);
    await tester.pumpAndSettle();
    await tester.tap(find.byType(DropdownMenu<String>));
    await tester.pumpAndSettle();
    await tester.tap(find.text('PROTOTIPO-R05').last);
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pumpAndSettle();
    expect(pedidos, ['PROTOTIPO-R05']);

    await tester.tap(find.text(Seccion.carga.etiqueta).last);
    await tester.pumpAndSettle();
    await tester.tap(find.text(Seccion.revision.etiqueta).last);
    await tester.pumpAndSettle();

    expect(pedidos, ['PROTOTIPO-R05', 'PROTOTIPO-R05']);
  });

  testWidgets('La barra superior muestra el nombre del sistema y que está conectado',
      (tester) async {
    await _montar(tester, tamano: const Size(1280, 900));

    expect(find.text(nombreSistema), findsOneWidget);
    expect(find.text('Conectado'), findsOneWidget);
  });

  testWidgets('Sin conexión, la barra lo dice y ofrece volver a comprobar', (tester) async {
    await _montar(tester, tamano: const Size(1280, 900), apiConectada: false);

    expect(find.text('Sin conexión'), findsOneWidget);
    expect(find.byTooltip('Volver a comprobar la conexión'), findsOneWidget);
  });

  testWidgets('En escritorio la navegación es un riel lateral con las cuatro secciones',
      (tester) async {
    await _montar(tester, tamano: const Size(1280, 900));

    expect(find.byType(NavigationRail), findsOneWidget);
    expect(find.byType(NavigationBar), findsNothing);
    for (final seccion in Seccion.values) {
      expect(find.text(seccion.etiqueta), findsWidgets);
    }
  });

  testWidgets('En teléfono la navegación es una barra inferior', (tester) async {
    await _montar(tester, tamano: const Size(390, 844));

    expect(find.byType(NavigationBar), findsOneWidget);
    expect(find.byType(NavigationRail), findsNothing);
  });

  testWidgets('Cambiar de sección no pierde lo escrito en otra', (tester) async {
    await _montar(tester, tamano: const Size(1280, 900));

    await tester.tap(find.text(Seccion.carga.etiqueta).last);
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).first, 'CALC-2026-02');

    await tester.tap(find.text(Seccion.panel.etiqueta).last);
    await tester.pumpAndSettle();
    await tester.tap(find.text(Seccion.carga.etiqueta).last);
    await tester.pumpAndSettle();

    expect(find.text('CALC-2026-02'), findsOneWidget);
  });

  test('La sección inicial se lee de la URL y cae al panel si no se reconoce', () {
    expect(seccionDesdeUrl(Uri.parse('https://x/?seccion=carga')), Seccion.carga);
    expect(seccionDesdeUrl(Uri.parse('https://x/?seccion=pauta')), Seccion.pauta);
    expect(seccionDesdeUrl(Uri.parse('https://x/?seccion=otra')), Seccion.panel);
    expect(seccionDesdeUrl(Uri.parse('https://x/')), Seccion.panel);
  });

  testWidgets('Una clave registrada en Pauta aparece en la carga sin recargar la página',
      (tester) async {
    tester.view.physicalSize = const Size(1280, 2600);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    final claves = <String, ClaveDelExamen>{};
    await tester.pumpWidget(QuantiaApp(
      servicios: ServiciosApp(
        verificarSalud: () async => true,
        seleccionarArchivos: ({alAvanzar}) async => const [],
        subirHojas: (examenId, archivos) async =>
            const ResultadoCarga(totalProcesados: 0, aceptadas: [], rechazados: []),
        proponerDistractores: (solicitud) async =>
            const ResultadoDistractores(distractores: [], descartados: []),
        listarExamenes: () async => [
          for (final clave in claves.values)
            ExamenConClave(examenId: clave.examenId, habilitada: clave.habilitada),
        ],
        consultarClave: (examen) async => claves[examen],
        guardarClave: (examen, respuestas) async => claves[examen] =
            ClaveDelExamen(examenId: examen, respuestas: respuestas, sePuedeCambiar: true),
        habilitarClave: (examen) async => claves[examen]!,
      ),
    ));
    await tester.pumpAndSettle();

    await tester.tap(find.text(Seccion.pauta.etiqueta).last);
    await tester.pumpAndSettle();
    await tester.enterText(find.widgetWithText(TextField, 'Examen'), 'QUIZ-9');
    await tester.pump(const Duration(milliseconds: 500));
    await tester.pumpAndSettle();
    await tester.enterText(find.widgetWithText(TextField, 'Pegar las respuestas'), 'ABCD');
    await tester.tap(find.text('Llenar'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Llenar la cuadrícula'));
    await tester.pumpAndSettle();
    await tester.ensureVisible(find.text('Guardar clave'));
    await tester.tap(find.text('Guardar clave'));
    await tester.pumpAndSettle();

    await tester.tap(find.text(Seccion.carga.etiqueta).last);
    await tester.pumpAndSettle();
    await tester.tap(find.byType(DropdownMenu<String>));
    await tester.pumpAndSettle();

    expect(find.text('QUIZ-9'), findsWidgets);
  });

  group('La puerta de la sesión', () {
    final sesionDePrueba = Sesion(
      token: 'v1.abc.def',
      correo: 'profe@utb.edu.co',
      vence: DateTime.utc(2026, 11, 22, 6),
    );

    Future<SesionActual> montarConSesion(
      WidgetTester tester, {
      Size tamano = const Size(1280, 900),
      Sesion? guardada,
      Future<Sesion> Function(String correo, String contrasena)? iniciarSesion,
    }) async {
      tester.view.physicalSize = tamano;
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.reset);
      final almacen = AlmacenEnMemoria();
      if (guardada != null) almacen.guardar(guardada, recordar: true);
      final sesion = SesionActual(almacen: almacen, reloj: () => DateTime.utc(2026, 11, 21, 18));
      await tester.pumpWidget(QuantiaApp(
        servicios: _servicios(),
        sesion: sesion,
        iniciarSesion: iniciarSesion ?? (correo, contrasena) async => sesionDePrueba,
      ));
      await tester.pumpAndSettle();
      return sesion;
    }

    testWidgets('Sin sesión abre la entrada y no las secciones', (tester) async {
      await montarConSesion(tester);

      expect(find.text('Bienvenido a QuantIA'), findsOneWidget);
      expect(find.byType(NavigationRail), findsNothing);
    });

    testWidgets('Al entrar muestra las secciones y el correo en la barra', (tester) async {
      final pedidas = <(String, String)>[];
      final sesion = await montarConSesion(tester, iniciarSesion: (correo, contrasena) async {
        pedidas.add((correo, contrasena));
        return sesionDePrueba;
      });

      await tester.enterText(find.widgetWithText(TextField, 'Correo institucional'), 'profe@utb.edu.co');
      await tester.enterText(find.widgetWithText(TextField, 'Contraseña del docente'), 'calculo-diferencial');
      await tester.tap(find.text('Iniciar sesión'));
      await tester.pumpAndSettle();

      expect(pedidas, [('profe@utb.edu.co', 'calculo-diferencial')]);
      expect(sesion.sesion, sesionDePrueba);
      expect(find.byType(NavigationRail), findsOneWidget);
      expect(find.text('profe@utb.edu.co'), findsOneWidget);
    });

    testWidgets('Con una sesión guardada que todavía vale entra directo', (tester) async {
      await montarConSesion(tester, guardada: sesionDePrueba);

      expect(find.byType(NavigationRail), findsOneWidget);
    });

    testWidgets('Cerrar sesión pide confirmación, y cancelar no la cierra', (tester) async {
      final sesion = await montarConSesion(tester, guardada: sesionDePrueba);

      await tester.tap(find.byTooltip('Cerrar sesión'));
      await tester.pumpAndSettle();

      expect(find.text('¿Cerrar sesión?'), findsOneWidget);
      await tester.tap(find.text('Cancelar'));
      await tester.pumpAndSettle();

      expect(find.text('¿Cerrar sesión?'), findsNothing);
      expect(sesion.sesion, sesionDePrueba);
      expect(find.byType(NavigationRail), findsOneWidget);
    });

    testWidgets('Tocar fuera del cuadro tampoco cierra la sesión', (tester) async {
      final sesion = await montarConSesion(tester, guardada: sesionDePrueba);

      await tester.tap(find.byTooltip('Cerrar sesión'));
      await tester.pumpAndSettle();
      await tester.tapAt(const Offset(10, 890));
      await tester.pumpAndSettle();

      expect(find.text('¿Cerrar sesión?'), findsNothing);
      expect(sesion.sesion, sesionDePrueba);
    });

    testWidgets('Al confirmar, cierra la sesión y vuelve a la entrada', (tester) async {
      final sesion = await montarConSesion(tester, guardada: sesionDePrueba);

      await tester.tap(find.byTooltip('Cerrar sesión'));
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(FilledButton, 'Cerrar sesión'));
      await tester.pumpAndSettle();

      expect(sesion.sesion, isNull);
      expect(find.text('Bienvenido a QuantIA'), findsOneWidget);
      expect(find.textContaining('terminó'), findsNothing);
    });

    testWidgets('Si la API dice que la sesión ya no vale, vuelve a la entrada y lo explica',
        (tester) async {
      final sesion = await montarConSesion(tester, guardada: sesionDePrueba);

      sesion.vencer();
      await tester.pumpAndSettle();

      expect(find.text('Su sesión terminó. Vuelva a entrar.'), findsOneWidget);
    });

    testWidgets('En teléfono, la barra deja el botón de cerrar sesión y esconde el correo',
        (tester) async {
      await montarConSesion(tester, tamano: const Size(390, 844), guardada: sesionDePrueba);

      expect(find.byTooltip('Cerrar sesión'), findsOneWidget);
      expect(find.text('profe@utb.edu.co'), findsNothing);
      expect(tester.takeException(), isNull);
    });
  });
}
