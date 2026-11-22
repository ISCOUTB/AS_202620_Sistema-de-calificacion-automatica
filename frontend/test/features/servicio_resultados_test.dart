import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/features/carga/data/servicio_resultados.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

/// La lectura de `GET /examenes/{examen_id}/resultados`, contra un `MockClient`.
void main() {
  test('Cada hoja queda por su hoja_id, con su estado, su nota y lo que espera al docente', () async {
    final cliente = MockClient((peticion) async {
      expect(peticion.url.pathSegments, ['examenes', 'P2#1', 'resultados']);
      return http.Response.bytes(
        utf8.encode(jsonEncode({
          'examen_id': 'P2#1',
          'hojas': [
            {
              'hoja_id': 'h-1', 'estado': 'en_revision', 'motivo': null, 'nota_en_decimas': 42,
              'provisional': true, 'preguntas_por_revisar': [7], 'codigo_completo': true,
              'momento': '2026-11-05T05:00:00Z',
            },
            {
              'hoja_id': 'h-2', 'estado': 'ilegible', 'motivo': 'hoja_no_reconocida',
              'nota_en_decimas': null, 'provisional': false, 'preguntas_por_revisar': [],
              'codigo_completo': null, 'momento': '2026-11-05T05:00:01Z',
            },
          ],
        })),
        200,
      );
    });

    final resultados = await consultarResultados('P2#1', cliente: cliente);

    final enRevision = resultados.porHoja['h-1']!;
    expect((enRevision.estado, enRevision.notaEnDecimas), (EstadoDeLectura.enRevision, 42));
    expect(enRevision.preguntasPorRevisar, [7]);
    expect(resultados.porHoja['h-2']!.estado, EstadoDeLectura.ilegible);
  });

  test('Una respuesta que no es 200 o no se puede leer es una ExcepcionDeConsulta', () async {
    for (final cliente in [
      MockClient((_) async => http.Response('', 503)),
      MockClient((_) async => http.Response('no es json', 200)),
    ]) {
      await expectLater(consultarResultados('P2', cliente: cliente),
          throwsA(isA<ExcepcionDeConsulta>()));
    }
  });

  test('La nota y los motivos se escriben como los lee el docente', () {
    expect(notaLegible(49), '4,9');
    expect(notaLegible(50), '5,0');
    expect(notaLegible(7), '0,7');
    expect(motivoLegible('marcas_de_registro_no_encontradas'),
        'no se ven las cuatro marcas negras de las esquinas');
    expect(motivoLegible('algo_nuevo'), 'algo_nuevo');
  });
}
