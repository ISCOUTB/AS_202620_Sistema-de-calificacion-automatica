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
<<<<<<< HEAD
              'codigo_completo': true, 'codigo': 'T20261105', 'nombre_archivo': 'hoja1.jpg',
=======
              'codigo_completo': true, 'nombre_archivo': 'hoja1.jpg',
>>>>>>> 88090461e81adc5d38504d646046fa218be33615
              'recibida_en': '2026-11-16T19:32:00Z',
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
    expect(hoja.nombreArchivo, 'hoja1.jpg');
<<<<<<< HEAD
    expect(hoja.codigo, 'T20261105');
=======
>>>>>>> 88090461e81adc5d38504d646046fa218be33615
    expect(hoja.recibidaEn, DateTime.utc(2026, 11, 16, 19, 32));
    final pregunta = hoja.preguntas.single;
    expect((pregunta.numero, pregunta.resuelta, pregunta.opcionResuelta), (7, true, null));
    expect(pregunta.burbujas[1].tipo, 'tenue');
  });

<<<<<<< HEAD
  test('Una hoja sin código leído llega con el código nulo', () {
    final hoja = HojaEnRevision.desdeJson({
      'hoja_id': 'h-1', 'nota_en_decimas': 30, 'provisional': true, 'codigo_completo': false,
      'codigo': null, 'preguntas': [],
    });

    expect(hoja.codigo, isNull);
  });

