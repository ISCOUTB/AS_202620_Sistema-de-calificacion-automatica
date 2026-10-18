import 'package:flutter/material.dart';

import 'app/app.dart';
import 'app/marco_app.dart';
import 'app/servicios.dart';

void main() {
  runApp(QuantiaApp(
    servicios: ServiciosApp.reales(),
    seccionInicial: seccionDesdeUrl(Uri.base),
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
