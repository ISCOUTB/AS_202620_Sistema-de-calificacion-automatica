import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:frontend/features/pauta/data/servicio_clave.dart';

const _json = {'Content-Type': 'application/json; charset=utf-8'};

http.Response _clave({String? por, bool cambiable = true}) => http.Response(
      jsonEncode({
        'examen_id': 'CALC-2026-03',
        'respuestas': ['A', 'B', 'C'],
        'habilitada_por': por,
        'habilitada_en': por == null ? null : '2026-11-22T15:00:00Z',
        'se_puede_cambiar': cambiable,
      }),
      200,
      headers: _json,
    );

void main() {
  group('Pedir, guardar y habilitar la clave', () {
    test('Una clave guardada llega con sus respuestas y su estado', () async {
      late http.Request pedida;
      final clave = await consultarClave(
        'CALC-2026-03',
        cliente: MockClient((peticion) async {
          pedida = peticion;
          return _clave(por: 'profe@utb.edu.co', cambiable: false);
        }),
      );

      expect(pedida.url.path, '/examenes/CALC-2026-03/clave');
      expect(clave!.respuestas, ['A', 'B', 'C']);
      expect(clave.habilitada, isTrue);
      expect(clave.habilitadaPor, 'profe@utb.edu.co');
      expect(clave.habilitadaEn, DateTime.utc(2026, 11, 22, 15));
      expect(clave.sePuedeCambiar, isFalse);
    });

    test('Un examen sin clave da nulo, no un error', () async {
      final clave = await consultarClave(
        'NUEVO',
        cliente: MockClient((_) async => http.Response('{"detail":"x"}', 404)),
      );

      expect(clave, isNull);
    });

    test('Guardar manda las respuestas en orden', () async {
      late http.Request enviada;
      final clave = await guardarClave(
        'CALC-2026-03',
        ['A', 'B', 'C'],
        cliente: MockClient((peticion) async {
          enviada = peticion;
          return _clave();
        }),
      );

      expect((enviada.method, enviada.url.path), ('PUT', '/examenes/CALC-2026-03/clave'));
      expect(jsonDecode(enviada.body), {'respuestas': ['A', 'B', 'C']});
      expect(clave.habilitada, isFalse);
    });

    test('Si la API no la guarda, el motivo es el suyo', () async {
      final cliente = MockClient((_) async => http.Response(
            jsonEncode({'detail': 'Ya hay hojas de CALC-2026-03 calificadas con esta clave: no se puede cambiar.'}),
            409,
            headers: _json,
          ));

      expect(
        () => guardarClave('CALC-2026-03', ['A'], cliente: cliente),
        throwsA(isA<ExcepcionDeClave>().having((e) => e.mensaje, 'mensaje', contains('no se puede cambiar'))),
      );
    });

    test('Habilitar la pide por POST y devuelve quién la habilitó', () async {
      late http.Request enviada;
      final clave = await habilitarClave(
        'CALC-2026-03',
        cliente: MockClient((peticion) async {
          enviada = peticion;
          return _clave(por: 'profe@utb.edu.co');
        }),
      );

      expect((enviada.method, enviada.url.path), ('POST', '/examenes/CALC-2026-03/clave/habilitacion'));
      expect(clave.habilitadaPor, 'profe@utb.edu.co');
    });
  });

  group('Las respuestas pegadas', () {
    test('Se leen las letras, con o sin números, comas y espacios', () {
      expect(respuestasDesdeTexto('abcd'), ['A', 'B', 'C', 'D']);
      expect(respuestasDesdeTexto('1. A, 2. B, 3. c\n4) d'), ['A', 'B', 'C', 'D']);
      expect(respuestasDesdeTexto('A B\tC'), ['A', 'B', 'C']);
    });

    test('Hasta 40, como la hoja', () {
      expect(respuestasDesdeTexto('A' * 40), hasLength(40));
      expect(
        () => respuestasDesdeTexto('A' * 41),
        throwsA(isA<FormatException>().having((e) => e.message, 'mensaje', 'Hay 41 respuestas; la hoja tiene 40.')),
      );
    });

    test('Una letra que no es opción de la hoja dice cuál y en qué pregunta', () {
      expect(
        () => respuestasDesdeTexto('ABE'),
        throwsA(isA<FormatException>().having((e) => e.message, 'mensaje', 'La pregunta 3 dice «E»: solo valen A, B, C y D.')),
      );
    });

    test('Sin letras no hay respuestas', () {
      expect(
        () => respuestasDesdeTexto(' 1, 2 '),
        throwsA(isA<FormatException>().having((e) => e.message, 'mensaje', 'No hay respuestas en el texto.')),
      );
    });
  });

  test('El identificador del examen sigue la regla de la API', () {
    expect(identificadorValido('CALC-2026-03'), isTrue);
    expect(identificadorValido('quiz_3'), isTrue);
    for (final malo in ['', ' X', 'con espacio', 'ñandú', '-X', 'x' * 65]) {
      expect(identificadorValido(malo), isFalse, reason: malo);
    }
  });
}
