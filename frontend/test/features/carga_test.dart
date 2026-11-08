import 'dart:async';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/common/api/servicio_salud.dart';
import 'package:frontend/common/tema/tema.dart';
import 'package:frontend/features/carga/data/servicio_carga.dart';
import 'package:frontend/features/carga/data/servicio_examenes.dart';
import 'package:frontend/features/carga/data/servicio_resultados.dart';
import 'package:frontend/features/carga/views/pantalla_carga.dart';

ArchivoSeleccionado _archivo(String nombre, [int bytes = 3]) =>
    ArchivoSeleccionado(nombre: nombre, contenido: Uint8List(bytes));

final _hoja = _archivo('hoja1.jpg');

/// El reporte que daría el backend si aceptara todo y lo encolara.
ResultadoCarga _todoEncolado(List<ArchivoSeleccionado> archivos) => ResultadoCarga(
      totalProcesados: archivos.length,
      aceptadas: [
        for (final a in archivos) HojaAceptada(nombreArchivo: a.nombre, trabajoId: 'id-${a.nombre}'),
      ],
      rechazados: const [],
    );

/// Monta la pantalla de carga con las dos operaciones sustituidas: ni diálogo de archivos ni
/// backend. Es lo que permite probar el aspecto A-01 del lado del docente sin levantar nada.
Widget _pantallaCarga({
  List<ArchivoSeleccionado>? seleccion,
  Future<List<ArchivoSeleccionado>> Function({void Function(int, int)? alAvanzar})? seleccionar,
  Future<ResultadoCarga> Function(String, List<ArchivoSeleccionado>)? subir,
  ValueNotifier<EstadoApi>? estadoApi,
  Future<ResultadosDelExamen> Function(String)? consultar,
  Future<List<ExamenConClave>> Function()? listar,
  void Function(String)? alRevisar,
  ValueNotifier<int>? revisionesGuardadas,
}) {
  final estado = estadoApi ?? ValueNotifier(EstadoApi.conectada);
  if (estadoApi == null) addTearDown(estado.dispose);
  return MaterialApp(
    theme: construirTema(),
    home: Scaffold(
      body: PantallaCarga(
        seleccionarArchivos: seleccionar ?? ({alAvanzar}) async => seleccion ?? [_hoja],
        subirHojas: subir ?? (examenId, archivos) async => _todoEncolado(archivos),
        estadoApi: estado,
        consultarResultados: consultar,
        listarExamenes: listar,
        alRevisar: alRevisar,
        revisionesGuardadas: revisionesGuardadas,
      ),
    ),
  );
}

/// El botón que contiene [texto]. Se busca por su texto y no por tipo exacto porque
/// `FilledButton.icon` construye una subclase privada.
ButtonStyleButton _boton(WidgetTester tester, String texto) => tester.widget<ButtonStyleButton>(
      find.ancestor(
        of: find.text(texto),
        matching: find.byWidgetPredicate((w) => w is ButtonStyleButton),
      ),
    );

/// Toca lo que encuentre [buscador] después de llevarlo a la vista: en la composición de dos
/// columnas, el botón de subir puede quedar debajo del borde de la superficie de prueba.
Future<void> _tocar(WidgetTester tester, Finder buscador) async {
  // Primero se deja terminar lo que esté en curso: al escribir en un campo, la página se desplaza
  // para mostrarlo, y si ese desplazamiento termina después de `ensureVisible`, se lleva el
  // botón fuera de la vista.
  await tester.pumpAndSettle();
  await tester.ensureVisible(buscador);
  await tester.pumpAndSettle();
  await tester.tap(buscador);
  await tester.pumpAndSettle();
}

/// Escribe el examen, elige los archivos y sube el lote.
Future<void> _subirLote(WidgetTester tester, {String examen = 'CALC-2026-02'}) async {
  await tester.enterText(find.byType(TextField), examen);
  await _tocar(tester, find.text('Seleccionar archivos'));
  await _tocar(tester, find.text('Subir al sistema'));
}

void _fijarTamano(WidgetTester tester, Size tamano) {
  tester.view.physicalSize = tamano;
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
}

