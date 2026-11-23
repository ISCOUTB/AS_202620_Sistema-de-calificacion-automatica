import 'package:flutter/material.dart';

import '../../../common/tema/tokens.dart';

/// Los colores de los gráficos del panel. Se validaron con el verificador de paletas (claridad,
/// saturación, separación para daltonismo y contraste sobre el blanco de la tarjeta):
///
/// * Las marcas: verde, rojo, violeta y ámbar pasan todas las pruebas. El rojo y el verde quedan
///   juntos en la barra y su separación para deuteranopía es la justa (8,6), así que la barra
///   lleva siempre su leyenda con el nombre, el número y el porcentaje de cada parte.
/// * «En blanco» es gris a propósito: es la ausencia de marca. No llega al contraste de 3:1, y por
///   eso su cifra va escrita en la leyenda.
/// * Las notas y los aciertos: cobalto (aprobado, 50 % o más) frente a ámbar (no aprobado, menos
///   del 50 %), con una separación amplia.
///
/// El texto nunca lleva estos colores: usa los de texto del tema, y el color va en la muestra.
abstract final class ColoresGraficos {
  static const correcta = Color(0xFF059669);
  static const incorrecta = Color(0xFFDC2626);
  static const doble = Color(0xFF7C3AED);
  static const tenue = Color(0xFFD97706);
  static const enBlanco = Color(0xFF94A3B8);

  static const aprobado = QColores.cobalto;
  static const noAprobado = Color(0xFFD97706);

  /// La curva normal, sobre las barras.
  static const curva = QColores.navy;

  /// Retícula y ejes: un paso por encima de la superficie, sin competir con los datos.
  static const reticula = QColores.borde;
  static const ejeTexto = QColores.textoTenue;
}

/// El estilo de los rótulos de los ejes.
const estiloEje = TextStyle(
  fontSize: 11,
  color: ColoresGraficos.ejeTexto,
  fontFeatures: [FontFeature.tabularFigures()],
);

/// Una muestra de color para las leyendas: el color va aquí y no en el texto de al lado.
class MuestraDeColor extends StatelessWidget {
  const MuestraDeColor(this.color, {super.key, this.linea = false});

  final Color color;

  /// Una línea corta en vez de un cuadrado, para series de línea.
  final bool linea;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: linea ? 16 : 10,
      height: linea ? 2 : 10,
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(linea ? 1 : 2),
      ),
    );
  }
}
