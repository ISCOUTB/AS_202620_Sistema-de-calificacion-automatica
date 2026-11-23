import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:frontend/app/servicios.dart';
import 'package:frontend/app/sesion_actual.dart';
import 'package:frontend/common/api/sesion.dart';
import 'package:frontend/features/carga/data/servicio_carga.dart';
import 'package:frontend/features/pauta/data/servicio_distractores.dart';

SesionActual _abierta() => SesionActual(
      almacen: AlmacenEnMemoria(),
      reloj: () => DateTime.utc(2026, 11, 21),
    )..abrir(
        Sesion(token: 'v1.abc.def', correo: 'profe@utb.edu.co', vence: DateTime.utc(2026, 11, 22)),
        recordar: false,
      );

/// Llama a cada servicio de la API una vez. La respuesta de la prueba no les sirve, así que
/// fallan: lo que importa es la petición que salió.
Future<void> _llamarATodos(ServiciosApp servicios) async {
  Future<void> intentar(Future<Object?> Function() llamada) async {
    try {
      await llamada();
    } catch (_) {
      // Se espera: la respuesta de la prueba no es la de la API.
    }
  }

  await intentar(() => servicios.subirHojas(
        'E',
        [ArchivoSeleccionado(nombre: 'a.jpg', contenido: Uint8List.fromList(const [1]))],
      ));
  await intentar(() => servicios.proponerDistractores(
        const SolicitudDistractores(enunciado: 'Derivada de x²', respuestaCorrecta: '2x'),
      ));
  await intentar(() => servicios.consultarResultados!('E'));
  await intentar(() => servicios.listarExamenes!());
  await intentar(() => servicios.consultarRevision!('E'));
  await intentar(() => servicios.guardarRevision!('E', 'h-1', {7: 'C'}));
  await intentar(() => servicios.consultarClave!('E'));
  await intentar(() => servicios.guardarClave!('E', ['A']));
  await intentar(() => servicios.habilitarClave!('E'));
}

void main() {
  test('Cada servicio de la API manda el token de la sesión', () async {
    final enviadas = <String, String?>{};
    final servicios = ServiciosApp.reales(
      _abierta(),
      interno: MockClient((peticion) async {
        enviadas['${peticion.method} ${peticion.url.path}'] = peticion.headers['Authorization'];
        return http.Response('{}', 500);
      }),
    );

    await _llamarATodos(servicios);

    expect(enviadas.keys, {
      'POST /examenes/E/hojas',
      'POST /distractores',
      'GET /examenes/E/resultados',
      'GET /examenes',
      'GET /examenes/E/revision',
      'POST /examenes/E/hojas/h-1/revision',
      'GET /examenes/E/clave',
      'PUT /examenes/E/clave',
      'POST /examenes/E/clave/habilitacion',
    });
    expect(enviadas.values.toSet(), {'Bearer v1.abc.def'});
  });

  test('El recorte de cada pregunta pide la imagen con el mismo token', () {
    final servicios = ServiciosApp.reales(_abierta(), interno: MockClient((_) async => http.Response('', 200)));

    expect(servicios.encabezadosDelRecorte!(), {'Authorization': 'Bearer v1.abc.def'});
  });

  test('Un 401 de la API cierra la sesión para volver a la entrada', () async {
    final sesion = _abierta();
    final servicios = ServiciosApp.reales(
      sesion,
      interno: MockClient((_) async => http.Response('{"detail":"Inicia sesión para continuar."}', 401)),
    );

    await expectLater(servicios.listarExamenes!(), throwsA(anything));

    expect((sesion.sesion, sesion.vencio), (null, true));
  });
}
