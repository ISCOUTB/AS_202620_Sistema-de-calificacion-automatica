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