void main() {
  testWidgets('El botón de subir sigue deshabilitado sin examen o sin archivos', (tester) async {
    await tester.pumpWidget(_pantallaCarga());
    await tester.pumpAndSettle();

    expect(_boton(tester, 'Subir al sistema').enabled, isFalse, reason: 'sin examen ni archivos');

    await tester.enterText(find.byType(TextField), 'CALC-2026-02');
    await tester.pumpAndSettle();
    expect(_boton(tester, 'Subir al sistema').enabled, isFalse,
        reason: 'hay examen pero no hay archivos');

    await _tocar(tester, find.text('Seleccionar archivos'));
    expect(_boton(tester, 'Subir al sistema').enabled, isTrue, reason: 'ya hay examen y archivos');

    await tester.enterText(find.byType(TextField), '   ');
    await tester.pumpAndSettle();
    expect(_boton(tester, 'Subir al sistema').enabled, isFalse,
        reason: 'un examen en blanco no cuenta como examen');
  });

  testWidgets('Las instrucciones para tomar las fotos están antes del examen y de los archivos',
      (tester) async {
    await tester.pumpWidget(_pantallaCarga());
    await tester.pumpAndSettle();

    final instrucciones = tester.getTopLeft(find.text('Cómo tomar las fotos'));
    expect(instrucciones.dy, lessThan(tester.getTopLeft(find.text('Examen').first).dy));
    expect(find.text('Con luz de día, sin flash ni luz directa encima'), findsOneWidget);
    expect(find.textContaining('PDF'), findsNothing);
  });

  testWidgets('Una foto con poca resolución se avisa antes de subir, sin impedirlo', (tester) async {
    await tester.pumpWidget(_pantallaCarga(seleccion: [
      ArchivoSeleccionado(nombre: 'whatsapp.jpg', contenido: Uint8List(3), ladoMayorPx: 1600),
      ArchivoSeleccionado(nombre: 'buena.jpg', contenido: Uint8List(3), ladoMayorPx: 3200),
    ]));
    await tester.enterText(find.byType(TextField), 'CALC-2026-02');
    await _tocar(tester, find.text('Seleccionar archivos'));

    expect(find.text('Poca resolución: puede quedar ilegible'), findsOneWidget);
    expect(find.text('Una foto tiene poca resolución'), findsOneWidget);
    expect(_boton(tester, 'Subir al sistema').enabled, isTrue);
  });

  testWidgets('Después de subir, cada hoja muestra su nota a medida que se lee', (tester) async {
    _fijarTamano(tester, const Size(1280, 2200));
    final hojas = [_archivo('ana.jpg'), _archivo('beto.jpg'), _archivo('borrosa.jpg')];
    var consultas = 0;
    final leidas = <String, ResultadoDeHoja>{};
    await tester.pumpWidget(_pantallaCarga(
      seleccion: hojas,
      subir: (examenId, archivos) async => ResultadoCarga(
        totalProcesados: 3,
        aceptadas: [
          for (final a in archivos)
            HojaAceptada(nombreArchivo: a.nombre, trabajoId: 't-${a.nombre}', hojaId: 'h-${a.nombre}'),
        ],
        rechazados: const [],
      ),
      consultar: (examenId) async {
        consultas++;
        return ResultadosDelExamen(examenId: examenId, porHoja: Map.of(leidas));
      },
    ));
    await _subirLote(tester);

    expect(find.text('Leídas 0 de 3'), findsOneWidget);
    expect(find.text('Recibida'), findsNWidgets(3));

    leidas['h-ana.jpg'] = const ResultadoDeHoja(
      hojaId: 'h-ana.jpg', estado: EstadoDeLectura.calificada, notaEnDecimas: 49, codigoCompleto: true);
    leidas['h-beto.jpg'] = const ResultadoDeHoja(
      hojaId: 'h-beto.jpg', estado: EstadoDeLectura.enRevision, notaEnDecimas: 42, provisional: true,
      preguntasPorRevisar: [7, 12], codigoCompleto: true);
    await tester.pump(const Duration(seconds: 3));
    await tester.pumpAndSettle();

    expect(find.text('Leídas 2 de 3'), findsOneWidget);
    expect(find.text('Calificada · 4,9'), findsOneWidget);
    expect(find.text('En revisión · 4,2'), findsOneWidget);
    expect(find.textContaining('Esperan su revisión las preguntas 7 y 12.'), findsOneWidget);

    leidas['h-borrosa.jpg'] = const ResultadoDeHoja(
      hojaId: 'h-borrosa.jpg', estado: EstadoDeLectura.ilegible, motivo: 'imagen_ilegible');
    await tester.pump(const Duration(seconds: 3));
    await tester.pumpAndSettle();

    expect(find.text('Lectura terminada: 3 hojas leídas'), findsOneWidget);
    expect(find.text('Ilegible'), findsOneWidget);
    expect(find.textContaining('la foto está borrosa, oscura o tiene poca resolución'),
        findsOneWidget);

    // Con todas leídas deja de preguntar.
    final hechas = consultas;
    await tester.pump(const Duration(seconds: 10));
    expect(consultas, hechas);
  });

  testWidgets('Una hoja en revisión ofrece revisarla, y al guardar la nota se refresca',
      (tester) async {
    _fijarTamano(tester, const Size(1280, 2200));
    final pedidos = <String>[];
    final guardadas = ValueNotifier(0);
    addTearDown(guardadas.dispose);
    var revisada = false;
    await tester.pumpWidget(_pantallaCarga(
      seleccion: [_archivo('ana.jpg')],
      subir: (examenId, archivos) async => const ResultadoCarga(
        totalProcesados: 1,
        aceptadas: [HojaAceptada(nombreArchivo: 'ana.jpg', trabajoId: 't-1', hojaId: 'h-1')],
        rechazados: [],
      ),
      consultar: (examenId) async => ResultadosDelExamen(examenId: examenId, porHoja: {
        'h-1': revisada
            ? const ResultadoDeHoja(
                hojaId: 'h-1', estado: EstadoDeLectura.calificada, notaEnDecimas: 50,
                codigoCompleto: true, revisada: true)
            : const ResultadoDeHoja(
                hojaId: 'h-1', estado: EstadoDeLectura.enRevision, notaEnDecimas: 49,
                provisional: true, preguntasPorRevisar: [7], codigoCompleto: true),
      }),
      alRevisar: pedidos.add,
      revisionesGuardadas: guardadas,
    ));
    await _subirLote(tester);
    await tester.pump(const Duration(seconds: 3));
    await tester.pumpAndSettle();

    await _tocar(tester, find.text('Revisar'));
    expect(pedidos, ['CALC-2026-02']);

    // La revisión se guardó en la otra pantalla: el reporte vuelve a pedir las notas.
    revisada = true;
    guardadas.value++;
    await tester.pumpAndSettle();

    expect(find.text('Calificada · 5,0'), findsOneWidget);
    expect(find.textContaining('Incluye su revisión.'), findsOneWidget);
    expect(find.text('Revisar'), findsNothing);
  });

  testWidgets('Mientras prepara las fotos muestra cuántas van y no deja subir', (tester) async {
    // Con 200 fotos, pasarlas a gris y reducirlas tarda: sin el avance parecería colgado, y
    // subir a medias dejaría fuera las que faltan.
    final listas = Completer<List<ArchivoSeleccionado>>();
    await tester.pumpWidget(_pantallaCarga(
      seleccionar: ({alAvanzar}) {
        alAvanzar?.call(1, 3);
        return listas.future;
      },
    ));
    await tester.enterText(find.byType(TextField), 'CALC-2026-02');
    await _tocar(tester, find.text('Seleccionar archivos'));

    expect(find.text('Preparando las fotos: 1 de 3…'), findsOneWidget);
    expect(_boton(tester, 'Subir al sistema').enabled, isFalse);

    listas.complete([_hoja]);
    await tester.pumpAndSettle();

    expect(find.text('Preparando las fotos: 1 de 3…'), findsNothing);
    expect(_boton(tester, 'Subir al sistema').enabled, isTrue);
  });

  testWidgets('El reporte muestra las aceptadas y las rechazadas con su motivo', (tester) async {
    await tester.pumpWidget(_pantallaCarga(
      seleccion: [_hoja, _archivo('apuntes.txt')],
      subir: (examenId, archivos) async => const ResultadoCarga(
        totalProcesados: 2,
        aceptadas: [
          HojaAceptada(
            nombreArchivo: 'hoja1.jpg',
            trabajoId: '2eede6b8-dd9f-4db6-9c1a-5b7e0f3a1c22',
          ),
        ],
        rechazados: [
          ArchivoRechazado(
            nombreArchivo: 'apuntes.txt',
            motivo: 'Extensión no admitida (.txt). Se aceptan JPG, PDF, PNG.',
          ),
        ],
      ),
    ));
    await tester.pumpAndSettle();
    await _subirLote(tester);

    // El total es la parte visible de EC-07: el docente puede contar lo que subió contra lo que
    // el sistema dice haber procesado.
    expect(find.text('2 archivos subidos'), findsOneWidget);
    expect(find.text('1 recibida'), findsOneWidget);
    expect(find.text('1 rechazada'), findsOneWidget);

    expect(find.text('hoja1.jpg'), findsOneWidget);
    expect(find.text('Recibida'), findsOneWidget);
    expect(find.text('Trabajo 2eede6b8-dd9f-4db6-9c1a-5b7e0f3a1c22'), findsOneWidget);

    expect(find.text('apuntes.txt'), findsOneWidget);
    expect(find.text('Rechazada'), findsOneWidget);
    expect(find.text('Extensión no admitida (.txt). Se aceptan JPG, PDF, PNG.'), findsOneWidget);

    expect(find.text('El reporte no cuadra con el lote'), findsNothing);
  });

  testWidgets('Una falla de red se muestra como aviso, no como rechazo', (tester) async {
    await tester.pumpWidget(_pantallaCarga(
      subir: (examenId, archivos) async =>
          throw const ExcepcionDeCarga('No se pudo contactar con el servidor.'),
    ));
    await tester.pumpAndSettle();
    await _subirLote(tester);

    expect(find.text('No se pudo contactar con el servidor.'), findsOneWidget);
    expect(find.text('No se pudo completar la carga'), findsOneWidget);
    expect(find.textContaining('subido'), findsNothing);
    expect(find.text('Rechazada'), findsNothing);

    // El lote no entró, así que la selección se conserva para reintentar.
    expect(find.text('1 archivo seleccionado'), findsOneWidget);
    expect(_boton(tester, 'Subir al sistema').enabled, isTrue);
    expect(find.textContaining('para que pueda reintentar'), findsOneWidget);
  });

  testWidgets('Si algunas hojas pudieron entrar, el aviso no invita a reintentar sin más',
      (tester) async {
    // Antes, el texto de la excepción decía «algunas hojas pudieron entrar» y el detalle
    // de abajo, «siguen seleccionados para que pueda reintentar».
    await tester.pumpWidget(_pantallaCarga(
      subir: (examenId, archivos) async => throw const ExcepcionDeCarga(
        'La API respondió 502. Algunas hojas pudieron entrar.',
        pudieronEntrar: true,
      ),
    ));
    await tester.pumpAndSettle();
    await _subirLote(tester);

    expect(find.textContaining('podría quedar repetida'), findsOneWidget);
    expect(find.textContaining('para que pueda reintentar'), findsNothing);
  });

  testWidgets('Las hojas recibidas salen de la selección para no volver a subirlas',
      (tester) async {
    final enviados = <List<String>>[];
    await tester.pumpWidget(_pantallaCarga(
      seleccion: [_archivo('hoja1.jpg'), _archivo('hoja2.png', 2048)],
      subir: (examenId, archivos) async {
        enviados.add([for (final a in archivos) a.nombre]);
        return _todoEncolado(archivos);
      },
    ));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), 'CALC-2026-02');
    await _tocar(tester, find.text('Seleccionar archivos'));
    expect(find.text('2 archivos seleccionados'), findsOneWidget);
    expect(find.text('3 KB en total'), findsOneWidget);

    await _tocar(tester, find.text('Subir al sistema'));

    expect(enviados, [
      ['hoja1.jpg', 'hoja2.png'],
    ]);
    expect(find.text('2 archivos subidos'), findsOneWidget);
    expect(find.text('2 archivos seleccionados'), findsNothing);
    expect(find.byTooltip('Quitar hoja1.jpg de la selección'), findsNothing);
    expect(_boton(tester, 'Subir al sistema').enabled, isFalse);
  });

  testWidgets('Sin conexión el botón se deshabilita y lo dice', (tester) async {
    final estado = ValueNotifier(EstadoApi.sinConexion);
    addTearDown(estado.dispose);
    await tester.pumpWidget(_pantallaCarga(estadoApi: estado));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), 'CALC-2026-02');
    await _tocar(tester, find.text('Seleccionar archivos'));

    expect(_boton(tester, 'Subir al sistema').enabled, isFalse);
    expect(find.text('Sin conexión con el servidor'), findsOneWidget);
    expect(find.textContaining('Podrá subirlos cuando vuelva la conexión'), findsOneWidget);

    // Cuando el marco vuelve a ver la API, la pantalla se habilita sola y conserva la selección.
    estado.value = EstadoApi.conectada;
    await tester.pumpAndSettle();
    expect(_boton(tester, 'Subir al sistema').enabled, isTrue);
    expect(find.text('Sin conexión con el servidor'), findsNothing);
    expect(find.text('1 archivo seleccionado'), findsOneWidget);
  });

  testWidgets('Mientras sube muestra el progreso y no deja subir otra vez', (tester) async {
    final respuesta = Completer<ResultadoCarga>();
    await tester.pumpWidget(_pantallaCarga(subir: (examenId, archivos) => respuesta.future));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), 'CALC-2026-02');
    await _tocar(tester, find.text('Seleccionar archivos'));
    await tester.ensureVisible(find.text('Subir al sistema'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Subir al sistema'));
    // Sin `pumpAndSettle`: la barra de progreso indeterminada no se asienta nunca.
    await tester.pump();

    expect(find.text('Subiendo…'), findsOneWidget);
    expect(find.byType(LinearProgressIndicator), findsOneWidget);
    expect(_boton(tester, 'Subiendo…').enabled, isFalse);
    expect(_boton(tester, 'Seleccionar archivos').enabled, isFalse);

    respuesta.complete(_todoEncolado([_hoja]));
    await tester.pumpAndSettle();

    expect(find.byType(LinearProgressIndicator), findsNothing);
    expect(find.text('1 archivo subido'), findsOneWidget);
  });

  testWidgets('Una hoja pendiente de encolar se muestra como pendiente, no como rechazada',
      (tester) async {
    var consultas = 0;
    await tester.pumpWidget(_pantallaCarga(
      subir: (examenId, archivos) async => const ResultadoCarga(
        totalProcesados: 1,
        aceptadas: [
          HojaAceptada(
            nombreArchivo: 'hoja1.jpg',
            trabajoId: '4f1ba782-99ca-41a3-8d2e-6c0b9a7f5e11',
            hojaId: 'h-1',
            estado: EstadoHoja.pendienteDeEncolar,
          ),
        ],
        rechazados: [],
      ),
      consultar: (examenId) async {
        consultas++;
        return ResultadosDelExamen(examenId: examenId, porHoja: const {});
      },
    ));
    await tester.pumpAndSettle();
    await _subirLote(tester);

    expect(find.text('En espera'), findsOneWidget);
    expect(find.textContaining('No hace falta volver a subirla'), findsOneWidget);
    // Una hoja en espera no entra a la lectura: no se pregunta por ella ni se promete leerla.
    expect(find.textContaining('Leídas'), findsNothing);
    expect(consultas, 0);
    expect(find.text('1 recibida'), findsOneWidget);
    expect(find.text('0 rechazadas'), findsOneWidget);
    expect(find.text('Rechazada'), findsNothing);
    expect(find.text('Recibida'), findsNothing);
    expect(find.text('No se pudo completar la carga'), findsNothing);
  });

  testWidgets('Se puede quitar un archivo de la selección antes de subir', (tester) async {
    final enviados = <String>[];
    await tester.pumpWidget(_pantallaCarga(
      seleccion: [_archivo('hoja1.jpg'), _archivo('hoja2.jpg')],
      subir: (examenId, archivos) async {
        enviados.addAll([for (final a in archivos) a.nombre]);
        return _todoEncolado(archivos);
      },
    ));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), 'CALC-2026-02');
    await _tocar(tester, find.text('Seleccionar archivos'));
    expect(find.text('2 archivos seleccionados'), findsOneWidget);

    await _tocar(tester, find.byTooltip('Quitar hoja1.jpg de la selección'));
    expect(find.text('1 archivo seleccionado'), findsOneWidget);
    expect(find.text('hoja1.jpg'), findsNothing);
    expect(find.text('hoja2.jpg'), findsOneWidget);

    await _tocar(tester, find.text('Subir al sistema'));
    expect(enviados, ['hoja2.jpg']);
  });

  testWidgets('Elegir otra vez suma archivos y no repite los que ya estaban', (tester) async {
    var vez = 0;
    await tester.pumpWidget(_pantallaCarga(
      seleccionar: ({alAvanzar}) async => ++vez == 1
          ? [_archivo('hoja1.jpg')]
          : [_archivo('hoja1.jpg'), _archivo('hoja2.jpg')],
    ));
    await tester.pumpAndSettle();

    await _tocar(tester, find.text('Seleccionar archivos'));
    await _tocar(tester, find.text('Seleccionar archivos'));

    expect(find.text('2 archivos seleccionados'), findsOneWidget);
    expect(
      find.text('Un archivo ya estaba en la selección y no se agregó otra vez.'),
      findsOneWidget,
    );
  });

  testWidgets('Avisa si el reporte no da cuenta de todos los archivos enviados', (tester) async {
    await tester.pumpWidget(_pantallaCarga(
      seleccion: [_archivo('hoja1.jpg'), _archivo('hoja2.jpg')],
      subir: (examenId, archivos) async => const ResultadoCarga(
        totalProcesados: 1,
        aceptadas: [HojaAceptada(nombreArchivo: 'hoja1.jpg', trabajoId: 'abc')],
        rechazados: [],
      ),
    ));
    await tester.pumpAndSettle();
    await _subirLote(tester);

    expect(find.text('El reporte no cuadra con el lote'), findsOneWidget);
    expect(find.text('Se enviaron 2 archivos, pero el reporte detalla 1.'), findsOneWidget);
  });

  testWidgets('Una respuesta ilegible se avisa sin dar el lote por perdido ni por recibido',
      (tester) async {
    await tester.pumpWidget(_pantallaCarga(
      subir: (examenId, archivos) async => throw const FormatException('cuerpo inesperado'),
    ));
    await tester.pumpAndSettle();
    await _subirLote(tester);

    expect(find.text('Sin confirmación del servidor'), findsOneWidget);
    expect(find.textContaining('subido'), findsNothing);
    expect(find.text('1 archivo seleccionado'), findsOneWidget);
  });

  group('Con la lista de exámenes con clave', () {
    const prototipo = ExamenConClave(examenId: 'PROTOTIPO-R05', habilitada: true);
    const quiz = ExamenConClave(examenId: 'QUIZ-3', habilitada: false);

    Future<void> elegir(WidgetTester tester, String examen) async {
      await _tocar(tester, find.byType(DropdownMenu<String>));
      await _tocar(tester, find.text(examen).last);
    }

    testWidgets('El examen se elige de la lista y las hojas van a ese examen', (tester) async {
      final destinos = <String>[];
      await tester.pumpWidget(_pantallaCarga(
        listar: () async => [prototipo, quiz],
        subir: (examenId, archivos) async {
          destinos.add(examenId);
          return _todoEncolado(archivos);
        },
      ));
      await tester.pumpAndSettle();

      await elegir(tester, 'PROTOTIPO-R05');
      await _tocar(tester, find.text('Seleccionar archivos'));
      expect(find.text('Se subirá 1 archivo a PROTOTIPO-R05.'), findsOneWidget);
      await _tocar(tester, find.text('Subir al sistema'));

      expect(destinos, ['PROTOTIPO-R05']);
    });

    testWidgets('Un nombre que no está en la lista se marca y no deja subir', (tester) async {
      await tester.pumpWidget(_pantallaCarga(listar: () async => [prototipo, quiz]));
      await tester.pumpAndSettle();
      await _tocar(tester, find.text('Seleccionar archivos'));

      await tester.enterText(find.byType(TextField), 'PROTOTIPO-R50');
      await tester.pumpAndSettle();
      expect(find.text('No hay un examen con ese nombre.'), findsOneWidget);
      expect(_boton(tester, 'Subir al sistema').enabled, isFalse);

      // Escrito en minúsculas sí es el examen, y se sube con su nombre exacto.
      await tester.enterText(find.byType(TextField), 'prototipo-r05');
      await tester.pumpAndSettle();
      expect(find.text('No hay un examen con ese nombre.'), findsNothing);
      expect(find.text('Se subirá 1 archivo a PROTOTIPO-R05.'), findsOneWidget);
      expect(_boton(tester, 'Subir al sistema').enabled, isTrue);
    });

    testWidgets('Un examen con la clave sin habilitar se avisa al elegirlo', (tester) async {
      await tester.pumpWidget(_pantallaCarga(listar: () async => [prototipo, quiz]));
      await tester.pumpAndSettle();

      await _tocar(tester, find.byType(DropdownMenu<String>));
      expect(find.text('Sin habilitar'), findsWidgets);
      await _tocar(tester, find.text('QUIZ-3').last);

      expect(find.text('Su clave no está habilitada: las hojas quedarán sin nota.'), findsOneWidget);
    });

    testWidgets('En el teléfono la lista se elige sin teclado y sin desbordes', (tester) async {
      _fijarTamano(tester, const Size(390, 900));
      await tester.pumpWidget(_pantallaCarga(listar: () async => [prototipo, quiz]));
      await tester.pumpAndSettle();

      expect(tester.widget<TextField>(find.byType(TextField)).readOnly, isTrue);
      await elegir(tester, 'QUIZ-3');
      await _tocar(tester, find.text('Seleccionar archivos'));

      expect(find.text('Se subirá 1 archivo a QUIZ-3.'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('Sin exámenes con clave lo dice y no deja subir', (tester) async {
      await tester.pumpWidget(_pantallaCarga(listar: () async => const []));
      await tester.pumpAndSettle();
      await _tocar(tester, find.text('Seleccionar archivos'));

      expect(find.text('Todavía no hay exámenes con clave.'), findsOneWidget);
      expect(_boton(tester, 'Subir al sistema').enabled, isFalse);
    });

    testWidgets('Si la lista no carga, el examen se escribe y se puede volver a pedir',
        (tester) async {
      var pedidos = 0;
      await tester.pumpWidget(_pantallaCarga(listar: () async {
        pedidos++;
        throw Exception('sin red');
      }));
      await tester.pumpAndSettle();

      expect(find.text('No se pudo cargar la lista. Escriba el nombre exacto.'), findsOneWidget);
      await tester.enterText(find.byType(TextField), 'CALC-2026-02');
      await _tocar(tester, find.text('Seleccionar archivos'));
      expect(_boton(tester, 'Subir al sistema').enabled, isTrue);

      await _tocar(tester, find.byTooltip('Volver a cargar la lista'));
      expect(pedidos, 2);
    });
  });

  for (final ancho in [390.0, 1280.0]) {
    testWidgets('No se desborda a ${ancho.toInt()} px con selección, reporte y avisos',
        (tester) async {
      _fijarTamano(tester, Size(ancho, 900));
      final estado = ValueNotifier(EstadoApi.conectada);
      addTearDown(estado.dispose);
      const nombreLargo =
          'escaneo_parcial_2_calculo_diferencial_grupo_04_estudiante_1092837_pagina_1.png';

      await tester.pumpWidget(_pantallaCarga(
        estadoApi: estado,
        seleccion: [
          _archivo(nombreLargo, 2400000),
          _archivo('hoja_2.pdf', 850 * 1024),
          _archivo('apuntes.txt'),
        ],
        subir: (examenId, archivos) async => const ResultadoCarga(
          totalProcesados: 3,
          aceptadas: [
            HojaAceptada(
              nombreArchivo: nombreLargo,
              trabajoId: '2eede6b8-dd9f-4db6-9c1a-5b7e0f3a1c22',
            ),
            HojaAceptada(
              nombreArchivo: 'hoja_2.pdf',
              trabajoId: '4f1ba782-99ca-41a3-8d2e-6c0b9a7f5e11',
              estado: EstadoHoja.pendienteDeEncolar,
            ),
          ],
          rechazados: [
            ArchivoRechazado(
              nombreArchivo: 'apuntes.txt',
              motivo: 'Extensión no admitida (.txt). Se aceptan JPG, PDF, PNG.',
            ),
          ],
        ),
      ));
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull, reason: 'estado inicial');

      await _subirLote(tester, examen: 'CALC-2026-02-PARCIAL-SEGUNDO-CORTE-GRUPO-04');
      expect(find.text('3 archivos subidos'), findsOneWidget);

      // Una segunda selección convive con el reporte anterior, y la API se cae: todo a la vez.
      await _tocar(tester, find.text('Seleccionar archivos'));
      estado.value = EstadoApi.sinConexion;
      await tester.pumpAndSettle();

      expect(find.text('Sin conexión con el servidor'), findsOneWidget);
      expect(find.text('3 archivos seleccionados'), findsOneWidget);
      expect(tester.takeException(), isNull, reason: 'con todo a la vista');
    });
  }
}
