import 'package:flutter/material.dart';

import '../common/tema/tema.dart';
import 'marco_app.dart';
import 'servicios.dart';

const nombreSistema = 'QuantIA';

/// Raíz de la aplicación. Recibe los servicios para que las pruebas monten la aplicación entera
/// con sustitutos.
class QuantiaApp extends StatelessWidget {
  const QuantiaApp({super.key, required this.servicios, this.seccionInicial = Seccion.panel});

  final ServiciosApp servicios;
  final Seccion seccionInicial;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: nombreSistema,
      debugShowCheckedModeBanner: false,
      theme: construirTema(),
      home: MarcoApp(servicios: servicios, seccionInicial: seccionInicial),
    );
  }
}
