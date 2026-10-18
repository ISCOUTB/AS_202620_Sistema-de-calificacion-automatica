import 'package:flutter/material.dart';

/// Tokens del sistema de diseño «Academic Precision AI» (diseño de Susana en Stitch), pasados a
/// Flutter. Las pantallas no escriben colores, radios ni sombras a mano: los toman de aquí, para
/// que un cambio de marca se haga en un solo archivo.
///
/// Una corrección frente al documento original: el verde, el naranja y el rojo semánticos
/// (`#10B981`, `#FF7A00`, `#EF4444`) no alcanzan 4,5:1 como texto sobre sus fondos claros. Se
/// conservan para íconos, rieles y barras, y el texto usa la variante oscura de cada uno.
abstract final class QColores {
  /// Navy institucional: barra superior, paneles de autoridad y acciones finales.
  static const navy = Color(0xFF051937);
  static const navyProfundo = Color(0xFF071B39);
  static const navyMedio = Color(0xFF213145);

  /// Cobalto: el único color de interacción (botones principales, pestaña activa, foco).
  static const cobalto = Color(0xFF0066FF);
  static const cobaltoOscuro = Color(0xFF0050CC);

  /// Cian: reservado para lo que hace la máquina (lectura OMR, propuestas del modelo).
  static const cian = Color(0xFF00D2FF);
  static const cianTexto = Color(0xFF00708A);

  static const fondo = Color(0xFFF8FAFC);
  static const superficie = Color(0xFFFFFFFF);
  static const superficieSuave = Color(0xFFF1F5F9);
  static const superficieAzul = Color(0xFFEFF4FF);
  static const superficieAzulMedia = Color(0xFFE5EEFF);
  static const superficieAzulFuerte = Color(0xFFDCE9FF);

  static const texto = Color(0xFF0F172A);
  static const textoSuave = Color(0xFF475569);
  static const textoTenue = Color(0xFF64748B);
  static const textoSobreNavy = Color(0xFFFFFFFF);
  static const textoSobreNavySuave = Color(0xFFB5C7ED);

  static const borde = Color(0xFFE2E8F0);
  static const bordeCampo = Color(0xFFCBD5E1);

  static const exito = Color(0xFF10B981);
  static const exitoTexto = Color(0xFF047857);
  static const exitoFondo = Color(0xFFECFDF5);

  static const advertencia = Color(0xFFFF7A00);
  static const advertenciaTexto = Color(0xFFB45309);
  static const advertenciaFondo = Color(0xFFFFF3E0);

  static const error = Color(0xFFEF4444);
  static const errorTexto = Color(0xFFB91C1C);
  static const errorFondo = Color(0xFFFEF2F2);
}

/// Radios. La regla es una sola y se cumple en todas las pantallas: controles (botones, campos,
/// chips) a 8; tarjetas a 16; hojas y paneles grandes a 24; píldora solo para las insignias de
/// confianza y los filtros.
abstract final class QRadios {
  static const control = 8.0;
  static const tarjeta = 16.0;
  static const hoja = 24.0;
  static const pildora = 999.0;
}

/// Espaciado en múltiplos de 4.
abstract final class QEspacios {
  static const xs = 4.0;
  static const sm = 8.0;
  static const md = 16.0;
  static const lg = 24.0;
  static const xl = 32.0;
  static const xxl = 48.0;
}

/// Sombras teñidas del navy, nunca negras.
abstract final class QSombras {
  static const nivel1 = [
    BoxShadow(color: Color(0x0D051937), blurRadius: 3, offset: Offset(0, 1)),
    BoxShadow(color: Color(0x08051937), blurRadius: 2, spreadRadius: -1, offset: Offset(0, 1)),
  ];
  static const nivel2 = [
    BoxShadow(color: Color(0x14051937), blurRadius: 6, spreadRadius: -1, offset: Offset(0, 4)),
    BoxShadow(color: Color(0x0A051937), blurRadius: 4, spreadRadius: -2, offset: Offset(0, 2)),
  ];
  static const nivel3 = [
    BoxShadow(color: Color(0x1A051937), blurRadius: 15, spreadRadius: -3, offset: Offset(0, 10)),
    BoxShadow(color: Color(0x0D051937), blurRadius: 6, spreadRadius: -4, offset: Offset(0, 4)),
  ];
}

/// Anchos de pantalla en los que cambia la composición.
abstract final class QAnchos {
  /// Desde aquí la navegación pasa de la barra inferior a un riel lateral.
  static const riel = 840.0;

  /// Desde aquí las cuadrículas pasan de una a dos columnas.
  static const dosColumnas = 720.0;

  /// Ancho máximo del contenido: más allá, las líneas de texto se vuelven difíciles de seguir.
  static const contenido = 1120.0;
}

/// Duraciones. Una transición de estado dura poco; nada se anima en bucle.
abstract final class QDuraciones {
  static const corta = Duration(milliseconds: 120);
  static const media = Duration(milliseconds: 220);
}
