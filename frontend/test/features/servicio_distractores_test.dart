import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/common/api/servicio_salud.dart' show backendUrl;
import 'package:frontend/features/pauta/data/servicio_distractores.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

/// La traducción de cada respuesta de `POST /distractores` a lo que ve el docente, contra un
/// `MockClient`: sin red y sin backend.

const _solicitud = SolicitudDistractores(
  enunciado: 'Derive f(x) = x·sin(x)',
  respuestaCorrecta: 'sin(x) + x·cos(x)',
);

const _detalleMinuto = 'Se alcanzó el límite de 6 solicitudes por minuto al proveedor. Puede '
    'volver a pedirlo en 42 s.';

const _detalleDia = 'Se agotó el presupuesto diario de 150 solicitudes al proveedor. Habrá cupo '
    'en unos 5 h; mientras tanto, los distractores se pueden escribir a mano.';

/// Un cliente que responde siempre lo mismo, con el cuerpo en UTF-8 como lo manda FastAPI.
MockClient _responde(int codigo, Object cuerpo, {Map<String, String> cabeceras = const {}}) =>
    MockClient((_) async => http.Response.bytes(
          utf8.encode(jsonEncode(cuerpo)),
          codigo,
          headers: {'content-type': 'application/json', ...cabeceras},
        ));

/// La excepción que lanza el servicio con ese cliente. Falla si no lanza.
Future<ExcepcionDistractores> _falla(MockClient cliente) async {
  try {
    await proponerDistractores(_solicitud, cliente: cliente);
  } on ExcepcionDistractores catch (e) {
    return e;
  }
  fail('El servicio no lanzó ExcepcionDistractores.');
}

void main() {
  test('La solicitud va a /distractores con los tres campos y ninguno más', () async {
    late http.Request enviada;
    final cliente = MockClient((solicitud) async {
      enviada = solicitud;
      return http.Response('{"distractores": [], "descartados": []}', 200);
    });

    await proponerDistractores(_solicitud, cliente: cliente);

    expect(enviada.method, 'POST');
    expect(enviada.url.toString(), '$backendUrl/distractores');
    expect(jsonDecode(enviada.body), {
      'enunciado': 'Derive f(x) = x·sin(x)',
      'respuesta_correcta': 'sin(x) + x·cos(x)',
      'cantidad': 3,
    });
  });

  test('Un 200 se traduce a propuestas y descartes', () async {
    final resultado = await proponerDistractores(
      _solicitud,
      cliente: _responde(200, {
        'distractores': [
          {'expresion': 'cos(x)', 'error': 'Olvida la regla del producto.'},
        ],
        'descartados': [
          {'expresion': 'x·sin(x)', 'motivo': 'Repite la función sin derivar'},
        ],
      }),
    );

    expect(resultado.distractores.single.expresion, 'cos(x)');
    expect(resultado.descartados.single.motivo, 'Repite la función sin derivar');
  });

  test('Un 503 lleva el motivo de la API y se marca como proveedor no disponible', () async {
    const motivo = 'El proveedor de IA tardó más de 20 s.';
    final e = await _falla(_responde(503, {'detail': motivo}));

    expect(e.mensaje, motivo);
    expect(e.proveedorNoDisponible, isTrue);
    expect(e.presupuestoAgotado, isFalse);
  });

  test('Un 422 pide revisar los campos', () async {
    final e = await _falla(_responde(422, {'detail': []}));

    expect(e.mensaje, startsWith('Revise el enunciado'));
    expect(e.proveedorNoDisponible, isFalse);
    expect(e.presupuestoAgotado, isFalse);
  });

  test('Un 429 del límite por minuto trae el mensaje de la API y la espera de Retry-After',
      () async {
    final e = await _falla(
      _responde(429, {'detail': _detalleMinuto}, cabeceras: {'retry-after': '42'}),
    );

    expect(e.mensaje, _detalleMinuto);
    expect(e.mensaje, isNot(contains('429')));
    expect(e.presupuestoAgotado, isTrue);
    expect(e.proveedorNoDisponible, isFalse);
    expect(e.reintentarEn, const Duration(seconds: 42));
    expect(e.cupoDiarioAgotado, isFalse);
  });

  test('Un 429 con una espera de horas es el límite diario', () async {
    final e = await _falla(
      _responde(429, {'detail': _detalleDia}, cabeceras: {'retry-after': '18000'}),
    );

    expect(e.mensaje, _detalleDia);
    expect(e.reintentarEn, const Duration(hours: 5));
    expect(e.cupoDiarioAgotado, isTrue);
  });

  test('Un 429 sin Retry-After legible conserva el mensaje y no inventa la espera', () async {
    final sinCabecera = await _falla(_responde(429, {'detail': _detalleMinuto}));
    final ilegible = await _falla(
      _responde(429, {'detail': _detalleMinuto}, cabeceras: {'retry-after': 'pronto'}),
    );

    for (final e in [sinCabecera, ilegible]) {
      expect(e.mensaje, _detalleMinuto);
      expect(e.presupuestoAgotado, isTrue);
      expect(e.reintentarEn, isNull);
      expect(e.cupoDiarioAgotado, isFalse);
    }
  });

  test('Un 429 sin detail legible se explica igual, sin el código', () async {
    final e = await _falla(_responde(429, 'no es json de FastAPI'));

    expect(e.mensaje, startsWith('Se alcanzó el límite de solicitudes'));
    expect(e.mensaje, isNot(contains('429')));
  });

  test('Si no hay red, lo dice sin culpar al proveedor', () async {
    final e = await _falla(MockClient((_) async => throw http.ClientException('sin red')));

    expect(e.mensaje, startsWith('No se pudo contactar con la API'));
    expect(e.proveedorNoDisponible, isFalse);
    expect(e.presupuestoAgotado, isFalse);
  });
}
