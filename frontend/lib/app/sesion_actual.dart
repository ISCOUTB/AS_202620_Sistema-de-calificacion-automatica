import 'package:flutter/foundation.dart';

import '../common/api/sesion.dart';

/// Dónde queda la sesión entre una recarga de la página y la siguiente.
abstract interface class AlmacenDeSesion {
  Sesion? leer();

  /// Con [recordar], la sesión sobrevive a cerrar el navegador; sin él, solo a recargar la pestaña.
  void guardar(Sesion sesion, {required bool recordar});

  void borrar();
}

/// El almacén de las pruebas y de lo que corre fuera del navegador: solo en memoria.
class AlmacenEnMemoria implements AlmacenDeSesion {
  Sesion? guardada;
  bool? recordada;

  @override
  Sesion? leer() => guardada;

  @override
  void guardar(Sesion sesion, {required bool recordar}) {
    guardada = sesion;
    recordada = recordar;
  }

  @override
  void borrar() {
    guardada = null;
    recordada = null;
  }
}

/// La sesión de quien usa la aplicación (A-05, ADR-0025): la abre la pantalla de entrada, la usan
/// los servicios para mandar el token y la cierran «Salir» o un 401 de la API.
///
/// Al crearse recupera la que quedó guardada si todavía vale, para que recargar la página no
/// obligue a entrar otra vez.
class SesionActual extends ChangeNotifier {
  SesionActual({required AlmacenDeSesion almacen, DateTime Function()? reloj})
      : _almacen = almacen,
        _reloj = reloj ?? DateTime.now {
    final guardada = _almacen.leer();
    if (guardada == null) return;
    if (guardada.vencidaEn(_ahora())) {
      _almacen.borrar();
    } else {
      _sesion = guardada;
    }
  }

  final AlmacenDeSesion _almacen;
  final DateTime Function() _reloj;
  Sesion? _sesion;
  bool _vencio = false;

  DateTime _ahora() => _reloj().toUtc();

  Sesion? get sesion => _sesion;

  /// Si la última sesión se cerró porque la API dejó de aceptarla, y no porque alguien salió: la
  /// entrada lo dice, para que no parezca un error.
  bool get vencio => _vencio;

  /// El token para mandar ahora, o null si no hay sesión o ya venció.
  String? get token {
    final sesion = _sesion;
    if (sesion == null || sesion.vencidaEn(_ahora())) return null;
    return sesion.token;
  }

  void abrir(Sesion sesion, {required bool recordar}) {
    _sesion = sesion;
    _vencio = false;
    _almacen.guardar(sesion, recordar: recordar);
    notifyListeners();
  }

  void cerrar() {
    _sesion = null;
    _vencio = false;
    _almacen.borrar();
    notifyListeners();
  }

  /// La API respondió 401: el token venció o ya no vale. Sin sesión abierta no hace nada, porque
  /// varias peticiones pueden volver con 401 a la vez.
  void vencer() {
    if (_sesion == null) return;
    _sesion = null;
    _vencio = true;
    _almacen.borrar();
    notifyListeners();
  }
}
