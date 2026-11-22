import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:frontend/app/sesion_actual.dart';
import 'package:frontend/common/api/cliente_con_sesion.dart';
import 'package:frontend/common/api/sesion.dart';

final _vence = DateTime.utc(2026, 11, 22, 6);
final _sesion = Sesion(token: 'v1.abc.def', correo: 'profe@utb.edu.co', vence: _vence);

void main() {
  group('Entrar (POST /sesion)', () {
    test('Manda el correo y la contraseña y devuelve la sesión', () async {
      late http.Request enviada;
      final cliente = MockClient((peticion) async {
        enviada = peticion;
        return http.Response(
          jsonEncode({
            'token': 'v1.abc.def',
            'correo': 'profe@utb.edu.co',
            'vence': '2026-11-22T06:00:00Z',
          }),
          200,
        );
      });

      final sesion = await iniciarSesion('profe@utb.edu.co', 'calculo-diferencial', cliente: cliente);

      expect(enviada.method, 'POST');
      expect(enviada.url.path, '/sesion');
      expect(jsonDecode(enviada.body), {'correo': 'profe@utb.edu.co', 'contrasena': 'calculo-diferencial'});
      expect(sesion.token, 'v1.abc.def');
      expect(sesion.correo, 'profe@utb.edu.co');
      expect(sesion.vence, _vence);
    });

    test('Un 401 dice que no coinciden, sin decir cuál de los dos', () async {
      final cliente = MockClient((_) async => http.Response('{"detail":"x"}', 401));

      expect(
        () => iniciarSesion('profe@utb.edu.co', 'otra', cliente: cliente),
        throwsA(isA<ExcepcionDeSesion>().having(
          (e) => e.mensaje,
          'mensaje',
          'El correo o la contraseña no coinciden.',
        )),
      );
    });

    test('Un 503 dice que el servidor no tiene configurado el inicio de sesión', () async {
      final cliente = MockClient((_) async => http.Response('{"detail":"x"}', 503));

      expect(
        () => iniciarSesion('profe@utb.edu.co', 'calculo-diferencial', cliente: cliente),
        throwsA(isA<ExcepcionDeSesion>()
            .having((e) => e.mensaje, 'mensaje', contains('no está configurado'))),
      );
    });

    test('Sin red dice que no se pudo contactar con el servidor', () async {
      final cliente = MockClient((_) async => throw http.ClientException('sin red'));

      expect(
        () => iniciarSesion('profe@utb.edu.co', 'calculo-diferencial', cliente: cliente),
        throwsA(isA<ExcepcionDeSesion>()
            .having((e) => e.mensaje, 'mensaje', 'No se pudo contactar con el servidor.')),
      );
    });
  });

  group('El cliente con sesión', () {
    test('Manda el token en cada petición', () async {
      String? encabezado;
      final cliente = ClienteConSesion(
        token: () => 'v1.abc.def',
        alVencer: () => fail('No venció'),
        interno: MockClient((peticion) async {
          encabezado = peticion.headers['Authorization'];
          return http.Response('{}', 200);
        }),
      );

      await cliente.get(Uri.parse('http://api/examenes'));

      expect(encabezado, 'Bearer v1.abc.def');
    });

    test('Sin sesión no manda el encabezado', () async {
      Map<String, String>? encabezados;
      final cliente = ClienteConSesion(
        token: () => null,
        alVencer: () {},
        interno: MockClient((peticion) async {
          encabezados = peticion.headers;
          return http.Response('{}', 200);
        }),
      );

      await cliente.get(Uri.parse('http://api/examenes'));

      expect(encabezados!.containsKey('Authorization'), isFalse);
    });

    test('Un 401 avisa que la sesión venció y deja pasar la respuesta', () async {
      var vencida = 0;
      final cliente = ClienteConSesion(
        token: () => 'v1.abc.def',
        alVencer: () => vencida++,
        interno: MockClient((_) async => http.Response('{"detail":"x"}', 401)),
      );

      final respuesta = await cliente.get(Uri.parse('http://api/examenes'));

      expect(respuesta.statusCode, 401);
      expect(vencida, 1);
    });
  });

  group('La sesión actual', () {
    test('Abrir la guarda en el almacén según «Recordar sesión», y cerrar la borra', () {
      final almacen = AlmacenEnMemoria();
      final sesion = SesionActual(almacen: almacen, reloj: () => DateTime.utc(2026, 11, 21));
      var avisos = 0;
      sesion.addListener(() => avisos++);

      sesion.abrir(_sesion, recordar: true);

      expect(sesion.sesion, _sesion);
      expect(sesion.token, 'v1.abc.def');
      expect((almacen.guardada, almacen.recordada), (_sesion, true));

      sesion.cerrar();

      expect(sesion.sesion, isNull);
      expect(sesion.vencio, isFalse);
      expect(almacen.guardada, isNull);
      expect(avisos, 2);
    });

    test('Vencer la cierra y lo dice, para que la entrada avise por qué', () {
      final sesion = SesionActual(almacen: AlmacenEnMemoria(), reloj: () => DateTime.utc(2026, 11, 21))
        ..abrir(_sesion, recordar: false);

      sesion.vencer();

      expect((sesion.sesion, sesion.vencio), (null, true));
    });

    test('Al arrancar recupera la sesión guardada si todavía vale', () {
      final almacen = AlmacenEnMemoria()..guardar(_sesion, recordar: true);

      final sesion = SesionActual(almacen: almacen, reloj: () => DateTime.utc(2026, 11, 21, 20));

      expect(sesion.sesion, _sesion);
    });

    test('Una sesión guardada que ya venció no se recupera y se borra', () {
      final almacen = AlmacenEnMemoria()..guardar(_sesion, recordar: true);

      final sesion = SesionActual(almacen: almacen, reloj: () => DateTime.utc(2026, 11, 22, 7));

      expect(sesion.sesion, isNull);
      expect(sesion.vencio, isFalse);
      expect(almacen.guardada, isNull);
    });

    test('Un token vencido no se manda aunque la sesión siga abierta en la pantalla', () {
      var ahora = DateTime.utc(2026, 11, 21);
      final sesion = SesionActual(almacen: AlmacenEnMemoria(), reloj: () => ahora)
        ..abrir(_sesion, recordar: false);

      ahora = DateTime.utc(2026, 11, 22, 7);

      expect(sesion.token, isNull);
    });

    test('La sesión viaja como JSON y vuelve igual', () {
      expect(Sesion.desdeJson(_sesion.aJson()), _sesion);
    });
  });
}
