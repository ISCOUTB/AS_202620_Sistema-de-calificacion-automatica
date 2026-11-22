import 'dart:convert';

import 'package:web/web.dart' as web;

import '../common/api/sesion.dart';
import 'sesion_actual.dart';

const _clave = 'quantia.sesion';

/// La sesión en el almacenamiento del navegador: en `localStorage` si el docente marcó «Recordar
/// sesión en este dispositivo», y si no en `sessionStorage`, que se borra al cerrar la pestaña.
///
/// Cualquier script de la página puede leer ese almacenamiento. Se acepta porque el sitio no
/// muestra HTML de terceros ni de usuarios, y el token vence a las pocas horas (ADR-0025). Un
/// navegador en modo privado puede negar el acceso: entonces la sesión dura lo que la página.
AlmacenDeSesion almacenDelNavegador() => _AlmacenDelNavegador();

class _AlmacenDelNavegador implements AlmacenDeSesion {
  List<web.Storage> _almacenes() {
    try {
      return [web.window.sessionStorage, web.window.localStorage];
    } catch (_) {
      return const [];
    }
  }

  @override
  Sesion? leer() {
    for (final almacen in _almacenes()) {
      try {
        final texto = almacen.getItem(_clave);
        if (texto != null) return Sesion.desdeJson(jsonDecode(texto) as Map<String, dynamic>);
      } catch (_) {
        // Una entrada ilegible es como no tener sesión: se vuelve a entrar.
      }
    }
    return null;
  }

  @override
  void guardar(Sesion sesion, {required bool recordar}) {
    borrar();
    try {
      final almacen = recordar ? web.window.localStorage : web.window.sessionStorage;
      almacen.setItem(_clave, jsonEncode(sesion.aJson()));
    } catch (_) {
      // Sin almacenamiento, la sesión dura lo que la página.
    }
  }

  @override
  void borrar() {
    for (final almacen in _almacenes()) {
      try {
        almacen.removeItem(_clave);
      } catch (_) {
        // Nada que borrar.
      }
    }
  }
}
