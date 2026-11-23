import 'package:flutter/material.dart';

import '../common/api/sesion.dart';
import '../common/tema/tema.dart';
import '../features/sesion/views/pantalla_entrada.dart';
import 'marco_app.dart';
import 'servicios.dart';
import 'sesion_actual.dart';

const nombreSistema = 'QuantIA';

/// Raíz de la aplicación. Recibe los servicios para que las pruebas monten la aplicación entera
/// con sustitutos.
///
/// Con [sesion], la aplicación empieza en la entrada y muestra las secciones solo con una sesión
/// abierta (A-05, ADR-0025). Sin ella, las monta directo: así prueban las secciones las pruebas
/// que no tratan de la sesión. Lo que protege los datos no es esta puerta sino la API, que pide el
/// token en cada ruta.
class QuantiaApp extends StatelessWidget {
  const QuantiaApp({
    super.key,
    required this.servicios,
    this.seccionInicial = Seccion.panel,
    this.sesion,
    this.iniciarSesion,
  });

  final ServiciosApp servicios;
  final Seccion seccionInicial;
  final SesionActual? sesion;

  /// Entra con correo y contraseña; lo usa la pantalla de entrada cuando hay [sesion].
  final Future<Sesion> Function(String correo, String contrasena)? iniciarSesion;

  @override
  Widget build(BuildContext context) {
    final sesion = this.sesion;
    return MaterialApp(
      title: nombreSistema,
      debugShowCheckedModeBanner: false,
      theme: construirTema(),
      home: sesion == null
          ? MarcoApp(servicios: servicios, seccionInicial: seccionInicial)
          : ListenableBuilder(
              listenable: sesion,
              builder: (context, _) {
                final abierta = sesion.sesion;
                if (abierta == null) {
                  return PantallaEntrada(
                    aviso: sesion.vencio ? 'Su sesión terminó. Vuelva a entrar.' : null,
                    alEntrar: (correo, contrasena, recordar) async {
                      final entrar = iniciarSesion;
                      if (entrar == null) return;
                      sesion.abrir(await entrar(correo, contrasena), recordar: recordar);
                    },
                  );
                }
                return MarcoApp(
                  servicios: servicios,
                  seccionInicial: seccionInicial,
                  correo: abierta.correo,
                  alSalir: sesion.cerrar,
                );
              },
            ),
    );
  }
}
