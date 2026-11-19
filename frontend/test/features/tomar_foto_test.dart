import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';

import 'package:frontend/features/carga/data/servicio_carga.dart';
import 'package:frontend/features/carga/data/tomar_foto.dart';

final _momento = DateTime(2026, 11, 19, 14, 32, 5);

ArchivoSeleccionado _deLaCamara(String nombre) =>
    ArchivoSeleccionado(nombre: nombre, contenido: Uint8List.fromList([0xFF, 0xD8, 0xFF, 1]));

void main() {
  group('El nombre de una foto tomada desde la aplicación', () {
    test('lleva la hora en que se tomó, porque en iPhone todas llegan como image.jpg', () {
      expect(nombreDeFoto(_momento, 'image.jpg'), 'foto 14.32.05.jpg');
    });

    test('conserva la extensión que trae la cámara, en minúsculas', () {
      expect(nombreDeFoto(_momento, 'IMG_20261119_143205.JPEG'), 'foto 14.32.05.jpeg');
    });

    test('sin extensión queda como .jpg', () {
      expect(nombreDeFoto(_momento, 'blob'), 'foto 14.32.05.jpg');
    });
  });

  group('tomarFoto', () {
    test('devuelve la foto con su nombre nuevo y el contenido de la cámara', () async {
      final foto = _deLaCamara('image.jpg');

      final tomada = await tomarFoto(
        abrir: () async => foto,
        ahora: () => _momento,
        reducir: (archivo) async => null,
      );

      expect(tomada?.nombre, 'foto 14.32.05.jpg');
      expect(tomada?.contenido, foto.contenido);
    });

    test('la prepara como al seleccionarla: si se reduce, sube la reducida', () async {
      final reducida = Uint8List.fromList([0xFF, 0xD8]);

      final tomada = await tomarFoto(
        abrir: () async => _deLaCamara('image.jpg'),
        ahora: () => _momento,
        reducir: (archivo) async => ArchivoSeleccionado(
          nombre: archivo.nombre,
          contenido: reducida,
          ladoMayorPx: 3200,
        ),
      );

      expect(tomada?.nombre, 'foto 14.32.05.jpg');
      expect(tomada?.contenido, reducida);
      expect(tomada?.ladoMayorPx, 3200);
    });

    test('si el docente cierra la cámara sin tomar nada, devuelve null', () async {
      final tomada = await tomarFoto(
        abrir: () async => null,
        ahora: () => _momento,
        reducir: (archivo) async => fail('no hay nada que reducir'),
      );

      expect(tomada, isNull);
    });
  });
}
