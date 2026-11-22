import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/features/carga/data/servicio_examenes.dart';
import 'package:frontend/features/carga/data/servicio_resultados.dart' show ExcepcionDeConsulta;
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

/// La lectura de `GET /examenes`, contra un `MockClient`.
void main() {
  test('Cada examen llega con su identificador y si su clave está habilitada', () async {
    final cliente = MockClient((peticion) async {
      expect(peticion.url.path, '/examenes');
      return http.Response.bytes(
        utf8.encode(jsonEncode({
          'examenes': [
            {'examen_id': 'Cálculo 1', 'habilitada': true},
            {'examen_id': 'QUIZ-3', 'habilitada': false},
          ],
        })),
        200,
      );
    });

    final examenes = await listarExamenes(cliente: cliente);

    expect([for (final e in examenes) (e.examenId, e.habilitada)], [
      ('Cálculo 1', true),
      ('QUIZ-3', false),
    ]);
  });

  test('Una respuesta que no es 200 o no se puede leer es una ExcepcionDeConsulta', () async {
    for (final respuesta in [http.Response('', 500), http.Response('no es json', 200)]) {
      await expectLater(
        listarExamenes(cliente: MockClient((_) async => respuesta)),
        throwsA(isA<ExcepcionDeConsulta>()),
      );
    }
  });

  test('Sin red también es una ExcepcionDeConsulta', () async {
    await expectLater(
      listarExamenes(cliente: MockClient((_) async => throw http.ClientException('sin red'))),
      throwsA(isA<ExcepcionDeConsulta>()),
    );
  });
}