=======
>>>>>>> 88090461e81adc5d38504d646046fa218be33615
  test('Cada pregunta trae la opción sugerida y cuándo se resolvió', () {
    final pregunta = PreguntaEnRevision.desdeJson({
      'numero': 4, 'burbujas': [], 'con_recorte': false, 'resuelta': true,
      'opcion_resuelta': 'B', 'resuelta_por': 'Docente', 'resuelta_en': '2026-11-19T19:40:00Z',
      'opcion_sugerida': 'B',
    });
    // Una hoja leída antes del corte no trae la sugerencia.
    final vieja = PreguntaEnRevision.desdeJson({
      'numero': 5, 'burbujas': [], 'con_recorte': false, 'resuelta': false,
      'opcion_resuelta': null, 'resuelta_por': null, 'resuelta_en': null,
    });

    expect((pregunta.opcionSugerida, pregunta.resueltaEn), ('B', DateTime.utc(2026, 11, 19, 19, 40)));
    expect((vieja.opcionSugerida, vieja.resueltaEn), (null, null));
  });

  test('Primero las confusas, después las preseleccionadas y al final las resueltas', () {
    const hoja = HojaEnRevision(
      hojaId: 'h-1',
      notaEnDecimas: 30,
      provisional: true,
      codigoCompleto: true,
      preguntas: [
        PreguntaEnRevision(
            numero: 1, burbujas: [], conRecorte: false, resuelta: true, opcionResuelta: 'A'),
        PreguntaEnRevision(numero: 2, burbujas: [], conRecorte: false, opcionSugerida: 'C'),
        PreguntaEnRevision(numero: 3, burbujas: [], conRecorte: false),
        PreguntaEnRevision(numero: 5, burbujas: [], conRecorte: false, opcionSugerida: 'D'),
        PreguntaEnRevision(numero: 4, burbujas: [], conRecorte: false),
      ],
    );

    expect([for (final p in preguntasEnOrden(hoja)) p.numero], [3, 4, 2, 5, 1]);
  });

  group('La lista de hojas', () {
    PreguntaEnRevision pregunta(int numero, {DateTime? resueltaEn}) => PreguntaEnRevision(
          numero: numero,
          burbujas: const [],
          conRecorte: false,
          resuelta: resueltaEn != null,
          resueltaEn: resueltaEn,
        );
    HojaEnRevision hoja(String id, {DateTime? recibida, bool revisada = false}) => HojaEnRevision(
          hojaId: id,
          notaEnDecimas: 30,
          provisional: !revisada,
          codigoCompleto: true,
          preguntas: [pregunta(1, resueltaEn: revisada ? DateTime(2026, 11, 19) : null)],
          recibidaEn: recibida,
        );
    final vieja = hoja('vieja', recibida: DateTime(2026, 11, 15), revisada: true);
    final nueva = hoja('nueva', recibida: DateTime(2026, 11, 17));
    final media = hoja('media', recibida: DateTime(2026, 11, 16), revisada: true);
    final sinHora1 = hoja('sin-hora-1');
    final sinHora2 = hoja('sin-hora-2', revisada: true);
    final hojas = [sinHora1, vieja, nueva, sinHora2, media];

    List<String> ids(List<HojaEnRevision> lista) => [for (final h in lista) h.hojaId];

    test('Se edita cuando se guardó la última de sus preguntas', () {
      final editada = HojaEnRevision(
        hojaId: 'h',
        notaEnDecimas: 30,
        provisional: true,
        codigoCompleto: true,
        preguntas: [
          pregunta(1, resueltaEn: DateTime.utc(2026, 11, 18, 10)),
          pregunta(2),
          pregunta(3, resueltaEn: DateTime.utc(2026, 11, 19, 19, 40)),
        ],
      );

      expect(editada.editadaEn, DateTime.utc(2026, 11, 19, 19, 40));
      expect(hoja('h').editadaEn, isNull);
    });

    test('La edición se lee en la hora del docente, como la llegada', () {
      expect(edicionLegible(DateTime(2026, 11, 19, 14, 40)), 'Editada el 19 nov, 14:40');
      final utc = DateTime.utc(2026, 11, 19, 19, 40);
      expect(edicionLegible(utc), edicionLegible(utc.toLocal()));
    });

    test('Con los dos filtros, primero todas las por revisar y después las revisadas', () {
      // Cada grupo va de la más nueva a la más vieja, con las que no tienen hora al final: una
      // revisada nunca queda entre dos por revisar, aunque se haya subido entre ellas.
      final porRevisarVieja = hoja('por-revisar-vieja', recibida: DateTime(2026, 11, 14));
      expect(
        ids(hojasVisibles([...hojas, porRevisarVieja], porRevisar: true, revisadas: true)),
        ['nueva', 'por-revisar-vieja', 'sin-hora-1', 'media', 'vieja', 'sin-hora-2'],
      );
    });

    test('Cada filtro deja solo las suyas, y sin ninguno no queda nada', () {
      expect(ids(hojasVisibles(hojas, porRevisar: true, revisadas: false)), ['nueva', 'sin-hora-1']);
      expect(
        ids(hojasVisibles(hojas, porRevisar: false, revisadas: true)),
        ['media', 'vieja', 'sin-hora-2'],
      );
      expect(hojasVisibles(hojas, porRevisar: false, revisadas: false), isEmpty);
    });
  });

  test('Si la API no manda el nombre ni la hora, la hoja queda sin ellos', () {
    final hoja = HojaEnRevision.desdeJson({
      'hoja_id': 'h-1', 'nota_en_decimas': 49, 'provisional': true,
      'codigo_completo': true, 'preguntas': [],
    });

    expect((hoja.nombreArchivo, hoja.recibidaEn), (null, null));
  });

  test('La llegada se lee en la hora del docente, con el mes abreviado', () {
    expect(llegadaLegible(DateTime(2026, 11, 16, 9, 5)), 'Subida el 16 nov, 09:05');
    // La API la manda en UTC; se muestra en la hora del navegador.
    final utc = DateTime.utc(2026, 11, 16, 19, 32);
    expect(llegadaLegible(utc), llegadaLegible(utc.toLocal()));
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

<<<<<<< HEAD
    final hoja = await guardarRevision('P2', 'h-1', {7: 'C', 9: null}, cliente: cliente);

    expect(enviado, {
=======
    final hoja = await guardarRevision('P2', 'h-1', 'Docente', {7: 'C', 9: null}, cliente: cliente);

    expect(enviado, {
      'por': 'Docente',
>>>>>>> 88090461e81adc5d38504d646046fa218be33615
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
<<<<<<< HEAD
      guardarRevision('P2', 'h-1', {8: 'A'}, cliente: cliente),
=======
      guardarRevision('P2', 'h-1', 'Docente', {8: 'A'}, cliente: cliente),
>>>>>>> 88090461e81adc5d38504d646046fa218be33615
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
