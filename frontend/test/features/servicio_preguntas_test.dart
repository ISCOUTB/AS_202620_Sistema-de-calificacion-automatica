import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/common/api/servicio_salud.dart' show backendUrl;
import 'package:frontend/features/pauta/data/servicio_preguntas.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

/// Las preguntas que el docente agrega en Pauta (ADR-0030), contra un `MockClient`.

final _llave = 'b' * 64;

Map<String, Object> _pregunta() => {
      'llave': _llave,
      'enunciado': 'Calcule la derivada de f(x) = x·ln(x).',
      'respuesta_correcta': 'ln(x) + 1',
      'agregada_en': '2026-11-23T09:00:00Z',
    };

MockClient _responde(int codigo, Object cuerpo) => MockClient((_) async => http.Response.bytes(
      utf8.encode(jsonEncode(cuerpo)),
      codigo,
      headers: {'content-type': 'application/json'},
    ));

Future<ExcepcionPreguntas> _falla(Future<void> Function() pedir) async {
  try {
    await pedir();
  } on ExcepcionPreguntas catch (e) {
    return e;
  }
  fail('El servicio no lanzó ExcepcionPreguntas.');
}

void main() {
  test('La lista se pide con GET y trae cada pregunta con su llave', () async {
    late http.Request enviada;
    final cliente = MockClient((peticion) async {
      enviada = peticion;
      return http.Response.bytes(
        utf8.encode(jsonEncode([_pregunta()])),
        200,
        headers: {'content-type': 'application/json'},
      );
    });

    final preguntas = await listarPreguntas(cliente: cliente);

    expect(enviada.method, 'GET');
    expect(enviada.url.toString(), '$backendUrl/preguntas');
    expect(preguntas.single.llave, _llave);
    expect(preguntas.single.enunciado, 'Calcule la derivada de f(x) = x·ln(x).');
    expect(preguntas.single.respuestaCorrecta, 'ln(x) + 1');
    expect(preguntas.single.agregadaEn, DateTime.utc(2026, 11, 23, 9));
  });

  test('Agregar manda el enunciado y la respuesta con POST', () async {
    late http.Request enviada;
    final cliente = MockClient((peticion) async {
      enviada = peticion;
      return http.Response.bytes(
        utf8.encode(jsonEncode(_pregunta())),
        201,
        headers: {'content-type': 'application/json'},
      );
    });

    final pregunta = await agregarPregunta(
      'Calcule la derivada de f(x) = x·ln(x).',
      'ln(x) + 1',
      cliente: cliente,
    );

    expect(enviada.method, 'POST');
    expect(enviada.url.toString(), '$backendUrl/preguntas');
    expect(jsonDecode(enviada.body), {
      'enunciado': 'Calcule la derivada de f(x) = x·ln(x).',
      'respuesta_correcta': 'ln(x) + 1',
    });
    expect(pregunta.llave, _llave);
  });

  test('Un 409 al agregar trae el motivo de la API', () async {
    final e = await _falla(() => agregarPregunta(
          'x',
          'y',
          cliente: _responde(409, {'detail': 'Esa pregunta ya está en su lista.'}),
        ));
    expect(e.mensaje, 'Esa pregunta ya está en su lista.');
    expect(e.yaEstaba, isTrue);
  });

  test('Eliminar manda DELETE con la llave, y lo que ya no estaba no es un error', () async {
    late http.Request enviada;
    final cliente = MockClient((peticion) async {
      enviada = peticion;
      return http.Response('', 204);
    });

    await eliminarPregunta(_llave, cliente: cliente);

    expect(enviada.method, 'DELETE');
    expect(enviada.url.toString(), '$backendUrl/preguntas/$_llave');
    await eliminarPregunta(
      _llave,
      cliente: _responde(404, {'detail': 'Esa pregunta no está en su lista.'}),
    );
  });

  test('Si no hay red, lo dice', () async {
    final e = await _falla(() => listarPreguntas(
          cliente: MockClient((_) async => throw http.ClientException('sin red')),
        ));
    expect(e.mensaje, 'No se pudo contactar con el servidor. Revise su conexión y vuelva a intentarlo.');
  });

  test('La misma pregunta con otros espacios tiene la misma forma', () {
    expect(
      formaDeLaPregunta('  Calcule la derivada de  f(x) = x·ln(x). ', 'ln(x)  + 1'),
      formaDeLaPregunta('Calcule la derivada de f(x) = x·ln(x).', 'ln(x) + 1'),
    );
    expect(
      formaDeLaPregunta('Calcule la derivada de f(x) = x·ln(x).', 'ln(x) + 1'),
      isNot(formaDeLaPregunta('Calcule la derivada de f(x) = x·ln(x).', 'ln(x) + 2')),
    );
  });
}
