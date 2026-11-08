import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/features/revision/data/servicio_revision.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

/// La revisión manual contra la API (RF-08), con un `MockClient`.
void main() {
  test('La revisión trae cada hoja con sus preguntas y lo que se midió', () async {
    final cliente = MockClient((peticion) async {
      expect(peticion.url.pathSegments, ['examenes', 'P 2', 'revision']);
      return http.Response.bytes(
        utf8.encode(jsonEncode({
          'examen_id': 'P 2',
          'hojas': [
            {
              'hoja_id': 'h-1', 'nota_en_decimas': 49, 'provisional': true,
              'codigo_completo': true,
              'preguntas': [
                {
                  'numero': 7,
                  'burbujas': [
                    {'opcion': 'A', 'tipo': 'vacia', 'confianza': 0},
                    {'opcion': 'C', 'tipo': 'tenue', 'confianza': 58},
                  ],
                  'con_recorte': true, 'resuelta': true, 'opcion_resuelta': null,
                  'resuelta_por': 'Docente', 'resuelta_en': '2026-11-05T21:00:00Z',
                },
              ],
            },
          ],
        })),
        200,
      );
    });

    final revision = await consultarRevision('P 2', cliente: cliente);

    final hoja = revision.hojas.single;
    expect((hoja.hojaId, hoja.notaEnDecimas, hoja.pendientes), ('h-1', 49, 0));
    final pregunta = hoja.preguntas.single;
    expect((pregunta.numero, pregunta.resuelta, pregunta.opcionResuelta), (7, true, null));
    expect(pregunta.burbujas[1].tipo, 'tenue');
  });

  test('Guardar manda el nombre y cada opción, y «ninguna» como nula', () async {
    late Map<String, dynamic> enviado;
    final cliente = MockClient((peticion) async {
      expect(peticion.method, 'POST');
      expect(peticion.url.pathSegments, ['examenes', 'P2', 'hojas', 'h-1', 'revision']);
      enviado = jsonDecode(peticion.body) as Map<String, dynamic>;
      return http.Response(
        jsonEncode({
          'hoja_id': 'h-1', 'estado': 'calificada', 'motivo': null, 'nota_en_decimas': 50,
          'provisional': false, 'preguntas_por_revisar': [], 'codigo_completo': true,
          'momento': '2026-11-05T21:00:00Z', 'revisada': true,
        }),
        200,
      );
    });

    final hoja = await guardarRevision('P2', 'h-1', 'Docente', {7: 'C', 9: null}, cliente: cliente);

    expect(enviado, {
      'por': 'Docente',
      'resoluciones': [
        {'numero': 7, 'opcion': 'C'},
        {'numero': 9, 'opcion': null},
      ],
    });
    expect((hoja.notaEnDecimas, hoja.revisada), (50, true));
  });

  test('Un rechazo del servidor llega con su motivo', () async {
    // FastAPI responde en UTF-8, con tildes.
    final cliente = MockClient(
      (_) async => http.Response.bytes(
        utf8.encode(jsonEncode({'detail': 'La pregunta 8 no está en revisión'})),
        422,
      ),
    );

    await expectLater(
      guardarRevision('P2', 'h-1', 'Docente', {8: 'A'}, cliente: cliente),
      throwsA(isA<ExcepcionDeRevision>().having(
        (e) => e.mensaje,
        'mensaje',
        'No se guardó: La pregunta 8 no está en revisión',
      )),
    );
  });

  test('El recorte se pide con el examen y la hoja codificados', () {
    expect(
      urlDelRecorte('P 2', 'h/1', 7),
      endsWith('/examenes/P%202/hojas/h%2F1/preguntas/7/recorte'),
    );
  });
}
