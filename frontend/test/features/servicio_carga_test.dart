import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/features/carga/data/servicio_carga.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

/// La traducción de cada respuesta de `POST /examenes/{examen_id}/hojas` a lo que ve el docente,
/// contra un `MockClient`: sin red y sin backend.

final _lote = [ArchivoSeleccionado(nombre: 'hoja1.jpg', contenido: Uint8List(3))];

/// Un cliente que responde siempre con [codigo] y un cuerpo en JSON.
MockClient _responde(int codigo, [Object cuerpo = const {'detail': 'x'}]) =>
    MockClient((_) async => http.Response.bytes(
          utf8.encode(jsonEncode(cuerpo)),
          codigo,
          headers: {'content-type': 'application/json'},
        ));

/// La excepción que lanza el servicio con ese cliente. Falla si no lanza.
Future<ExcepcionDeCarga> _falla(MockClient cliente, {String examen = 'CALC-2026-01'}) async {
  try {
    await subirHojas(examen, _lote, cliente: cliente);
  } on ExcepcionDeCarga catch (e) {
    return e;
  }
  fail('El servicio no lanzó ExcepcionDeCarga.');
}

void main() {
  _tandas();

  test('Un 5xx no afirma que no entró nada: algunas hojas pudieron entrar', () async {
    // El proxy de Render puede devolver 502 o 504 mientras la API sigue trabajando. Antes, el
    // mensaje decía «No se recibió ninguna hoja» e invitaba a duplicarlas.
    for (final codigo in [500, 502, 504]) {
      final error = await _falla(_responde(codigo));

      expect(error.pudieronEntrar, isTrue, reason: 'con $codigo');
      expect(error.mensaje, contains('pudieron entrar'));
      expect(error.mensaje, isNot(contains('ninguna hoja')));
    }
  });

  test('Un 4xx sale antes de procesar el lote: ahí sí no entró ninguna hoja', () async {
    final error = await _falla(_responde(422));

    expect(error.pudieronEntrar, isFalse);
    expect(error.mensaje, contains('No entró ninguna hoja'));
  });

  test('Un 200 ilegible avisa que algunas hojas pudieron entrar', () async {
    final ilegible = await _falla(MockClient((_) async => http.Response('no es JSON', 200)));

    expect(ilegible.pudieronEntrar, isTrue);
  });

  test('El examen viaja codificado en la ruta', () async {
    // Sin codificar, «P2#1» mandaba la petición a /examenes/P2: lo demás quedaba como fragmento
    // de la URL.
    late Uri pedida;
    final cliente = MockClient((peticion) async {
      pedida = peticion.url;
      return http.Response.bytes(
        utf8.encode(jsonEncode({'total_procesados': 0, 'aceptadas': [], 'rechazados': []})),
        200,
      );
    });

    await subirHojas('P2#1 ¿B?', _lote, cliente: cliente);

    expect(pedida.pathSegments, ['examenes', 'P2#1 ¿B?', 'hojas']);
    expect(pedida.hasFragment, isFalse);
    expect(pedida.hasQuery, isFalse);
  });
}

/// Un cliente que acepta cada archivo que recibe, con su nombre, salvo en las peticiones que
/// [falla] marque: ahí responde con 429, como el presupuesto de carga.
MockClient _aceptaTodo({bool Function(int peticion)? falla}) {
  var peticiones = 0;
  return MockClient((peticion) async {
    peticiones++;
    if (falla?.call(peticiones) ?? false) {
      return http.Response('{"detail": "x"}', 429, headers: {'content-type': 'application/json'});
    }
    final nombres = RegExp(r'filename="([^"]+)"')
        .allMatches(latin1.decode(peticion.bodyBytes))
        .map((m) => m.group(1)!)
        .toList();
    return http.Response(
      jsonEncode({
        'total_procesados': nombres.length,
        'aceptadas': [
          for (final n in nombres) {'nombre_archivo': n, 'trabajo_id': 't-$n'},
        ],
        'rechazados': [],
      }),
      200,
      headers: {'content-type': 'application/json'},
    );
  });
}

List<ArchivoSeleccionado> _hojas(int cantidad) => [
      for (var i = 0; i < cantidad; i++)
        ArchivoSeleccionado(nombre: 'h$i.jpg', contenido: Uint8List(3)),
    ];

void _tandas() {
  test('Un examen que no cabe en una petición sale en tandas y llega un solo reporte', () async {
    // 251 hojas: una más de las que la API admite por lote.
    final lote = _hojas(251);

    final resultado = await subirHojas('CALC-2026-01', lote, cliente: _aceptaTodo());

    expect(resultado.totalProcesados, 251);
    expect(resultado.aceptadas.map((h) => h.nombreArchivo), [for (final a in lote) a.nombre]);
  });

  test('Si la segunda tanda falla, se dice cuántas hojas entraron y que pueden duplicarse',
      () async {
    final error = await () async {
      try {
        await subirHojas('CALC-2026-01', _hojas(251), cliente: _aceptaTodo(falla: (n) => n == 2));
      } on ExcepcionDeCarga catch (e) {
        return e;
      }
      fail('El servicio no lanzó ExcepcionDeCarga.');
    }();

    expect(error.pudieronEntrar, isTrue);
    expect(error.mensaje, contains('Entraron 250 de 251 hojas'));
  });

  test('Si la primera tanda falla, no entró nada y se puede reintentar', () async {
    final error = await _falla(_aceptaTodo(falla: (n) => n == 1));

    expect(error.pudieronEntrar, isFalse);
  });
}
