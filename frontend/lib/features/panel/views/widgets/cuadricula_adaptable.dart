import 'package:flutter/material.dart';

import '../../../../common/tema/tokens.dart';

/// Cuadrícula de tarjetas de altura pareja, para usar dentro de una página que ya se desplaza.
///
/// `GridView` no sirve aquí: dentro de [SingleChildScrollView] exigiría `shrinkWrap` y una altura
/// fija por celda, y las tarjetas del panel cambian de alto según el ancho (el texto se parte en
/// más líneas en teléfono). Con filas de [IntrinsicHeight], las dos tarjetas de una fila miden lo
/// que mida la más alta.
///
/// Vive en el panel porque `lib/common/` no tiene una; si otra pantalla la necesita, conviene
/// moverla a `lib/common/widgets/`.
class CuadriculaAdaptable extends StatelessWidget {
  const CuadriculaAdaptable({
    super.key,
    required this.columnas,
    required this.children,
    this.espacio = QEspacios.md,
  });

  final int columnas;
  final List<Widget> children;
  final double espacio;

  @override
  Widget build(BuildContext context) {
    final filas = <Widget>[];
    for (var inicio = 0; inicio < children.length; inicio += columnas) {
      if (filas.isNotEmpty) filas.add(SizedBox(height: espacio));
      if (columnas <= 1) {
        filas.add(children[inicio]);
        continue;
      }
      final celdas = <Widget>[];
      for (var columna = 0; columna < columnas; columna++) {
        if (columna > 0) celdas.add(SizedBox(width: espacio));
        final indice = inicio + columna;
        celdas.add(
          Expanded(child: indice < children.length ? children[indice] : const SizedBox.shrink()),
        );
      }
      filas.add(
        IntrinsicHeight(
          child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: celdas),
        ),
      );
    }
    return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: filas);
  }
}
