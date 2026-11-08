import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:frontend/features/carga/data/preparacion_de_hojas.dart';
import 'package:frontend/features/carga/data/servicio_carga.dart';

/// Cómo se preparan las fotos antes de subirlas. La reducción de verdad usa el canvas del
/// navegador; aquí se reemplaza por un sustituto y se prueba lo que se decide alrededor de ella.

ArchivoSeleccionado _archivo(String nombre, int bytes) =>
    ArchivoSeleccionado(nombre: nombre, contenido: Uint8List(bytes));

void main() {
  test('Una foto se reduce hasta 3 200 px en el lado mayor y nunca se agranda', () {
    expect(escalaPara(3000, 4000), closeTo(0.8, 1e-9));
    expect(escalaPara(4000, 3000), closeTo(0.8, 1e-9));
    expect(escalaPara(2400, 3200), 1);
    expect(escalaPara(1700, 2200), 1);
  });

  test('Con 3 200 px, una hoja que ocupa dos tercios de la foto sigue sobre 7,5 px/mm', () {
    // La lectura rechaza por debajo de 7,5 px/mm (ADR-0023), y la hoja carta mide 279,4 mm.
    const pxPorMm = ladoMaximoPx * (2 / 3) / 279.4;

    expect(pxPorMm, greaterThan(7.5));
  });

  test('Una foto preparada siempre se llama .jpg, que es lo que es', () {
    expect(nombreJpg('hoja 1.PNG'), 'hoja 1.jpg');
    expect(nombreJpg('IMG_2041.jpeg'), 'IMG_2041.jpg');
    expect(nombreJpg('scan.v2.jpg'), 'scan.v2.jpg');
    expect(nombreJpg('sin_extension'), 'sin_extension.jpg');
  });

  test('Se usa la foto reducida si quedó más liviana', () async {
    final original = _archivo('IMG_2041.jpeg', 4000000);

    final preparada = await prepararUna(original, (_) async => _archivo('IMG_2041.jpg', 650000));

    expect(preparada.nombre, 'IMG_2041.jpg');
    expect(preparada.contenido.length, 650000);
  });

  test('Un escaneo que ya era liviano, o lo que el navegador no entendió, viaja como llegó',
      () async {
    final escaneo = _archivo('escaneo.jpg', 300000);
    final rara = _archivo('rara.png', 2000000);

    final comoLlego = await prepararUna(
      escaneo,
      (_) async => ArchivoSeleccionado(
        nombre: 'escaneo.jpg',
        contenido: Uint8List(450000),
        ladoMayorPx: 2200,
      ),
    );
    expect(comoLlego.contenido, same(escaneo.contenido));
    expect(comoLlego.nombre, 'escaneo.jpg');
    // El tamaño que midió el navegador viaja con la original, para el aviso de resolución.
    expect(comoLlego.ladoMayorPx, 2200);
    expect(await prepararUna(rara, (_) async => null), same(rara));
  });

  test('Una foto que no llega a 2 100 px no alcanza 7,5 px/mm ni con la hoja llenándola', () {
    ArchivoSeleccionado conLado(int? lado) =>
        ArchivoSeleccionado(nombre: 'f.jpg', contenido: Uint8List(1), ladoMayorPx: lado);

    expect(ladoMinimoPx * 1.0 / 279.4, greaterThanOrEqualTo(7.5));
    expect(tienePocaResolucion(conLado(1600)), isTrue);
    expect(tienePocaResolucion(conLado(2100)), isFalse);
    expect(tienePocaResolucion(conLado(3200)), isFalse);
    // Si el navegador no la pudo abrir, no se adivina: decide la lectura.
    expect(tienePocaResolucion(conLado(null)), isFalse);
  });

  test('Lo que no es una foto no pasa por el navegador', () async {
    final pdf = _archivo('hoja.pdf', 500000);
    var llamadas = 0;

    final preparada = await prepararUna(pdf, (_) async {
      llamadas++;
      return null;
    });

    expect(preparada, same(pdf));
    expect(llamadas, 0);
  });

  test('Las tandas no pasan del peso ni de las hojas que admite la API, y conservan el orden', () {
    final fotos = [for (var i = 0; i < 200; i++) _archivo('h$i.jpg', 650000)];

    final tandas = repartirEnTandas(fotos);

    expect(tandas.length, 2);
    for (final tanda in tandas) {
      expect(tanda.fold<int>(0, (suma, a) => suma + a.contenido.length),
          lessThanOrEqualTo(bytesPorTanda));
      expect(tanda.length, lessThanOrEqualTo(hojasPorTanda));
    }
    expect([for (final tanda in tandas) ...tanda], fotos);
  });

  test('Un examen de escaneos livianos se corta por la cantidad de hojas', () {
    final escaneos = [for (var i = 0; i < 300; i++) _archivo('e$i.jpg', 1000)];

    expect([for (final tanda in repartirEnTandas(escaneos)) tanda.length], [250, 50]);
  });

  test('Un archivo más pesado que una tanda va solo, y la API dice el motivo', () {
    final archivos = [_archivo('a.jpg', 10), _archivo('enorme.jpg', 100), _archivo('b.jpg', 10)];

    final tandas = repartirEnTandas(archivos, maxBytes: 50);

    expect([for (final tanda in tandas) tanda.map((a) => a.nombre).toList()], [
      ['a.jpg'],
      ['enorme.jpg'],
      ['b.jpg'],
    ]);
  });
}
