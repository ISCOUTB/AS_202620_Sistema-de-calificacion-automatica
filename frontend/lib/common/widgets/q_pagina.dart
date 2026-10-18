import 'package:flutter/material.dart';

import '../tema/tokens.dart';

/// Contenedor de cada pantalla: desplazable, centrado y con un ancho máximo legible.
///
/// El margen lateral crece con la pantalla (16, 24 o 32 px), que es lo que pide el sistema de
/// diseño para teléfono, tableta y escritorio.
class QPagina extends StatelessWidget {
  const QPagina({super.key, required this.children, this.controlador});

  final List<Widget> children;
  final ScrollController? controlador;

  static double margenPara(double ancho) {
    if (ancho < 600) return QEspacios.md;
    if (ancho < 1024) return QEspacios.lg;
    return QEspacios.xl;
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, restricciones) {
        final margen = margenPara(restricciones.maxWidth);
        return SingleChildScrollView(
          controller: controlador,
          padding: EdgeInsetsDirectional.fromSTEB(margen, QEspacios.lg, margen, QEspacios.xxl),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: QAnchos.contenido),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: children,
              ),
            ),
          ),
        );
      },
    );
  }
}
