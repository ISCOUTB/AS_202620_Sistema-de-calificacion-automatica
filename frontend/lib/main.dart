import 'package:flutter/material.dart';

import 'app/almacen_de_sesion.dart';
import 'app/app.dart';
import 'app/marco_app.dart';
import 'app/servicios.dart';
import 'app/sesion_actual.dart';
import 'common/api/sesion.dart';

void main() {
  // Una sola sesión para toda la aplicación: la entrada la abre y los servicios mandan su token.
  final sesion = SesionActual(almacen: almacenDelNavegador());
  runApp(QuantiaApp(
    servicios: ServiciosApp.reales(sesion),
    seccionInicial: seccionDesdeUrl(Uri.base),
    sesion: sesion,
    iniciarSesion: iniciarSesion,
  ));
}

/// La sección inicial sale de `?seccion=` en la URL (`panel`, `carga`, `revision` o `pauta`).
///
/// Permite enlazar directo a una sección, por ejemplo desde el README o en una sustentación, y
/// capturar cada pantalla sin interacción. Un valor desconocido o ausente abre el panel.
Seccion seccionDesdeUrl(Uri url) {
  final pedida = url.queryParameters['seccion'];
  return Seccion.values.firstWhere(
    (seccion) => seccion.name == pedida,
    orElse: () => Seccion.panel,
  );
}
