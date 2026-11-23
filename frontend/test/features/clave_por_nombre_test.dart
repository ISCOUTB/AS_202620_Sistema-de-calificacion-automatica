import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/common/tema/tema.dart';
import 'package:frontend/features/carga/data/servicio_examenes.dart';
import 'package:frontend/features/pauta/data/servicio_clave.dart';
import 'package:frontend/features/pauta/views/widgets/tarjeta_clave.dart';

/// Una API de exámenes y claves en memoria, con los identificadores que acuña el servidor
/// (ADR-0028).
class _Api {
  _Api({this.examenes = const [], Map<String, ClaveDelExamen>? claves, this.yaExiste})
      : claves = {...?claves};

  final List<ExamenConClave> examenes;
  final Map<String, ClaveDelExamen> claves;

  /// Un examen que el servidor ya tiene con ese nombre aunque la lista no lo traiga.
  final ExamenCreado? yaExiste;

  final creados = <String>[];
  final consultados = <String>[];
  final guardados = <(String, List<String>)>[];
  final habilitados = <String>[];

  Future<ExamenCreado> crear(String nombre) async {
    creados.add(nombre);
    return yaExiste ?? ExamenCreado(examenId: '000007', nombre: nombre, creado: true);
  }

  Future<ClaveDelExamen?> consultar(String examenId) async {
    consultados.add(examenId);
    return claves[examenId];
  }

  Future<ClaveDelExamen> guardar(String examenId, List<String> respuestas) async {
    guardados.add((examenId, respuestas));
    return claves[examenId] =
        ClaveDelExamen(examenId: examenId, respuestas: respuestas, sePuedeCambiar: true);
  }

  Future<ClaveDelExamen> habilitar(String examenId) async {
    habilitados.add(examenId);
    return claves[examenId] = ClaveDelExamen(
      examenId: examenId,
      respuestas: claves[examenId]!.respuestas,
      sePuedeCambiar: true,
      habilitadaPor: 'ana@utb.edu.co',
      habilitadaEn: DateTime.utc(2026, 11, 23, 15),
    );
  }
}

Future<void> _montar(WidgetTester tester, _Api api) async {
  tester.view.physicalSize = const Size(1280, 2400);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(MaterialApp(
    theme: construirTema(),
    home: Scaffold(
      body: SingleChildScrollView(
        child: TarjetaClaveDelExamen(
          listarExamenes: () async => api.examenes,
          consultarClave: api.consultar,
          guardarClave: api.guardar,
          habilitarClave: api.habilitar,
          crearExamen: api.crear,
        ),
      ),
    ),
  ));
  await tester.pumpAndSettle();
}

Future<void> _escribirNombre(WidgetTester tester, String nombre) async {
  await tester.enterText(find.widgetWithText(TextField, 'Nombre del examen'), nombre);
  await tester.pump(const Duration(milliseconds: 500));
  await tester.pumpAndSettle();
}

Future<void> _llenar(WidgetTester tester, String respuestas) async {
  await tester.enterText(find.widgetWithText(TextField, 'Pegar las respuestas'), respuestas);
  await tester.tap(find.text('Llenar'));
  await tester.pumpAndSettle();
  await tester.tap(find.text('Llenar la cuadrícula'));
  await tester.pumpAndSettle();
}

Future<void> _tocar(WidgetTester tester, String texto) async {
  final boton = find.text(texto);
  await tester.ensureVisible(boton);
  await tester.pumpAndSettle();
  await tester.tap(boton);
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('Un nombre nuevo no busca clave: el examen se crea al guardarla', (tester) async {
    final api = _Api();
    await _montar(tester, api);

    await _escribirNombre(tester, 'Parcial 1');

    expect(api.consultados, isEmpty);
    expect(find.text('Examen nuevo: se crea al guardar la clave.'), findsOneWidget);

    await _llenar(tester, 'ABCD');
    await _tocar(tester, 'Guardar clave');

    expect(api.creados, ['Parcial 1']);
    expect(api.guardados, hasLength(1));
    expect(api.guardados.single.$1, '000007');
    expect(api.guardados.single.$2, ['A', 'B', 'C', 'D']);
    expect(find.textContaining('examen 000007'), findsOneWidget, reason: 'el aviso');
    expect(find.text('Examen 000007'), findsOneWidget, reason: 'la ayuda del campo');
    expect(find.text('Guardada, sin habilitar.'), findsOneWidget);
  });

  testWidgets('Habilitar usa el identificador, no el nombre', (tester) async {
    final api = _Api();
    await _montar(tester, api);
    await _escribirNombre(tester, 'Parcial 1');
    await _llenar(tester, 'AB');
    await _tocar(tester, 'Guardar clave');

    await _tocar(tester, 'Habilitar');
    expect(find.text('¿Habilitar la clave de Parcial 1?'), findsOneWidget);
    await tester.tap(find.widgetWithText(FilledButton, 'Habilitar'));
    await tester.pumpAndSettle();

    expect(api.habilitados, ['000007']);
  });

  testWidgets('Un nombre que el docente ya tiene carga la clave de ese examen', (tester) async {
    final api = _Api(
      examenes: const [ExamenConClave(examenId: '000003', nombre: 'Quiz 2', habilitada: false)],
      claves: {
        '000003': const ClaveDelExamen(
          examenId: '000003',
          respuestas: ['C', 'D'],
          sePuedeCambiar: true,
        ),
      },
    );
    await _montar(tester, api);

    // Sin distinguir mayúsculas ni espacios de más.
    await _escribirNombre(tester, '  quiz   2');

    expect(api.consultados, ['000003']);
    expect(find.text('Guardada, sin habilitar.'), findsOneWidget);
    expect(find.text('Examen 000003'), findsOneWidget);
  });

  testWidgets('Los chips de «Con clave:» muestran el nombre del examen', (tester) async {
    final api = _Api(
      examenes: const [ExamenConClave(examenId: '000003', nombre: 'Quiz 2', habilitada: true)],
    );
    await _montar(tester, api);

    await tester.tap(find.widgetWithText(ActionChip, 'Quiz 2'));
    await tester.pump(const Duration(milliseconds: 500));
    await tester.pumpAndSettle();

    expect(api.consultados, ['000003']);
    expect(find.text('000003'), findsNothing);
  });

  testWidgets('Si el servidor ya tenía un examen con ese nombre, no pisa su clave sin mostrarla',
      (tester) async {
    final api = _Api(
      yaExiste: const ExamenCreado(examenId: '000002', nombre: 'Parcial 1', creado: false),
      claves: {
        '000002': const ClaveDelExamen(
          examenId: '000002',
          respuestas: ['D', 'D', 'D'],
          sePuedeCambiar: true,
        ),
      },
    );
    await _montar(tester, api);
    await _escribirNombre(tester, 'Parcial 1');
    await _llenar(tester, 'AB');

    await _tocar(tester, 'Guardar clave');

    expect(api.guardados, isEmpty);
    expect(api.consultados, ['000002']);
    expect(find.textContaining('Ya tenía un examen llamado «Parcial 1»'), findsOneWidget);
    final filas = tester
        .widgetList<SegmentedButton<String>>(find.byType(SegmentedButton<String>))
        .map((fila) => fila.selected)
        .toList();
    expect(filas, [{'D'}, {'D'}, {'D'}]);
  });

  testWidgets('Un nombre de más de 80 caracteres no se acepta', (tester) async {
    final api = _Api();
    await _montar(tester, api);

    await _escribirNombre(tester, 'x' * 81);

    expect(find.text('Hasta 80 caracteres.'), findsOneWidget);
    expect(find.text('Guardar clave'), findsNothing);
  });
}
