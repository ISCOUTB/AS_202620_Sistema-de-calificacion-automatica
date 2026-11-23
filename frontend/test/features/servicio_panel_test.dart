import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/features/carga/data/servicio_examenes.dart';
import 'package:frontend/features/carga/data/servicio_resultados.dart' show ExcepcionDeConsulta;
import 'package:frontend/features/panel/data/servicio_panel.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

http.Response _json(Object cuerpo, int estado) =>
    http.Response.bytes(utf8.encode(jsonEncode(cuerpo)), estado);

/// Los servicios de ADR-0028 contra un `MockClient`: crear un examen con su nombre, la lista con
/// los nombres y las cifras del panel.
void main() {
  group('crearExamen', () {
    test('Manda el nombre y devuelve el identificador que acuñó la API', () async {
      final cliente = MockClient((peticion) async {
        expect((peticion.method, peticion.url.path), ('POST', '/examenes'));
        expect(jsonDecode(peticion.body), {'nombre': 'Parcial 1'});
        return _json({'examen_id': '000001', 'nombre': 'Parcial 1'}, 201);
      });

      final creado = await crearExamen('Parcial 1', cliente: cliente);

      expect((creado.examenId, creado.nombre, creado.creado), ('000001', 'Parcial 1', true));
    });

    test('Con 200 es el examen que el docente ya tenía con ese nombre', () async {
      final cliente = MockClient(
        (_) async => _json({'examen_id': '000004', 'nombre': 'Parcial 1'}, 200),
      );

      expect((await crearExamen('parcial 1', cliente: cliente)).creado, isFalse);
    });

    test('El motivo de un 422 llega al docente', () async {
      final cliente = MockClient(
        (_) async => _json({'detail': 'Escriba el nombre del examen.'}, 422),
      );

      await expectLater(
        crearExamen(' ', cliente: cliente),
        throwsA(
          isA<ExcepcionDeConsulta>().having((e) => e.mensaje, 'mensaje', contains('Escriba')),
        ),
      );
    });
  });

  test('La lista trae el nombre de cada examen, y sin nombre usa el identificador', () async {
    final cliente = MockClient(
      (_) async => _json({
        'examenes': [
          {'examen_id': '000001', 'nombre': 'Parcial 1', 'habilitada': true},
          {'examen_id': 'QUIZ-3', 'habilitada': false},
        ],
      }, 200),
    );

    final examenes = await listarExamenes(cliente: cliente);

    expect([for (final e in examenes) (e.examenId, e.nombre, e.etiqueta)], [
      ('000001', 'Parcial 1', 'Parcial 1 · 000001'),
      ('QUIZ-3', 'QUIZ-3', 'QUIZ-3'),
    ]);
  });

  test('Los nombres se comparan sin espacios de más ni mayúsculas', () {
    expect(claveDelNombre('  Parcial   1 '), claveDelNombre('parcial 1'));
    expect(claveDelNombre('Parcial 1'), isNot(claveDelNombre('Parcial 2')));
  });

  group('consultarPanel', () {
    test('Lee las cifras del examen en la escala de 0 a 5', () async {
      final cliente = MockClient((peticion) async {
        expect(peticion.url.path, '/examenes/000001/panel');
        return _json({
          'examen_id': '000001',
          'nombre': 'Parcial 1',
          'resumen': {
            'hojas_recibidas': 2,
            'hojas_leidas': 2,
            'hojas_con_nota': 2,
            'hojas_sin_nota': 0,
            'hojas_ilegibles': 0,
            'hojas_en_revision': 0,
            'preguntas_por_revisar': 0,
            'aprobados': 2,
            'promedio_en_decimas': 45.0,
            'desviacion_en_decimas': 5.0,
            'nota_aprobatoria_en_decimas': 30,
          },
          'marcas': {
            'correctas': 36,
            'incorrectas': 4,
            'tenues_o_dudosas': 0,
            'dobles': 0,
            'en_blanco': 0,
            'pendientes': 0,
          },
          'notas_en_decimas': [40, 50],
          'preguntas': [
            {
              'numero': 1,
              'correcta': 'A',
              'aciertos': 1,
              'hojas': 2,
              'marcadas': {'A': 1, 'B': 1, 'C': 0, 'D': 0},
              'en_blanco': 0,
              'dobles': 0,
              'dudosas': 0,
            },
          ],
        }, 200);
      });

      final panel = await consultarPanel('000001', cliente: cliente);

      expect(panel.notas, [4.0, 5.0]);
      expect(panel.resumen.promedio, 4.5);
      expect(panel.resumen.desviacion, 0.5);
      expect(panel.marcas.total, 40);
      expect(panel.preguntas.single.porcentajeAciertos, 50);
    });

    test('Un 404 dice que el examen no es del docente', () async {
      await expectLater(
        consultarPanel('000009', cliente: MockClient((_) async => http.Response('', 404))),
        throwsA(isA<ExcepcionDeConsulta>()
            .having((e) => e.mensaje, 'mensaje', 'Ese examen no existe en su cuenta.')),
      );
    });

    test('Sin red, un error del servidor o un cuerpo ilegible son una ExcepcionDeConsulta',
        () async {
      for (final cliente in [
        MockClient((_) async => throw http.ClientException('sin red')),
        MockClient((_) async => http.Response('', 500)),
        MockClient((_) async => http.Response('{"examen_id": 1}', 200)),
      ]) {
        await expectLater(
          consultarPanel('000001', cliente: cliente),
          throwsA(isA<ExcepcionDeConsulta>()),
        );
      }
    });
  });
}
